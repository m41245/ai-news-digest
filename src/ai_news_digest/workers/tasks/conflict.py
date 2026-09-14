from __future__ import annotations

import asyncio
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


async def _detect_claim_conflicts_impl() -> dict[str, int | str | float]:
    """
    Typed implementation function for claim conflict detection.
    """
    logger.info("Starting claim conflict detection")
    settings = get_settings()

    async for container in get_container():
        if not settings.conflict_detection_enabled:
            logger.info("Conflict detection is disabled")
            return {"status": "disabled"}

        detect_use_case = container.detect_claim_conflicts
        if detect_use_case is None:
            logger.warning("Conflict detection use case is unavailable")
            return {"status": "unavailable"}

        raw_result = await detect_use_case.execute()
        result = cast("dict[str, int | str | float]", raw_result)
        logger.info(
            "Claim conflict detection completed",
            candidates=result.get("candidates", 0),
            conflicts=result.get("conflicts", 0),
        )
        return result

    return {"status": "not_found"}


@celery_app.task(
    name="workers.tasks.conflict.detect_claim_conflicts",
    max_retries=2,
    default_retry_delay=120,
)
def detect_claim_conflicts() -> dict[str, int | str | float]:
    """
    Detect potential conflicts between claims from different sources.

    This task is idempotent and can be safely retried.
    """
    return record_task_outcome(
        "workers.tasks.conflict.detect_claim_conflicts",
        _detect_claim_conflicts_impl(),
    )


def record_task_outcome(
    task_name: str,
    impl_coro: Coroutine[Any, Any, dict[str, int | str | float]],
) -> dict[str, int | str | float]:
    """Run a task implementation while recording Celery metrics."""
    start = time.monotonic()
    loop = asyncio.get_event_loop()
    try:
        result = loop.run_until_complete(impl_coro)
        loop.run_until_complete(record_celery_task_success(task_name))
        return result
    except Exception as exc:
        logger.error(
            "Task failed",
            task=task_name,
            error=str(exc),
            exc_info=True,
        )
        loop.run_until_complete(record_celery_task_failure(task_name))
        raise
    finally:
        elapsed = round(time.monotonic() - start, 3)
        loop.run_until_complete(
            record_celery_task_duration(task_name, elapsed)
        )


__all__ = ["detect_claim_conflicts"]
