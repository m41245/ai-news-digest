"""Bounded, explicitly invoked deterministic processing runner.

Executes the deterministic AI-free processing pipeline against staging
data without requiring a persistent Celery worker, Beat scheduler, or
Redis-backed durable queue.

Pipeline stages (in order):
    1. Summarize   NEW  -> SUMMARIZED
    2. Categorize  SUMMARIZED -> CATEGORIZED
    3. Analyze     CATEGORIZED/SUMMARIZED -> ANALYZED
    4. Cluster     unclustered processed articles -> story clusters
    5. Rank        story clusters -> ranked scores + top story
    6. Trends      detect trends from clusters/activity
    7. Digest      generate daily digest from eligible articles

``--batch-size`` bounds only summarize, categorize, analyze, and cluster;
rank, trends, and digest operate on the full eligible collection. Already
processed articles are skipped. A ``--dry-run`` flag reports what would
be processed without mutating the database.

Usage::

    python scripts/scheduled/run_deterministic_batch.py \\
        --batch-size 50 \\
        --dry-run

    python scripts/scheduled/run_deterministic_batch.py \\
        --batch-size 100
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ai_news_digest.bootstrap.container import Container
from ai_news_digest.core.logging import configure_logging, get_logger
from ai_news_digest.domain.enums.article_status import ArticleStatus
from ai_news_digest.workers._container import get_container
from ai_news_digest.workers.tasks.cluster import _cluster_pending_articles_impl
from ai_news_digest.workers.tasks.digest import _generate_daily_digest_impl
from ai_news_digest.workers.tasks.process import (
    _analyze_pending_articles_impl,
    _categorize_pending_articles_impl,
    _summarize_pending_articles_impl,
)
from ai_news_digest.workers.tasks.ranking import _rank_stories_impl
from ai_news_digest.workers.tasks.trend import _detect_trends_impl

if TYPE_CHECKING:
    pass

configure_logging()
logger = get_logger(__name__)

_STAGE_NAMES: tuple[str, ...] = (
    "summarize",
    "categorize",
    "analyze",
    "cluster",
    "rank",
    "trends",
    "digest",
)

ALL_STAGES = ", ".join(_STAGE_NAMES)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run bounded deterministic processing stages in order.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Maximum number of articles to process per stage (default: 100).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Report what would be processed without mutating the database.",
    )
    parser.add_argument(
        "--stages",
        type=str,
        default=ALL_STAGES,
        help=f"Comma-separated list of stages to run (default: {ALL_STAGES}).",
    )
    parser.add_argument(
        "--skip-stages",
        type=str,
        default="",
        help="Comma-separated list of stages to skip.",
    )
    return parser.parse_args()


async def _count_by_status(
    container: Container,
    status: ArticleStatus,
) -> int:
    articles = await container.article_repository.list_by_status(status, limit=1)
    return len(articles)


async def _run_stage(
    stage: str,
    batch_size: int,
    dry_run: bool,
    container: Container,
) -> dict[str, Any]:
    """Run a single pipeline stage and return a structured result."""
    result: dict[str, Any] = {
        "stage": stage,
        "dry_run": dry_run,
        "processed": 0,
        "skipped": 0,
        "failed": 0,
        "status": "skipped",
    }

    if dry_run:
        if stage == "summarize":
            n = await _count_by_status(container, ArticleStatus.NEW)
            result["status"] = "would_process"
            result["processed"] = n
        elif stage == "categorize":
            n = await _count_by_status(container, ArticleStatus.SUMMARIZED)
            result["status"] = "would_process"
            result["processed"] = n
        elif stage == "analyze":
            n = await _count_by_status(container, ArticleStatus.CATEGORIZED)
            n += await _count_by_status(container, ArticleStatus.SUMMARIZED)
            result["status"] = "would_process"
            result["processed"] = n
        elif stage == "cluster":
            result["status"] = "would_process"
            result["processed"] = -1  # unknown without scanning
        elif stage in ("rank", "trends", "digest"):
            result["status"] = "would_process"
            result["processed"] = -1
        logger.info(
            "Dry run stage preview",
            stage=stage,
            would_process=result["processed"],
        )
        return result

    try:
        result_data: dict[str, Any]
        if stage == "summarize":
            result_data = await _summarize_pending_articles_impl(
                execute_directly=True,
                limit=batch_size,
            )
            result["processed"] = int(result_data.get("queued", 0))
            result["failed"] = int(result_data.get("failed", 0))
            result["status"] = "completed"
        elif stage == "categorize":
            result_data = await _categorize_pending_articles_impl(
                execute_directly=True,
                limit=batch_size,
            )
            result["processed"] = int(result_data.get("queued", 0))
            result["failed"] = int(result_data.get("failed", 0))
            result["status"] = "completed"
        elif stage == "analyze":
            result_data = await _analyze_pending_articles_impl(
                execute_directly=True,
                limit=batch_size,
            )
            result["processed"] = int(result_data.get("queued", 0))
            result["failed"] = int(result_data.get("failed", 0))
            result["status"] = "completed"
        elif stage == "cluster":
            result_data = await _cluster_pending_articles_impl(
                execute_directly=True,
                limit=batch_size,
            )
            result["processed"] = int(result_data.get("queued", 0))
            result["status"] = "completed"
        elif stage == "rank":
            result_data = await _rank_stories_impl()
            result["processed"] = int(result_data.get("ranked_clusters", "0"))
            result["status"] = str(result_data.get("status", "completed"))
        elif stage == "trends":
            result_data = await _detect_trends_impl()
            detected = result_data.get("detected", 0)
            if isinstance(detected, dict):
                detected = sum(int(v) for v in detected.values())
            result["processed"] = int(detected or 0)
            result["status"] = str(result_data.get("status", "completed"))
        elif stage == "digest":
            result_data = await _generate_daily_digest_impl()
            result["processed"] = int(result_data.get("included_articles", "0"))
            result["status"] = str(result_data.get("status", "completed"))
        else:
            result["status"] = "unknown_stage"
            logger.warning("Unknown stage requested", stage=stage)

    except Exception as exc:
        logger.error(
            "Stage failed",
            stage=stage,
            error=str(exc),
            exc_info=True,
        )
        result["status"] = "failed"
        result["failed"] = 1
        result["error"] = str(exc)

    logger.info(
        "Stage complete",
        stage=stage,
        processed=result["processed"],
        failed=result["failed"],
        status=result["status"],
    )
    return result


async def _run_pipeline(
    batch_size: int,
    dry_run: bool,
    stages: list[str],
) -> list[dict[str, Any]]:
    """Run the pipeline stages in order, returning per-stage results."""
    results: list[dict[str, Any]] = []

    async for container in get_container():
        for stage in stages:
            stage_result = await _run_stage(stage, batch_size, dry_run, container)
            results.append(stage_result)
            if stage_result["status"] == "failed":
                logger.error(
                    "Pipeline halted due to stage failure",
                    stage=stage,
                )
                break

    return results


_LOCK_FILE_NAME = "ai_news_digest_batch_runner.lock"


def _lock_path() -> Path:
    return Path(tempfile.gettempdir()) / _LOCK_FILE_NAME


def _is_pid_alive(pid: int) -> bool:
    """Return True if a process with *pid* appears to be running."""
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _acquire_lock() -> bool:
    """Best-effort single-instance lock.

    Returns True when this process holds (or could not test) the lock, False
    when another live process already holds it. Stale locks left by dead
    processes are reclaimed automatically.
    """
    path = _lock_path()
    holder_pid: int | None = None
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        raw = ""
    except OSError:
        raw = ""

    if raw:
        try:
            holder_pid = int(raw)
        except ValueError:
            holder_pid = None

    if holder_pid is not None and _is_pid_alive(holder_pid):
        return False

    try:
        path.write_text(str(os.getpid()), encoding="utf-8")
    except OSError:
        return True

    return True


def _release_lock() -> None:
    path = _lock_path()
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except (FileNotFoundError, OSError):
        return
    try:
        if int(raw) == os.getpid():
            path.unlink()
    except (ValueError, OSError):
        pass


def main() -> int:
    args = _parse_args()

    requested = {s.strip() for s in args.stages.split(",") if s.strip()}
    skipped = {s.strip() for s in args.skip_stages.split(",") if s.strip()}

    invalid = requested - set(_STAGE_NAMES)
    if invalid:
        logger.error("Invalid stages requested", stages=sorted(invalid))
        return 1

    stages = [s for s in _STAGE_NAMES if s in requested and s not in skipped]

    if not stages:
        logger.error("No stages selected to run")
        return 1

    if not _acquire_lock():
        logger.error("Another batch runner instance is already running")
        return 2

    logger.info(
        "Deterministic batch runner starting",
        stages=", ".join(stages),
        batch_size=args.batch_size,
        dry_run=args.dry_run,
    )

    start = datetime.now(UTC)
    try:
        results = asyncio.run(
            _run_pipeline(args.batch_size, args.dry_run, stages),
        )
    except Exception as exc:
        logger.error(
            "Pipeline execution failed",
            error=str(exc),
            exc_info=True,
        )
        return 1
    finally:
        _release_lock()

    elapsed = (datetime.now(UTC) - start).total_seconds()

    total_processed = sum(
        r.get("processed", 0)
        for r in results
        if isinstance(r.get("processed"), int) and r["processed"] > 0
    )
    total_failed = sum(r.get("failed", 0) for r in results)
    failed_stages = [r["stage"] for r in results if r["status"] == "failed"]

    logger.info(
        "Deterministic batch runner finished",
        elapsed_seconds=round(elapsed, 2),
        stages_run=len(results),
        total_processed=total_processed,
        total_failed=total_failed,
        failed_stages=failed_stages,
    )

    for r in results:
        logger.info(
            "Stage result",
            stage=r["stage"],
            status=r["status"],
            processed=r["processed"],
            failed=r["failed"],
        )

    return 1 if failed_stages else 0


if __name__ == "__main__":
    sys.exit(main())
