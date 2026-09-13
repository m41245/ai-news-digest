from __future__ import annotations

import time
from uuid import UUID

from ai_news_digest.core.logging import get_logger
from ai_news_digest.core.metrics import (
    record_celery_task_duration,
    record_celery_task_failure,
    record_celery_task_success,
)
from ai_news_digest.domain.enums.article_status import ArticleStatus
from ai_news_digest.domain.ports.article_repository import ArticleRepository
from ai_news_digest.workers._container import get_container
from ai_news_digest.workers.celery_app import celery_app

logger = get_logger(__name__)


async def _cluster_article_impl(article_id: UUID) -> dict[str, str]:
    """
    Typed implementation function for article story clustering.
    """
    logger.info(
        "Starting article clustering",
        article_id=str(article_id),
    )

    async for container in get_container():
        article_repository: ArticleRepository = container.article_repository
        article = await article_repository.get_by_id(article_id)

        if article is None:
            logger.warning(
                "Article not found for clustering",
                article_id=str(article_id),
            )
            return {"status": "not_found"}

        if article.cluster_id is not None:
            logger.info(
                "Article already clustered, skipping",
                article_id=str(article_id),
                cluster_id=str(article.cluster_id),
            )
            return {"status": "already_clustered"}

        if article.status not in (
            ArticleStatus.CATEGORIZED,
            ArticleStatus.SUMMARIZED,
            ArticleStatus.ANALYZED,
            ArticleStatus.READY,
        ):
            logger.info(
                "Article not ready for clustering, skipping",
                article_id=str(article_id),
                status=article.status,
            )
            return {"status": "not_ready"}

        use_case = container.cluster_articles
        cluster = await use_case.execute(article)

        if cluster is None:
            return {
                "status": "created",
                "article_id": str(article.id),
                "cluster_id": str(article.cluster_id) if article.cluster_id else "",
            }

        return {
            "status": "assigned",
            "article_id": str(article.id),
            "cluster_id": str(cluster.id),
        }

    return {"status": "not_found"}


async def _cluster_pending_articles_impl() -> dict[str, int]:
    """
    Typed implementation function for batch article clustering.
    """
    logger.info("Starting batch clustering of unclustered articles")

    async for container in get_container():
        article_repository: ArticleRepository = container.article_repository
        categorized = await article_repository.list_by_status(
            ArticleStatus.CATEGORIZED, limit=100
        )
        analyzed = await article_repository.list_by_status(
            ArticleStatus.ANALYZED, limit=100
        )
        ready = await article_repository.list_by_status(
            ArticleStatus.READY, limit=100
        )

        candidates = [
            a for a in (categorized + analyzed + ready) if a.cluster_id is None
        ]

        if not candidates:
            logger.info("No unclustered articles found")
            return {"queued": 0}

        logger.info(
            "Found unclustered articles for clustering",
            count=len(candidates),
        )

        for article in candidates:
            cluster_article.delay(article.id)

        return {
            "queued": len(candidates),
        }

    return {"queued": 0}


@celery_app.task(
    name="workers.tasks.cluster.cluster_article",
    max_retries=3,
    default_retry_delay=60,
)
async def cluster_article(article_id: UUID) -> dict[str, str]:
    """
    Cluster a single article into a story cluster.

    This task is idempotent and can be safely retried.
    """
    start = time.monotonic()
    try:
        result = await _cluster_article_impl(article_id)
        await record_celery_task_success("workers.tasks.cluster.cluster_article")
        return result
    except Exception as exc:
        logger.error(
            "Article clustering failed",
            article_id=str(article_id),
            error=str(exc),
            exc_info=True,
        )
        await record_celery_task_failure("workers.tasks.cluster.cluster_article")
        raise
    finally:
        await record_celery_task_duration(
            "workers.tasks.cluster.cluster_article",
            time.monotonic() - start,
        )


@celery_app.task(
    name="workers.tasks.cluster.cluster_pending_articles",
    max_retries=3,
    default_retry_delay=60,
)
async def cluster_pending_articles() -> dict[str, int]:
    """
    Cluster all unclustered articles that have been processed by the AI pipeline.

    This task chains individual clustering tasks for each article.
    """
    start = time.monotonic()
    try:
        result = await _cluster_pending_articles_impl()
        await record_celery_task_success(
            "workers.tasks.cluster.cluster_pending_articles"
        )
        return result
    except Exception as exc:
        logger.error(
            "Batch clustering failed",
            error=str(exc),
            exc_info=True,
        )
        await record_celery_task_failure(
            "workers.tasks.cluster.cluster_pending_articles"
        )
        raise
    finally:
        await record_celery_task_duration(
            "workers.tasks.cluster.cluster_pending_articles",
            time.monotonic() - start,
        )


__all__ = [
    "cluster_article",
    "cluster_pending_articles",
]
