from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta

from ai_news_digest.core.logging import get_logger
from ai_news_digest.core.metrics import (
    record_celery_task_duration,
    record_celery_task_failure,
    record_celery_task_success,
)
from ai_news_digest.workers._container import get_container
from ai_news_digest.workers.celery_app import celery_app

logger = get_logger(__name__)

_BATCH_SIZE = 1000
_TASK_NAME_CLEANUP_ARTICLES = "workers.tasks.cleanup.cleanup_old_articles"
_TASK_NAME_CLEANUP_DIGESTS = "workers.tasks.cleanup.cleanup_old_digests"


@celery_app.task(
    name="workers.tasks.cleanup.cleanup_old_articles",
    max_retries=3,
    default_retry_delay=60,
)
async def cleanup_old_articles(days: int = 30) -> dict[str, int]:
    """Delete articles older than the specified number of days."""
    start = time.monotonic()
    try:
        cutoff_date = datetime.now(UTC) - timedelta(days=days)
        deleted = 0

        async for container in get_container():
            article_repository = container.article_repository
            while True:
                batch_deleted = await article_repository.delete_older_than(
                    cutoff_date,
                    limit=_BATCH_SIZE,
                )
                deleted += batch_deleted
                if batch_deleted < _BATCH_SIZE:
                    break
            break

        logger.info(
            "Cleanup completed: deleted %d articles older than %d days",
            deleted,
            days,
        )

        await record_celery_task_success(_TASK_NAME_CLEANUP_ARTICLES)
        return {
            "deleted": deleted,
            "days": days,
        }
    except Exception as exc:
        logger.error(
            "Article cleanup failed",
            days=days,
            error=str(exc),
            exc_info=True,
        )
        await record_celery_task_failure(_TASK_NAME_CLEANUP_ARTICLES)
        raise
    finally:
        await record_celery_task_duration(_TASK_NAME_CLEANUP_ARTICLES, time.monotonic() - start)


@celery_app.task(
    name="workers.tasks.cleanup.cleanup_old_digests",
    max_retries=3,
    default_retry_delay=60,
)
async def cleanup_old_digests(days: int = 90) -> dict[str, int]:
    """Delete digests older than the specified number of days."""
    start = time.monotonic()
    try:
        cutoff_date = datetime.now(UTC) - timedelta(days=days)
        deleted = 0

        async for container in get_container():
            digest_repository = container.digest_repository
            while True:
                batch_deleted = await digest_repository.delete_older_than(
                    cutoff_date,
                    limit=_BATCH_SIZE,
                )
                deleted += batch_deleted
                if batch_deleted < _BATCH_SIZE:
                    break
            break

        logger.info(
            "Digest cleanup completed: deleted %d digests older than %d days",
            deleted,
            days,
        )

        await record_celery_task_success(_TASK_NAME_CLEANUP_DIGESTS)
        return {
            "deleted": deleted,
            "days": days,
        }
    except Exception as exc:
        logger.error(
            "Digest cleanup failed",
            days=days,
            error=str(exc),
            exc_info=True,
        )
        await record_celery_task_failure(_TASK_NAME_CLEANUP_DIGESTS)
        raise
    finally:
        await record_celery_task_duration(_TASK_NAME_CLEANUP_DIGESTS, time.monotonic() - start)


__all__ = ["cleanup_old_articles", "cleanup_old_digests"]
