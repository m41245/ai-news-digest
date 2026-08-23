from __future__ import annotations

from datetime import UTC, datetime, timedelta

from celery.utils.log import get_task_logger

from ai_news_digest.core.logging import get_logger
from ai_news_digest.workers._container import get_container
from ai_news_digest.workers.celery_app import celery_app

task_logger = get_task_logger(__name__)
logger = get_logger(__name__)

_BATCH_SIZE = 1000


@celery_app.task(
    name="workers.tasks.cleanup.cleanup_old_articles",
    max_retries=2,
    default_retry_delay=180,
)
async def cleanup_old_articles(days: int = 30) -> dict[str, int]:
    """Delete articles older than the specified number of days."""
    cutoff_date = datetime.now(UTC) - timedelta(days=days)
    deleted = 0

    async for container in get_container():
        article_repository = container.article_repository
        offset = 0

        while True:
            batch = await article_repository.list_recent(
                limit=_BATCH_SIZE,
                offset=offset,
            )

            if not batch:
                break

            batch_deleted = 0
            for article in batch:
                if article.published_at < cutoff_date:
                    await article_repository.delete(article.id)
                    batch_deleted += 1

            deleted += batch_deleted
            offset += _BATCH_SIZE

            if len(batch) < _BATCH_SIZE:
                break

        break

    logger.info(
        "Cleanup completed: deleted %d articles older than %d days",
        deleted,
        days,
    )

    return {
        "deleted": deleted,
        "days": days,
    }


@celery_app.task(
    name="workers.tasks.cleanup.cleanup_old_digests",
    max_retries=2,
    default_retry_delay=180,
)
async def cleanup_old_digests(days: int = 90) -> dict[str, int]:
    """Delete digests older than the specified number of days."""
    cutoff_date = datetime.now(UTC) - timedelta(days=days)
    deleted = 0

    async for container in get_container():
        digest_repository = container.digest_repository
        offset = 0

        while True:
            batch = await digest_repository.list_recent(
                limit=_BATCH_SIZE,
                offset=offset,
            )

            if not batch:
                break

            batch_deleted = 0
            for digest in batch:
                if digest.generated_at < cutoff_date:
                    await digest_repository.delete(digest.id)
                    batch_deleted += 1

            deleted += batch_deleted
            offset += _BATCH_SIZE

            if len(batch) < _BATCH_SIZE:
                break

        break

    logger.info(
        "Digest cleanup completed: deleted %d digests older than %d days",
        deleted,
        days,
    )

    return {
        "deleted": deleted,
        "days": days,
    }


__all__ = ["cleanup_old_articles", "cleanup_old_digests"]
