from __future__ import annotations

from uuid import UUID

from celery.utils.log import get_task_logger

from ai_news_digest.core.logging import get_logger
from ai_news_digest.domain.enums.article_status import ArticleStatus
from ai_news_digest.domain.ports.article_repository import ArticleRepository
from ai_news_digest.workers._container import get_container
from ai_news_digest.workers.celery_app import celery_app

task_logger = get_task_logger(__name__)
logger = get_logger(__name__)


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

        from ai_news_digest.domain.enums.article_status import ArticleStatus

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
        recent_articles = await article_repository.list_recent(limit=100)

        pending_articles = [
            article for article in recent_articles if article.status == ArticleStatus.NEW
        ]

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
        recent_articles = await article_repository.list_recent(limit=100)

        ready_articles = [
            article for article in recent_articles if article.status == ArticleStatus.SUMMARIZED
        ]

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
    default_retry_delay=120,
)
async def summarize_article(article_id: UUID) -> dict[str, str]:
    """
    Summarize a single article using AI.

    This task is idempotent and can be safely retried.
    """
    try:
        return await _summarize_article_impl(article_id)
    except Exception as exc:
        logger.error(
            "Article summarization failed",
            article_id=str(article_id),
            error=str(exc),
            exc_info=True,
        )
        raise


@celery_app.task(
    name="workers.tasks.process.categorize_article",
    max_retries=3,
    default_retry_delay=120,
)
async def categorize_article(article_id: UUID) -> dict[str, str]:
    """
    Categorize a single article using AI.

    This task is idempotent and can be safely retried.
    """
    try:
        return await _categorize_article_impl(article_id)
    except Exception as exc:
        logger.error(
            "Article categorization failed",
            article_id=str(article_id),
            error=str(exc),
            exc_info=True,
        )
        raise


@celery_app.task(
    name="workers.tasks.process.process_article",
    max_retries=3,
    default_retry_delay=120,
)
async def process_article(article_id: UUID) -> dict[str, str]:
    """
    Run the full AI processing pipeline for a single article.

    This task is idempotent and can be safely retried.
    """
    try:
        return await _process_article_impl(article_id)
    except Exception as exc:
        logger.error(
            "Article processing failed",
            article_id=str(article_id),
            error=str(exc),
            exc_info=True,
        )
        raise


@celery_app.task(
    name="workers.tasks.process.summarize_pending_articles",
)
async def summarize_pending_articles() -> dict[str, int]:
    """
    Summarize all pending NEW articles.

    This task chains individual summarization tasks for each article.
    """
    try:
        return await _summarize_pending_articles_impl()
    except Exception as exc:
        logger.error(
            "Batch summarization failed",
            error=str(exc),
            exc_info=True,
        )
        raise


@celery_app.task(
    name="workers.tasks.process.categorize_pending_articles",
)
async def categorize_pending_articles() -> dict[str, int]:
    """
    Categorize all SUMMARIZED articles.

    This task chains individual categorization tasks for each article.
    """
    try:
        return await _categorize_pending_articles_impl()
    except Exception as exc:
        logger.error(
            "Batch categorization failed",
            error=str(exc),
            exc_info=True,
        )
        raise


__all__ = [
    "categorize_article",
    "categorize_pending_articles",
    "process_article",
    "summarize_article",
    "summarize_pending_articles",
]
