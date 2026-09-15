"""
Unit tests for M85 DetectTrendsUseCase.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from ai_news_digest.application.use_cases.trend.detect_trends import DetectTrendsUseCase
from ai_news_digest.domain.enums.source_status import SourceStatus
from ai_news_digest.domain.enums.source_type import SourceType
from ai_news_digest.domain.enums.story_activity_status import StoryActivityStatus
from ai_news_digest.domain.enums.trend_status import TrendStatus
from ai_news_digest.domain.enums.trend_type import TrendType
from ai_news_digest.domain.models.article import Article
from ai_news_digest.domain.models.source import Source
from ai_news_digest.domain.models.trend import Trend


def _make_source(
    source_id: UUID,
    name: str,
    is_active: bool = True,
    status: SourceStatus = SourceStatus.VERIFIED,
    source_type: SourceType = SourceType.TECH_PUBLICATION,
) -> Source:
    return Source(
        id=source_id,
        name=name,
        feed_url=f"https://example.com/feed/{source_id}",
        website_url=f"https://example.com/{source_id}",
        description=f"Source {name}",
        is_active=is_active,
        source_type=source_type,
        status=status,
        created_at=datetime.now(UTC),
    )


def _make_article(
    article_id: UUID,
    source_id: UUID,
    published_at: datetime,
    company_ids: tuple[UUID, ...] = (),
    topic_ids: tuple[UUID, ...] = (),
    category_id: UUID | None = None,
    cluster_id: UUID | None = None,
) -> Article:
    article = Article.create(
        title=f"Article {article_id}",
        url=f"https://example.com/article/{article_id}",
        summary=f"Summary for article {article_id}",
        content=None,
        source_id=source_id,
        published_at=published_at,
        category_id=category_id,
    )
    article.id = article_id
    article.company_ids = company_ids
    article.topic_ids = topic_ids
    article.cluster_id = cluster_id
    article.status = article.status
    return article


@pytest.fixture
def mock_article_repository() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_source_repository() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_topic_repository() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_company_repository() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_category_repository() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_story_cluster_repository() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_story_activity_repository() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_story_event_repository() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_trend_repository() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def use_case(
    mock_article_repository: AsyncMock,
    mock_source_repository: AsyncMock,
    mock_topic_repository: AsyncMock,
    mock_company_repository: AsyncMock,
    mock_category_repository: AsyncMock,
    mock_story_cluster_repository: AsyncMock,
    mock_story_activity_repository: AsyncMock,
    mock_story_event_repository: AsyncMock,
    mock_trend_repository: AsyncMock,
) -> DetectTrendsUseCase:
    return DetectTrendsUseCase(
        article_repository=mock_article_repository,
        source_repository=mock_source_repository,
        topic_repository=mock_topic_repository,
        company_repository=mock_company_repository,
        category_repository=mock_category_repository,
        story_cluster_repository=mock_story_cluster_repository,
        story_activity_repository=mock_story_activity_repository,
        story_event_repository=mock_story_event_repository,
        trend_repository=mock_trend_repository,
        provider_manager=None,
    )


class TestDisabled:
    @pytest.mark.asyncio
    async def test_disabled_returns_early(
        self,
        use_case: DetectTrendsUseCase,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from ai_news_digest.core.config import get_settings

        settings = get_settings()
        new_settings = settings.model_copy(update={"trend_detection_enabled": False})
        monkeypatch.setattr(use_case, "_settings", new_settings)

        result = await use_case.execute()
        assert result == {"status": "disabled"}


class TestNoCandidates:
    @pytest.mark.asyncio
    async def test_no_candidates_returns_empty(
        self,
        use_case: DetectTrendsUseCase,
        mock_article_repository: AsyncMock,
        mock_source_repository: AsyncMock,
        mock_trend_repository: AsyncMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        mock_source_repository.list_all.return_value = []
        mock_trend_repository.list_recent.return_value = []
        mock_article_repository.list_public_articles_for_feed.return_value = []

        result = await use_case.execute()
        assert result["status"] == "completed"
        assert result["evaluated"] == 0


class TestTrendScore:
    @pytest.mark.asyncio
    async def test_high_growth_creates_emerging_trend(
        self,
        use_case: DetectTrendsUseCase,
        mock_article_repository: AsyncMock,
        mock_source_repository: AsyncMock,
        mock_company_repository: AsyncMock,
        mock_category_repository: AsyncMock,
        mock_topic_repository: AsyncMock,
        mock_story_cluster_repository: AsyncMock,
        mock_story_activity_repository: AsyncMock,
        mock_story_event_repository: AsyncMock,
        mock_trend_repository: AsyncMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from ai_news_digest.core.config import get_settings

        settings = get_settings()
        new_settings = settings.model_copy(
            update={
                "trend_min_recent_activity": 1,
                "trend_min_sources": 1,
                "trend_max_candidates_per_type": 10,
                "trend_max_total_candidates": 10,
            }
        )
        monkeypatch.setattr(use_case, "_settings", new_settings)

        now = datetime.now(UTC)
        company_id = uuid4()
        source_id = uuid4()
        cluster_id = uuid4()

        company = MagicMock()
        company.id = company_id
        company.name = "OpenAI"
        company.article_count = 10

        mock_company_repository.list_all_with_counts.return_value = [company]
        mock_source_repository.list_all.return_value = [
            _make_source(source_id, "Source A")
        ]
        mock_category_repository.list_all.return_value = []
        mock_topic_repository.list_all_with_counts.return_value = []

        recent_articles = [
            _make_article(
                article_id=uuid4(),
                source_id=source_id,
                published_at=now - timedelta(hours=1),
                company_ids=(company_id,),
                cluster_id=cluster_id,
            )
            for _ in range(5)
        ]
        baseline_articles = [
            _make_article(
                article_id=uuid4(),
                source_id=source_id,
                published_at=now - timedelta(days=3),
                company_ids=(company_id,),
            )
            for _ in range(2)
        ]

        def article_filter(*, published_from=None, published_to=None, limit=100, **kwargs):
            if published_from and published_to is None:
                return recent_articles[:limit]
            if published_from and published_to:
                return baseline_articles[:limit]
            return []

        mock_article_repository.list_public_articles_for_feed.side_effect = article_filter
        mock_article_repository.list_by_cluster_id.return_value = recent_articles
        mock_story_cluster_repository.find_recent_active_clusters.return_value = []
        mock_story_activity_repository.list_recent.return_value = []
        mock_story_event_repository.list_by_cluster_id.return_value = []
        mock_trend_repository.get_by_canonical_key.return_value = None
        mock_trend_repository.upsert.return_value = MagicMock()

        result = await use_case.execute()

        assert result["status"] == "completed"
        assert result["evaluated"] >= 1
        mock_trend_repository.upsert.assert_called_once()
        trend = mock_trend_repository.upsert.call_args[0][0]
        assert trend.trend_type == TrendType.COMPANY_TREND
        assert trend.display_name == "OpenAI"
        assert trend.status in (TrendStatus.EMERGING, TrendStatus.RISING, TrendStatus.SUSTAINED)


class TestIdempotency:
    @pytest.mark.asyncio
    async def test_upsert_updates_existing_trend(
        self,
        use_case: DetectTrendsUseCase,
        mock_article_repository: AsyncMock,
        mock_source_repository: AsyncMock,
        mock_company_repository: AsyncMock,
        mock_category_repository: AsyncMock,
        mock_topic_repository: AsyncMock,
        mock_story_cluster_repository: AsyncMock,
        mock_story_activity_repository: AsyncMock,
        mock_story_event_repository: AsyncMock,
        mock_trend_repository: AsyncMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from ai_news_digest.core.config import get_settings

        settings = get_settings()
        new_settings = settings.model_copy(
            update={
                "trend_min_recent_activity": 1,
                "trend_min_sources": 1,
                "trend_max_candidates_per_type": 10,
                "trend_max_total_candidates": 10,
            }
        )
        monkeypatch.setattr(use_case, "_settings", new_settings)

        now = datetime.now(UTC)
        company_id = uuid4()
        source_id = uuid4()

        company = MagicMock()
        company.id = company_id
        company.name = "OpenAI"
        company.article_count = 10

        mock_company_repository.list_all_with_counts.return_value = [company]
        mock_source_repository.list_all.return_value = [
            _make_source(source_id, "Source A")
        ]
        mock_category_repository.list_all.return_value = []
        mock_topic_repository.list_all_with_counts.return_value = []

        recent_articles = [
            _make_article(
                article_id=uuid4(),
                source_id=source_id,
                published_at=now - timedelta(hours=1),
                company_ids=(company_id,),
            )
            for _ in range(5)
        ]
        baseline_articles = [
            _make_article(
                article_id=uuid4(),
                source_id=source_id,
                published_at=now - timedelta(days=3),
                company_ids=(company_id,),
            )
            for _ in range(2)
        ]

        def article_filter(*, published_from=None, published_to=None, limit=100, **kwargs):
            if published_from and published_to is None:
                return recent_articles[:limit]
            if published_from and published_to:
                return baseline_articles[:limit]
            return []

        mock_article_repository.list_public_articles_for_feed.side_effect = article_filter
        mock_article_repository.list_by_cluster_id.return_value = []
        mock_story_cluster_repository.find_recent_active_clusters.return_value = []
        mock_story_activity_repository.list_recent.return_value = []
        mock_story_event_repository.list_by_cluster_id.return_value = []

        existing_trend = Trend.create(
            trend_type=TrendType.COMPANY_TREND,
            canonical_key="company:openai",
            display_name="OpenAI",
            status=TrendStatus.SUSTAINED,
            trend_score=40.0,
            momentum_score=30.0,
            first_detected_at=now - timedelta(days=1),
            last_detected_at=now - timedelta(hours=6),
            recent_activity=5,
            baseline_activity=5,
            source_count=1,
            story_count=0,
            event_count=0,
            explanation="old",
        )
        mock_trend_repository.get_by_canonical_key.return_value = existing_trend
        mock_trend_repository.upsert.return_value = existing_trend

        result = await use_case.execute()

        assert result["status"] == "completed"
        mock_trend_repository.upsert.assert_called_once()
        trend = mock_trend_repository.upsert.call_args[0][0]
        assert trend.canonical_key == "company:openai"


class TestStatusThresholds:
    @pytest.mark.asyncio
    async def test_status_is_deterministic_from_score(
        self,
        use_case: DetectTrendsUseCase,
        mock_article_repository: AsyncMock,
        mock_source_repository: AsyncMock,
        mock_company_repository: AsyncMock,
        mock_category_repository: AsyncMock,
        mock_topic_repository: AsyncMock,
        mock_story_cluster_repository: AsyncMock,
        mock_story_activity_repository: AsyncMock,
        mock_story_event_repository: AsyncMock,
        mock_trend_repository: AsyncMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from ai_news_digest.core.config import get_settings

        settings = get_settings()
        new_settings = settings.model_copy(
            update={
                "trend_min_recent_activity": 1,
                "trend_min_sources": 1,
                "trend_max_candidates_per_type": 10,
                "trend_max_total_candidates": 10,
            }
        )
        monkeypatch.setattr(use_case, "_settings", new_settings)

        now = datetime.now(UTC)
        company_id = uuid4()
        source_id = uuid4()

        company = MagicMock()
        company.id = company_id
        company.name = "OpenAI"
        company.article_count = 10

        mock_company_repository.list_all_with_counts.return_value = [company]
        mock_source_repository.list_all.return_value = [
            _make_source(source_id, "Source A")
        ]
        mock_category_repository.list_all.return_value = []
        mock_topic_repository.list_all_with_counts.return_value = []

        recent_articles = [
            _make_article(
                article_id=uuid4(),
                source_id=source_id,
                published_at=now - timedelta(hours=1),
                company_ids=(company_id,),
            )
            for _ in range(5)
        ]
        baseline_articles = [
            _make_article(
                article_id=uuid4(),
                source_id=source_id,
                published_at=now - timedelta(days=3),
                company_ids=(company_id,),
            )
            for _ in range(2)
        ]

        def article_filter(*, published_from=None, published_to=None, limit=100, **kwargs):
            if published_from and published_to is None:
                return recent_articles[:limit]
            if published_from and published_to:
                return baseline_articles[:limit]
            return []

        mock_article_repository.list_public_articles_for_feed.side_effect = article_filter
        mock_article_repository.list_by_cluster_id.return_value = []
        mock_story_cluster_repository.find_recent_active_clusters.return_value = []
        mock_story_activity_repository.list_recent.return_value = []
        mock_story_event_repository.list_by_cluster_id.return_value = []
        mock_trend_repository.get_by_canonical_key.return_value = None
        mock_trend_repository.upsert.return_value = MagicMock()

        await use_case.execute()

        trend = mock_trend_repository.upsert.call_args[0][0]
        assert trend.trend_score >= 0.0
        assert trend.trend_score <= 100.0
        assert trend.momentum_score >= 0.0
        assert trend.momentum_score <= 100.0
        assert trend.status in (
            TrendStatus.EMERGING,
            TrendStatus.RISING,
            TrendStatus.SUSTAINED,
            TrendStatus.COOLING,
            TrendStatus.STALE,
        )


__all__ = [
    "TestDisabled",
    "TestIdempotency",
    "TestNoCandidates",
    "TestStatusThresholds",
    "TestTrendScore",
]
