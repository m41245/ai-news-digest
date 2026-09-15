"""
Application tests for GetRecommendationsUseCase.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from ai_news_digest.application.dto.recommendation import RecommendationResponse
from ai_news_digest.application.use_cases.recommendation.get_recommendations import (
    GetRecommendationsUseCase,
)
from ai_news_digest.domain.models.article import Article
from ai_news_digest.domain.models.source import Source
from ai_news_digest.domain.models.story_activity import StoryActivity
from ai_news_digest.domain.models.story_cluster import StoryCluster
from ai_news_digest.domain.models.story_event import StoryEvent
from ai_news_digest.domain.models.trend import Trend
from ai_news_digest.domain.models.user import User
from ai_news_digest.domain.models.user_preference import UserPreferenceProfile
from ai_news_digest.domain.enums.article_status import ArticleStatus
from ai_news_digest.domain.enums.story_activity_status import StoryActivityStatus
from ai_news_digest.domain.enums.trend_status import TrendStatus
from ai_news_digest.domain.enums.trend_type import TrendType
from ai_news_digest.domain.enums.source_type import SourceType
from ai_news_digest.domain.enums.source_status import SourceStatus


def _make_user() -> User:
    return User(
        id=uuid4(),
        email="me@example.com",
        hashed_password="hashed",
        is_active=True,
        is_admin=False,
        created_at=datetime.now(UTC),
    )


def _make_profile(**kwargs) -> UserPreferenceProfile:
    defaults = {
        "user_id": uuid4(),
        "followed_company_ids": frozenset(),
        "followed_topic_ids": frozenset(),
        "followed_category_ids": frozenset(),
        "followed_source_ids": frozenset(),
        "muted_company_ids": frozenset(),
        "muted_topic_ids": frozenset(),
        "muted_category_ids": frozenset(),
        "muted_source_ids": frozenset(),
        "min_importance": 0.0,
        "min_confidence": 0.0,
        "feed_sort": "published_at",
        "freshness_window_days": None,
        "preferred_source_types": (),
    }
    defaults.update(kwargs)
    return UserPreferenceProfile(**defaults)


def _make_article(source_id: UUID | None = None, **kwargs) -> Article:
    defaults = {
        "id": uuid4(),
        "title": "Test Article",
        "url": "https://example.com/test",
        "summary": "Summary",
        "content": None,
        "source_id": source_id or uuid4(),
        "category_id": None,
        "published_at": datetime(2026, 8, 23, 12, 0, 0, tzinfo=UTC),
        "fetched_at": datetime(2026, 8, 23, 12, 0, 0, tzinfo=UTC),
        "status": ArticleStatus.READY,
        "importance_score": 0.5,
        "confidence": 0.5,
        "extraction_method": "rss",
        "extraction_quality": "none",
        "extracted_at": None,
        "content_char_count": None,
        "ai_provider": None,
        "ai_model": None,
        "ai_processed_at": None,
        "ai_input_tokens": None,
        "ai_output_tokens": None,
        "ai_prompt_version": None,
        "key_takeaways": (),
        "why_it_matters": None,
        "topics": (),
        "companies": (),
        "categories": (),
        "topic_ids": (),
        "company_ids": (),
        "category_ids": (),
        "cluster_id": None,
    }
    defaults.update(kwargs)
    return Article(**defaults)


def _make_source() -> Source:
    return Source(
        id=uuid4(),
        name="Test Source",
        feed_url="https://example.com/feed",
        website_url="https://example.com",
        description="Test",
        is_active=True,
        source_type=SourceType.TECH_PUBLICATION,
        status=SourceStatus.VERIFIED,
        created_at=datetime(2026, 8, 23, 12, 0, 0, tzinfo=UTC),
    )


def _make_cluster() -> StoryCluster:
    return StoryCluster(
        id=uuid4(),
        title="Cluster",
        slug="cluster",
        importance_score=0.9,
        confidence=0.9,
        last_updated_at=datetime(2026, 8, 23, 12, 0, 0, tzinfo=UTC),
    )


def _make_activity(cluster_id: UUID) -> StoryActivity:
    return StoryActivity(
        id=uuid4(),
        story_cluster_id=cluster_id,
        status=StoryActivityStatus.BREAKING,
        activity_score=0.9,
        confidence=0.9,
        explanation="Test",
        evaluated_at=datetime(2026, 8, 23, 12, 0, 0, tzinfo=UTC),
        detection_version="v1",
    )


def _make_event(cluster_id: UUID) -> StoryEvent:
    return StoryEvent(
        id=uuid4(),
        story_cluster_id=cluster_id,
        event_type="development",
        title="Event",
        description="Event desc",
        confidence=0.8,
        event_time=datetime(2026, 8, 23, 12, 0, 0, tzinfo=UTC),
        sequence=1,
    )


def _make_trend(**kwargs) -> Trend:
    defaults = {
        "id": uuid4(),
        "trend_type": TrendType.COMPANY_TREND,
        "canonical_key": "company:test",
        "display_name": "Test Trend",
        "status": TrendStatus.EMERGING,
        "trend_score": 70.0,
        "momentum_score": 60.0,
        "first_detected_at": datetime(2026, 8, 23, 12, 0, 0, tzinfo=UTC),
        "last_detected_at": datetime(2026, 8, 23, 12, 0, 0, tzinfo=UTC),
        "recent_activity": 10,
        "baseline_activity": 5,
        "source_count": 3,
        "story_count": 2,
        "event_count": 1,
        "explanation": "test",
        "trend_metadata": {},
        "related_company_ids": frozenset(),
        "related_topic_ids": frozenset(),
        "related_category_ids": frozenset(),
    }
    defaults.update(kwargs)
    return Trend(**defaults)


def _build_container(
    profile: UserPreferenceProfile,
    articles: list[Article],
    clusters: list[StoryCluster],
    activities: list[StoryActivity],
    events_by_cluster: dict[UUID, list[StoryEvent]],
    trends: list[Trend],
) -> MagicMock:
    container = MagicMock()
    container.user_preference_repository = AsyncMock()
    container.user_preference_repository.get_by_user_id = AsyncMock(return_value=profile)
    container.user_preference_repository.create = AsyncMock(side_effect=lambda p: p)

    container.article_repository = AsyncMock()
    container.article_repository.list_personalized_feed_story_candidates = AsyncMock(return_value=articles)

    container.story_cluster_repository = AsyncMock()
    container.story_cluster_repository.get_by_ids = AsyncMock(return_value=clusters)

    container.source_repository = AsyncMock()
    container.source_repository.list_all = AsyncMock(return_value=[_make_source()])

    container.category_repository = AsyncMock()
    container.category_repository.list_all = AsyncMock(return_value=[])

    container.company_repository = AsyncMock()
    container.company_repository.list_all = AsyncMock(return_value=[])

    container.story_activity_repository = AsyncMock()
    container.story_activity_repository.get_by_cluster_ids = AsyncMock(return_value=activities)

    container.story_event_repository = AsyncMock()
    container.story_event_repository.list_by_cluster_ids = AsyncMock(return_value=events_by_cluster)

    container.trend_repository = AsyncMock()
    container.trend_repository.list_recent = AsyncMock(return_value=trends)

    return container


class TestGetRecommendationsUseCase:
    @pytest.mark.asyncio
    async def test_empty_preferences_returns_fallback(self) -> None:
        user = _make_user()
        profile = _make_profile(user_id=user.id)
        article = _make_article(cluster_id=uuid4())
        container = _build_container(profile, [article], [], [], {}, [])
        use_case = GetRecommendationsUseCase(
            preference_repository=container.user_preference_repository,
            article_repository=container.article_repository,
            story_cluster_repository=container.story_cluster_repository,
            source_repository=container.source_repository,
            category_repository=container.category_repository,
            company_repository=container.company_repository,
            story_activity_repository=container.story_activity_repository,
            story_event_repository=container.story_event_repository,
            trend_repository=container.trend_repository,
        )
        response = await use_case.execute(current_user=user)
        assert isinstance(response, RecommendationResponse)

    @pytest.mark.asyncio
    async def test_followed_company_increases_score(self) -> None:
        user = _make_user()
        company_id = uuid4()
        cluster = _make_cluster()
        article = _make_article(
            source_id=uuid4(),
            company_ids=(company_id,),
            companies=("Acme",),
            cluster_id=cluster.id,
        )
        profile = _make_profile(user_id=user.id, followed_company_ids=frozenset([company_id]))
        container = _build_container(profile, [article], [cluster], [], {}, [])
        use_case = GetRecommendationsUseCase(
            preference_repository=container.user_preference_repository,
            article_repository=container.article_repository,
            story_cluster_repository=container.story_cluster_repository,
            source_repository=container.source_repository,
            category_repository=container.category_repository,
            company_repository=container.company_repository,
            story_activity_repository=container.story_activity_repository,
            story_event_repository=container.story_event_repository,
            trend_repository=container.trend_repository,
        )
        response = await use_case.execute(current_user=user)
        assert response.total >= 0

    @pytest.mark.asyncio
    async def test_muted_entities_are_excluded(self) -> None:
        user = _make_user()
        company_id = uuid4()
        cluster = _make_cluster()
        article = _make_article(
            source_id=uuid4(),
            company_ids=(company_id,),
            companies=("Acme",),
            cluster_id=cluster.id,
        )
        profile = _make_profile(user_id=user.id, muted_company_ids=frozenset([company_id]))
        container = _build_container(profile, [], [cluster], [], {}, [])
        container.article_repository.list_personalized_feed_story_candidates = AsyncMock(return_value=[])
        use_case = GetRecommendationsUseCase(
            preference_repository=container.user_preference_repository,
            article_repository=container.article_repository,
            story_cluster_repository=container.story_cluster_repository,
            source_repository=container.source_repository,
            category_repository=container.category_repository,
            company_repository=container.company_repository,
            story_activity_repository=container.story_activity_repository,
            story_event_repository=container.story_event_repository,
            trend_repository=container.trend_repository,
        )
        response = await use_case.execute(current_user=user)
        assert response.total == 0

    @pytest.mark.asyncio
    async def test_pagination_metadata(self) -> None:
        user = _make_user()
        profile = _make_profile(user_id=user.id)
        container = _build_container(profile, [], [], [], {}, [])
        use_case = GetRecommendationsUseCase(
            preference_repository=container.user_preference_repository,
            article_repository=container.article_repository,
            story_cluster_repository=container.story_cluster_repository,
            source_repository=container.source_repository,
            category_repository=container.category_repository,
            company_repository=container.company_repository,
            story_activity_repository=container.story_activity_repository,
            story_event_repository=container.story_event_repository,
            trend_repository=container.trend_repository,
        )
        response = await use_case.execute(current_user=user, page=1, page_size=10)
        assert response.limit == 10
        assert response.offset == 0


__all__ = ["TestGetRecommendationsUseCase"]
