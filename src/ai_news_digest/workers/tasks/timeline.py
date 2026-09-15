from __future__ import annotations

import asyncio
import contextlib
import time
from collections.abc import Coroutine
from typing import Any, cast

from ai_news_digest.core.config import get_settings
from ai_news_digest.core.logging import get_logger
from ai_news_digest.core.metrics import (
    record_celery_task_duration,
    record_celery_task_failure,
    record_celery_task_success,
)
from ai_news_digest.workers._container import get_container
from ai_news_digest.workers.celery_app import celery_app

logger = get_logger(__name__)


async def _generate_timeline_impl() -> dict[str, int | str | float]:
    logger.info("Starting story timeline generation")
    settings = get_settings()
    if not settings.timeline_generation_enabled:
        return {"status": "disabled"}
    async for container in get_container():
        use_case = container.generate_story_timeline
        cluster_repo = container.story_cluster_repository
        from datetime import UTC, datetime, timedelta

        cutoff = datetime.now(UTC) - timedelta(days=settings.timeline_lookback_days)
        clusters = await cluster_repo.find_recent_active_clusters(
            cutoff=cutoff,
            limit=settings.max_story_candidates,
        )
        total_events = 0
        for cluster in clusters:
            try:
                result = await use_case.execute(cluster.id)
                total_events += result.get("events_created", 0)
            except Exception:
                logger.warning(
                    "Timeline generation failed for cluster",
                    cluster_id=str(cluster.id),
                )
        return {
            "status": "completed",
            "clusters_processed": len(clusters),
            "total_events": total_events,
        }
    return {"status": "not_found"}


@celery_app.task(
    name="workers.tasks.timeline.generate_story_timeline",
    max_retries=2,
    default_retry_delay=120,
)
def generate_story_timeline() -> dict[str, int | str | float]:
    return record_task_outcome(
        "workers.tasks.timeline.generate_story_timeline", _generate_timeline_impl()
    )


def record_task_outcome(
    task_name: str,
    impl_coro: Coroutine[Any, Any, dict[str, int | str | float]],
) -> dict[str, int | str | float]:
    start = time.monotonic()

    def _run(coro: Coroutine[Any, Any, Any]) -> Any:
        try:
            return asyncio.run(coro)
        except RuntimeError:
            asyncio.get_event_loop()
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result()

    try:
        result = cast("dict[str, int | str | float]", _run(impl_coro))
        _run(record_celery_task_success(task_name))
        return result
    except Exception as exc:
        logger.error("Task failed", task=task_name, error=str(exc), exc_info=True)
        with contextlib.suppress(Exception):
            _run(record_celery_task_failure(task_name))
        raise
    finally:
        elapsed = round(time.monotonic() - start, 3)
        with contextlib.suppress(Exception):
            _run(record_celery_task_duration(task_name, elapsed))


__all__ = ["generate_story_timeline"]
