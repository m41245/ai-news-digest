from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta

from ai_news_digest.application.services.ranking.story_ranking_service import (
    StoryRankingEngine,
)
from ai_news_digest.application.services.ranking.top_story_selector import (
    TopStorySelector,
)
from ai_news_digest.core.config import get_settings
from ai_news_digest.core.logging import get_logger
from ai_news_digest.domain.models.article import Article
from ai_news_digest.core.metrics import (
    record_celery_task_duration,
    record_celery_task_failure,
    record_celery_task_success,
)
from ai_news_digest.workers._container import get_container
from ai_news_digest.workers.celery_app import celery_app

logger = get_logger(__name__)

_TASK_NAME = "workers.tasks.ranking.rank_stories"


async def _rank_stories_impl() -> dict[str, str]:
    """
    Typed implementation function for daily story ranking.
    """
    logger.info("Starting daily story ranking")

    async for container in get_container():
        settings = get_settings()
        if not settings.story_ranking_enabled:
            logger.info("Story ranking is disabled, skipping")
            return {
                "status": "skipped",
                "reason": "ranking_disabled",
            }

        now = datetime.now(UTC)
        cutoff = now - timedelta(hours=settings.ranking_lookback_hours)

        clusters = await container.story_cluster_repository.find_recent_active_clusters(
            cutoff=cutoff,
            limit=settings.ranking_max_candidates,
        )

        if not clusters:
            logger.info("No eligible story clusters for ranking")
            return {
                "status": "completed",
                "ranked_clusters": "0",
                "top_story_cluster_id": "",
            }

        source_map_raw = await container.source_repository.list_all()
        source_map = {str(s.id): s for s in source_map_raw}

        category_map_raw = await container.category_repository.list_all()
        known_category_ids = {str(c.id) for c in category_map_raw}

        company_map_raw = await container.company_repository.list_all()
        known_company_ids = {str(c.id) for c in company_map_raw}

        topic_map_raw = await container.topic_repository.list_all()
        known_topic_ids = {str(t.id) for t in topic_map_raw}

        engine = StoryRankingEngine(
            recency_weight=settings.ranking_recency_weight,
            source_trust_weight=settings.ranking_source_trust_weight,
            source_diversity_weight=settings.ranking_source_diversity_weight,
            corroboration_weight=settings.ranking_corroboration_weight,
            company_relevance_weight=settings.ranking_company_relevance_weight,
            category_topic_relevance_weight=settings.ranking_category_topic_relevance_weight,
            article_quality_weight=settings.ranking_article_quality_weight,
            official_announcement_weight=settings.ranking_official_announcement_weight,
            recency_decay_hours=settings.ranking_recency_decay_hours,
        )

        cluster_articles: dict[str, list[Article]] = {}
        for cluster in clusters:
            articles = await container.article_repository.list_by_cluster_id(cluster.id)
            cluster_articles[str(cluster.id)] = articles

        selector = TopStorySelector(ranking_engine=engine)
        ranked_clusters, top_story = selector.rank_and_select(
            clusters=clusters,
            cluster_articles=cluster_articles,
            source_map=source_map,
            known_company_ids=known_company_ids,
            known_topic_ids=known_topic_ids,
            known_category_ids=known_category_ids,
        )

        updates = []
        for ranked in ranked_clusters:
            explanation_parts = [s.explanation for s in ranked.signals if s.explanation]
            explanation = "; ".join(explanation_parts) if explanation_parts else ""
            updates.append((ranked.cluster.id, ranked.score, explanation))

        if updates:
            await container.story_cluster_repository.bulk_update_ranking(updates)

        scores = [r.score for r in ranked_clusters]
        min_score = min(scores) if scores else 0.0
        max_score = max(scores) if scores else 0.0

        logger.info(
            "Daily story ranking completed",
            ranked_clusters=len(ranked_clusters),
            top_story_cluster_id=top_story.top_story_cluster_id,
            top_story_score=top_story.top_story_score,
            min_score=min_score,
            max_score=max_score,
        )

        return {
            "status": "completed",
            "ranked_clusters": str(len(ranked_clusters)),
            "top_story_cluster_id": str(top_story.top_story_cluster_id or ""),
            "top_story_score": str(top_story.top_story_score or ""),
            "min_score": str(min_score),
            "max_score": str(max_score),
        }

    return {"status": "skipped", "reason": "no_container"}


@celery_app.task(
    name="workers.tasks.ranking.rank_stories",
    max_retries=3,
    default_retry_delay=60,
)
async def rank_stories() -> dict[str, str]:
    """
    Rank story clusters for the daily digest.

    This task is idempotent and can be safely retried.
    """
    start = time.monotonic()
    try:
        result = await _rank_stories_impl()
        if result.get("status") == "completed":
            pass
        await record_celery_task_success(_TASK_NAME)
        return result
    except Exception as exc:
        logger.error(
            "Daily story ranking failed",
            error=str(exc),
            exc_info=True,
        )
        await record_celery_task_failure(_TASK_NAME)
        raise
    finally:
        await record_celery_task_duration(_TASK_NAME, time.monotonic() - start)


__all__ = ["rank_stories"]
