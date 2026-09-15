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


async def _detect_story_activity_impl() -> dict[str, int | str | float]:
    """
    Typed implementation function for story activity detection.
    """
    logger.info("Starting story activity detection")
    settings = get_settings()

    async for container in get_container():
        if not settings.breaking_detection_enabled:
            logger.info("Story activity detection is disabled")
            return {"status": "disabled" }

        detect_use_case = container.detect_story_activity
        if detect_use_case is None:
            logger.warning("Story activity detection use case is unavailable")
            return {"status": "unavailable"}

        raw_result = await detect_use_case.execute()
        result = cast("dict[str, int | str | float]", raw_result)
        logger.info(
            "Story activity detection completed",
            evaluated=result.get("evaluated", 0),
            breaking=result.get("breaking", 0),
            developing=result.get("developing", 0),
            ongoing=result.get("ongoing", 0),
            stale=result.get("stale", 0),
        )
        return result

    return {"status": "not_found"}


@celery_app.task(
    name="workers.tasks.story_activity.detect_story_activity",
    max_retries=2,
    default_retry_delay=120,
)
def detect_story_activity() -> dict[str, int | str | float]:
    """
    Detect breaking and developing story activity.

    This task is idempotent and can be safely retried.
    """
    return record_task_outcome(
        "workers.tasks.story_activity.detect_story_activity",
        _detect_story_activity_impl(),
    )


def record_task_outcome(
    task_name: str,
    impl_coro: Coroutine[Any, Any, dict[str, int | str | float]],
) -> dict[str, int | str | float]:
    """Run a task implementation while recording Celery metrics."""
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
        logger.error(
            "Task failed",
            task=task_name,
            error=str(exc),
            exc_info=True,
        )
        with contextlib.suppress(Exception):
            _run(record_celery_task_failure(task_name))
        raise
    finally:
        elapsed = round(time.monotonic() - start, 3)
        with contextlib.suppress(Exception):
            _run(record_celery_task_duration(task_name, elapsed))


__all__ = ["detect_story_activity"]
