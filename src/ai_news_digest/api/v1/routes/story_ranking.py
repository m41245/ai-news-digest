"""
Story ranking and Top Story API endpoints (M68).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from ai_news_digest.api.v1.dependencies.auth import get_current_active_user
from ai_news_digest.api.v1.dependencies.dependencies import get_container
from ai_news_digest.api.v1.schemas.common import (
    DEFAULT_PAGE_LIMIT,
    MAX_OFFSET,
    MAX_PAGE_LIMIT,
)
from ai_news_digest.api.v1.schemas.story_ranking import (
    RankedStoriesResponse,
    StoryRankingResponse,
    StoryRankingSignalResponse,
    TopStoryResponse,
)
from ai_news_digest.application.services.ranking.story_ranking_service import (
    StoryRankingEngine,
)
from ai_news_digest.application.services.ranking.top_story_selector import (
    TopStorySelector,
)
from ai_news_digest.bootstrap.container import Container
from ai_news_digest.core.config import get_settings
from ai_news_digest.domain.models.article import Article
from ai_news_digest.domain.models.user import User

router = APIRouter(
    prefix="/story-ranking",
    tags=["Story Ranking"],
)


@router.get(
    "/top-story",
    response_model=TopStoryResponse,
    summary="Get the current Top Story",
)
async def get_top_story(
    container: Annotated[Container, Depends(get_container)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> TopStoryResponse:
    """Return the highest-ranked eligible StoryCluster for today's digest window."""
    settings = get_settings()
    if not settings.story_ranking_enabled:
        return TopStoryResponse(
            top_story_cluster_id=None,
            top_story_score=None,
            total_candidates=0,
            eligible_candidates=0,
            ranking_window_start=None,
            ranking_window_end=None,
            generated_at=datetime.now(UTC).isoformat(),
        )

    now = datetime.now(UTC)
    cutoff = now - timedelta(hours=settings.ranking_lookback_hours)

    clusters = await container.story_cluster_repository.find_recent_active_clusters(
        cutoff=cutoff,
        limit=settings.ranking_max_candidates,
    )

    if not clusters:
        return TopStoryResponse(
            top_story_cluster_id=None,
            top_story_score=None,
            total_candidates=0,
            eligible_candidates=0,
            ranking_window_start=cutoff.isoformat(),
            ranking_window_end=now.isoformat(),
            generated_at=now.isoformat(),
        )

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
    _, top_story = selector.rank_and_select(
        clusters=clusters,
        cluster_articles=cluster_articles,
        source_map=source_map,
        known_company_ids=known_company_ids,
        known_topic_ids=known_topic_ids,
        known_category_ids=known_category_ids,
    )

    return TopStoryResponse(
        top_story_cluster_id=top_story.top_story_cluster_id,
        top_story_score=top_story.top_story_score,
        total_candidates=top_story.total_candidates,
        eligible_candidates=top_story.eligible_candidates,
        ranking_window_start=top_story.ranking_window_start.isoformat(),
        ranking_window_end=top_story.ranking_window_end.isoformat(),
        generated_at=top_story.generated_at.isoformat(),
    )


@router.get(
    "/clusters",
    response_model=RankedStoriesResponse,
    summary="List ranked story clusters",
)
async def list_ranked_clusters(
    container: Annotated[Container, Depends(get_container)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_LIMIT)] = DEFAULT_PAGE_LIMIT,
    offset: Annotated[int, Query(ge=0, le=MAX_OFFSET)] = 0,
) -> RankedStoriesResponse:
    """Return ranked story clusters with explanation for the current ranking window."""
    settings = get_settings()
    if not settings.story_ranking_enabled:
        return RankedStoriesResponse(
            items=[],
            total=0,
            limit=limit,
            offset=offset,
        )

    now = datetime.now(UTC)
    cutoff = now - timedelta(hours=settings.ranking_lookback_hours)

    clusters = await container.story_cluster_repository.find_recent_active_clusters(
        cutoff=cutoff,
        limit=settings.ranking_max_candidates,
    )

    if not clusters:
        return RankedStoriesResponse(
            items=[],
            total=0,
            limit=limit,
            offset=offset,
        )

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
    ranked_clusters, _ = selector.rank_and_select(
        clusters=clusters,
        cluster_articles=cluster_articles,
        source_map=source_map,
        known_company_ids=known_company_ids,
        known_topic_ids=known_topic_ids,
        known_category_ids=known_category_ids,
    )

    page = offset // limit + 1 if limit > 0 else 1
    start = (page - 1) * limit
    end = start + limit
    page_items = ranked_clusters[start:end]

    items = [
        StoryRankingResponse(
            story_cluster_id=rc.cluster.id,
            score=rc.score,
            rank=rc.rank,
            signals=[
                StoryRankingSignalResponse(
                    name=s.name,
                    normalized_value=s.normalized_value,
                    weight=s.weight,
                    contribution=s.contribution,
                    explanation=s.explanation,
                )
                for s in rc.signals
            ],
            explanation=rc.explanation,
        )
        for rc in page_items
    ]

    return RankedStoriesResponse(
        items=items,
        total=len(ranked_clusters),
        limit=limit,
        offset=offset,
    )


__all__ = ["router"]
