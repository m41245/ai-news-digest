from __future__ import annotations

from uuid import UUID

from ai_news_digest.core.logging import get_logger
from ai_news_digest.workers._container import get_container
from ai_news_digest.workers.celery_app import celery_app

logger = get_logger(__name__)


async def _extract_article_relationships_impl(
    article_id: UUID,
) -> dict[str, object]:
    logger.info(
        "Starting relationship extraction for article",
        article_id=str(article_id),
    )

    async for container in get_container():
        use_case = container.extract_relationships
        relationships = await use_case.extract_for_article(article_id)

        logger.info(
            "Relationship extraction completed for article",
            article_id=str(article_id),
            relationship_count=len(relationships),
        )

        return {
            "status": "completed",
            "article_id": str(article_id),
            "relationship_count": len(relationships),
        }

    return {"status": "skipped", "reason": "no_container"}


async def _extract_story_cluster_relationships_impl(
    cluster_id: UUID,
) -> dict[str, object]:
    logger.info(
        "Starting relationship extraction for story cluster",
        cluster_id=str(cluster_id),
    )

    async for container in get_container():
        use_case = container.extract_relationships
        relationships = await use_case.extract_for_story_cluster(cluster_id)

        logger.info(
            "Relationship extraction completed for story cluster",
            cluster_id=str(cluster_id),
            relationship_count=len(relationships),
        )

        return {
            "status": "completed",
            "cluster_id": str(cluster_id),
            "relationship_count": len(relationships),
        }

    return {"status": "skipped", "reason": "no_container"}


@celery_app.task(
    name="workers.tasks.knowledge_graph.extract_article_relationships",
    max_retries=3,
    default_retry_delay=60,
)
async def extract_article_relationships(article_id: UUID) -> dict[str, object]:
    """Extract knowledge graph relationships for a single article."""
    return await _extract_article_relationships_impl(article_id)


@celery_app.task(
    name="workers.tasks.knowledge_graph.extract_story_cluster_relationships",
    max_retries=3,
    default_retry_delay=60,
)
async def extract_story_cluster_relationships(cluster_id: UUID) -> dict[str, object]:
    """Extract knowledge graph relationships for a story cluster."""
    return await _extract_story_cluster_relationships_impl(cluster_id)


__all__ = [
    "extract_article_relationships",
    "extract_story_cluster_relationships",
]
