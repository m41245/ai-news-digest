from __future__ import annotations

import time
from collections.abc import Awaitable
from uuid import UUID

from ai_news_digest.core.logging import get_logger
from ai_news_digest.core.metrics import (
    record_article_processed,
    record_celery_task_duration,
    record_celery_task_failure,
    record_celery_task_success,
)
from ai_news_digest.domain.enums.article_status import ArticleStatus
from ai_news_digest.domain.ports.article_repository import ArticleRepository
from ai_news_digest.workers._container import get_container
from ai_news_digest.workers.celery_app import celery_app

logger = get_logger(__name__)


async def _record_task_outcome(
    task_name: str,
    impl_coro: Awaitable[object],
    *,
    count_article_on_completed: bool = False,
) -> object:
    """Run a task implementation while recording Celery and article metrics."""
    start = time.monotonic()
    try:
        result = await impl_coro
        if (
            count_article_on_completed
            and isinstance(result, dict)
            and result.get("status") == "completed"
        ):
            record_article_processed(1)
        await record_celery_task_success(task_name)
        return result
    except Exception as exc:
        logger.error(
            "Task failed",
            task=task_name,
            error=str(exc),
            exc_info=True,
        )
        await record_celery_task_failure(task_name)
        raise
    finally:
        await record_celery_task_duration(task_name, time.monotonic() - start)


async def _summarize_article_impl(article_id: UUID) -> dict[str, str]:
    """
    Typed implementation function for article summarization.
    """
    logger.info(
        "Starting article summarization",
        article_id=str(article_id),
    )

    async for container in get_container():
        article_repository = container.article_repository
        article = await article_repository.get_by_id(article_id)

        if article is None:
            logger.warning(
                "Article not found for summarization",
                article_id=str(article_id),
            )
            return {"status": "not_found"}

        if article.status != ArticleStatus.NEW:
            logger.info(
                "Article already processed, skipping summarization",
                article_id=str(article_id),
                status=article.status,
            )
            return {"status": "already_processed"}

        use_case = container.summarize_article
        updated_article = await use_case.execute(article)

        logger.info(
            "Article summarization completed",
            article_id=str(article_id),
            status=updated_article.status,
        )

        return {
            "status": "completed",
            "article_id": str(updated_article.id),
            "article_status": updated_article.status,
        }

    return {"status": "not_found"}


async def _categorize_article_impl(article_id: UUID) -> dict[str, str]:
    """
    Typed implementation function for article categorization.
    """
    logger.info(
        "Starting article categorization",
        article_id=str(article_id),
    )

    async for container in get_container():
        article_repository = container.article_repository
        article = await article_repository.get_by_id(article_id)

        if article is None:
            logger.warning(
                "Article not found for categorization",
                article_id=str(article_id),
            )
            return {"status": "not_found"}

        if article.status != ArticleStatus.SUMMARIZED:
            logger.info(
                "Article not ready for categorization, skipping",
                article_id=str(article_id),
                status=article.status,
            )
            return {"status": "not_ready"}

        use_case = container.categorize_article
        updated_article = await use_case.execute(article)

        logger.info(
            "Article categorization completed",
            article_id=str(article_id),
            status=updated_article.status,
        )

        return {
            "status": "completed",
            "article_id": str(updated_article.id),
            "article_status": updated_article.status,
        }

    return {"status": "not_found"}


async def _process_article_impl(article_id: UUID) -> dict[str, str]:
    """
    Typed implementation function for full article AI processing.
    """
    logger.info(
        "Starting full article processing",
        article_id=str(article_id),
    )

    async for container in get_container():
        article_repository = container.article_repository
        article = await article_repository.get_by_id(article_id)

        if article is None:
            logger.warning(
                "Article not found for processing",
                article_id=str(article_id),
            )
            return {"status": "not_found"}

        if article.status not in (ArticleStatus.NEW, ArticleStatus.SUMMARIZED):
            logger.info(
                "Article already fully processed, skipping",
                article_id=str(article_id),
                status=article.status,
            )
            return {"status": "already_processed"}

        use_case = container.process_article
        updated_article = await use_case.execute(article)

        logger.info(
            "Article processing completed",
            article_id=str(article_id),
            status=updated_article.status,
        )

        return {
            "status": "completed",
            "article_id": str(updated_article.id),
            "article_status": updated_article.status,
        }

    return {"status": "not_found"}


async def _summarize_pending_articles_impl() -> dict[str, int]:
    """
    Typed implementation function for batch article summarization.
    """
    logger.info("Starting batch summarization of pending articles")

    async for container in get_container():
        article_repository: ArticleRepository = container.article_repository
        pending_articles = await article_repository.list_by_status(
            ArticleStatus.NEW, limit=100
        )

        if not pending_articles:
            logger.info("No pending articles found for summarization")
            return {"processed": 0}

        logger.info(
            "Found pending articles for summarization",
            count=len(pending_articles),
        )

        for article in pending_articles:
            summarize_article.delay(article.id)

        return {
            "queued": len(pending_articles),
        }

    return {"processed": 0}


async def _categorize_pending_articles_impl() -> dict[str, int]:
    """
    Typed implementation function for batch article categorization.
    """
    logger.info("Starting batch categorization of summarized articles")

    async for container in get_container():
        article_repository: ArticleRepository = container.article_repository
        ready_articles = await article_repository.list_by_status(
            ArticleStatus.SUMMARIZED, limit=100
        )

        if not ready_articles:
            logger.info("No ready articles found for categorization")
            return {"processed": 0}

        logger.info(
            "Found ready articles for categorization",
            count=len(ready_articles),
        )

        for article in ready_articles:
            categorize_article.delay(article.id)

        return {
            "queued": len(ready_articles),
        }

    return {"processed": 0}


@celery_app.task(
    name="workers.tasks.process.summarize_article",
    max_retries=3,
    default_retry_delay=60,
)
async def summarize_article(article_id: UUID) -> dict[str, str]:
    """
    Summarize a single article using AI.

    This task is idempotent and can be safely retried.
    """
    return await _record_task_outcome(  # type: ignore[return-value]
        "workers.tasks.process.summarize_article",
        _summarize_article_impl(article_id),
        count_article_on_completed=True,
    )


@celery_app.task(
    name="workers.tasks.process.categorize_article",
    max_retries=3,
    default_retry_delay=60,
)
async def categorize_article(article_id: UUID) -> dict[str, str]:
    """
    Categorize a single article using AI.

    This task is idempotent and can be safely retried.
    """
    return await _record_task_outcome(  # type: ignore[return-value]
        "workers.tasks.process.categorize_article",
        _categorize_article_impl(article_id),
        count_article_on_completed=True,
    )


@celery_app.task(
    name="workers.tasks.process.process_article",
    max_retries=3,
    default_retry_delay=60,
)
async def process_article(article_id: UUID) -> dict[str, str]:
    """
    Run the full AI processing pipeline for a single article.

    This task is idempotent and can be safely retried.
    """
    return await _record_task_outcome(  # type: ignore[return-value]
        "workers.tasks.process.process_article",
        _process_article_impl(article_id),
        count_article_on_completed=True,
    )


@celery_app.task(
    name="workers.tasks.process.summarize_pending_articles",
    max_retries=3,
    default_retry_delay=60,
)
async def summarize_pending_articles() -> dict[str, int]:
    """
    Summarize all pending NEW articles.

    This task chains individual summarization tasks for each article.
    """
    return await _record_task_outcome(  # type: ignore[return-value]
        "workers.tasks.process.summarize_pending_articles",
        _summarize_pending_articles_impl(),
    )


@celery_app.task(
    name="workers.tasks.process.categorize_pending_articles",
    max_retries=3,
    default_retry_delay=60,
)
async def categorize_pending_articles() -> dict[str, int]:
    """
    Categorize all SUMMARIZED articles.

    This task chains individual categorization tasks for each article.
    """
    return await _record_task_outcome(  # type: ignore[return-value]
        "workers.tasks.process.categorize_pending_articles",
        _categorize_pending_articles_impl(),
    )


__all__ = [
    "categorize_article",
    "categorize_pending_articles",
    "process_article",
    "summarize_article",
    "summarize_pending_articles",
]
