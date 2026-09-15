"""
Unit tests for M83 DetectStoryActivityUseCase.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from ai_news_digest.application.use_cases.story_activity.detect_story_activity import (
    DetectStoryActivityUseCase,
)
from ai_news_digest.domain.enums.article_status import ArticleStatus
from ai_news_digest.domain.enums.source_status import SourceStatus
from ai_news_digest.domain.enums.source_type import SourceType
from ai_news_digest.domain.enums.story_activity_status import StoryActivityStatus
from ai_news_digest.domain.models.article import Article
from ai_news_digest.domain.models.source import Source
from ai_news_digest.domain.models.story_activity import StoryActivity


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


def _make_article_model(
    article_id: UUID,
    cluster_id: UUID,
    source_id: UUID,
    published_at: datetime,
    status: ArticleStatus = ArticleStatus.READY,
) -> Article:
    article = Article.create(
        title=f"Article {article_id}",
        url=f"https://example.com/article/{article_id}",
        summary=f"Summary for article {article_id}",
        content=f"Content for article {article_id}",
        source_id=source_id,
        published_at=published_at,
    )
    article.id = article_id
    article.cluster_id = cluster_id
    article.status = status
    return article


@pytest.fixture
def mock_article_repository() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_source_repository() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_claim_repository() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_conflict_repository() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_story_activity_repository() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_story_cluster_repository() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def use_case(
    mock_article_repository: AsyncMock,
    mock_source_repository: AsyncMock,
    mock_claim_repository: AsyncMock,
    mock_conflict_repository: AsyncMock,
    mock_story_activity_repository: AsyncMock,
    mock_story_cluster_repository: AsyncMock,
) -> DetectStoryActivityUseCase:
    return DetectStoryActivityUseCase(
        article_repository=mock_article_repository,
        source_repository=mock_source_repository,
        claim_repository=mock_claim_repository,
        conflict_repository=mock_conflict_repository,
        story_activity_repository=mock_story_activity_repository,
        story_cluster_repository=mock_story_cluster_repository,
        provider_manager=None,
    )


class TestDisabled:
    @pytest.mark.asyncio
    async def test_disabled_returns_early(
        self,
        use_case: DetectStoryActivityUseCase,
        mock_article_repository: AsyncMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from ai_news_digest.core.config import get_settings

        settings = get_settings()
        new_settings = settings.model_copy(update={"breaking_detection_enabled": False})
        monkeypatch.setattr(use_case, "_settings", new_settings)

        result = await use_case.execute()
        assert result == {"status": "disabled"}
        mock_article_repository._session.execute.assert_not_called()


class TestStale:
    @pytest.mark.asyncio
    async def test_no_candidates_returns_empty(
        self,
        use_case: DetectStoryActivityUseCase,
        mock_article_repository: AsyncMock,
    ) -> None:
        mock_article_repository._session.execute.return_value.scalars.return_value.all.return_value = []  # noqa: E501
        result = await use_case.execute()
        assert result["status"] == "completed"
        assert result["evaluated"] == 0


class TestBreaking:
    @pytest.mark.asyncio
    async def test_high_velocity_many_sources_breaks(
        self,
        use_case: DetectStoryActivityUseCase,
        mock_article_repository: AsyncMock,
        mock_source_repository: AsyncMock,
        mock_claim_repository: AsyncMock,
        mock_conflict_repository: AsyncMock,
        mock_story_activity_repository: AsyncMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from ai_news_digest.core.config import get_settings

        settings = get_settings()


        new_settings = settings.model_copy(


            update={


                "breaking_threshold": 0.3,


                "developing_threshold": 0.1,


                "minimum_independent_sources": 2,


                "max_articles_per_story": 50,


                "max_claims_per_story": 50,


            }


        )


        monkeypatch.setattr(use_case, "_settings", new_settings)

        now = datetime.now(UTC)
        cluster_id = uuid4()
        source_ids = [uuid4() for _ in range(5)]

        cluster = MagicMock()
        cluster.id = cluster_id
        cluster.status = MagicMock()
        cluster.status.value = "active"

        monkeypatch.setattr(use_case, "_get_candidates", AsyncMock(return_value=[cluster]))

        articles = [
            _make_article_model(
                article_id=uuid4(),
                cluster_id=cluster_id,
                source_id=source_ids[i % 5],
                published_at=now - timedelta(minutes=i * 10),
            )
            for i in range(10)
        ]

        mock_article_repository.list_by_cluster_id.return_value = articles
        mock_source_repository.list_all.return_value = [
            _make_source(sid, f"Source {i}") for i, sid in enumerate(source_ids)
        ]
        mock_claim_repository.list_by_article_id.return_value = []
        mock_conflict_repository.list_by_story_cluster_id.return_value = []

        mock_story_activity_repository.get_by_story_cluster_id.return_value = None
        mock_story_activity_repository.upsert.return_value = MagicMock()

        result = await use_case.execute()

        assert result["status"] == "completed"
        assert result["evaluated"] == 1
        mock_story_activity_repository.upsert.assert_called_once()
        activity = mock_story_activity_repository.upsert.call_args[0][0]
        assert activity.status == StoryActivityStatus.BREAKING


class TestDeveloping:
    @pytest.mark.asyncio
    async def test_moderate_activity_is_developing(
        self,
        use_case: DetectStoryActivityUseCase,
        mock_article_repository: AsyncMock,
        mock_source_repository: AsyncMock,
        mock_claim_repository: AsyncMock,
        mock_conflict_repository: AsyncMock,
        mock_story_activity_repository: AsyncMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from ai_news_digest.core.config import get_settings

        settings = get_settings()


        new_settings = settings.model_copy(


            update={


                "breaking_threshold": 0.8,


                "developing_threshold": 0.2,


                "minimum_independent_sources": 5,


                "max_articles_per_story": 50,


                "max_claims_per_story": 50,


            }


        )


        monkeypatch.setattr(use_case, "_settings", new_settings)

        now = datetime.now(UTC)
        cluster_id = uuid4()
        source_ids = [uuid4() for _ in range(3)]

        cluster = MagicMock()
        cluster.id = cluster_id
        cluster.status = MagicMock()
        cluster.status.value = "active"

        monkeypatch.setattr(use_case, "_get_candidates", AsyncMock(return_value=[cluster]))

        articles = [
            _make_article_model(
                article_id=uuid4(),
                cluster_id=cluster_id,
                source_id=source_ids[i % 3],
                published_at=now - timedelta(hours=i),
            )
            for i in range(4)
        ]

        mock_article_repository.list_by_cluster_id.return_value = articles
        mock_source_repository.list_all.return_value = [
            _make_source(sid, f"Source {i}") for i, sid in enumerate(source_ids)
        ]
        mock_claim_repository.list_by_article_id.return_value = []
        mock_conflict_repository.list_by_story_cluster_id.return_value = []

        mock_story_activity_repository.get_by_story_cluster_id.return_value = None
        mock_story_activity_repository.upsert.return_value = MagicMock()

        result = await use_case.execute()

        assert result["status"] == "completed"
        assert result["evaluated"] == 1
        activity = mock_story_activity_repository.upsert.call_args[0][0]
        assert activity.status == StoryActivityStatus.DEVELOPING


class TestOngoing:
    @pytest.mark.asyncio
    async def test_low_activity_is_ongoing(
        self,
        use_case: DetectStoryActivityUseCase,
        mock_article_repository: AsyncMock,
        mock_source_repository: AsyncMock,
        mock_claim_repository: AsyncMock,
        mock_conflict_repository: AsyncMock,
        mock_story_activity_repository: AsyncMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from ai_news_digest.core.config import get_settings

        settings = get_settings()


        new_settings = settings.model_copy(


            update={


                "breaking_threshold": 0.8,


                "developing_threshold": 0.3,


                "minimum_independent_sources": 5,


                "max_articles_per_story": 50,


                "max_claims_per_story": 50,


            }


        )


        monkeypatch.setattr(use_case, "_settings", new_settings)

        now = datetime.now(UTC)
        cluster_id = uuid4()
        source_ids = [uuid4()]

        cluster = MagicMock()
        cluster.id = cluster_id
        cluster.status = MagicMock()
        cluster.status.value = "active"

        monkeypatch.setattr(use_case, "_get_candidates", AsyncMock(return_value=[cluster]))

        articles = [
            _make_article_model(
                article_id=uuid4(),
                cluster_id=cluster_id,
                source_id=source_ids[0],
                published_at=now - timedelta(hours=2),
            )
        ]

        mock_article_repository.list_by_cluster_id.return_value = articles
        mock_source_repository.list_all.return_value = [
            _make_source(source_ids[0], "Source A")
        ]
        mock_claim_repository.list_by_article_id.return_value = []
        mock_conflict_repository.list_by_story_cluster_id.return_value = []

        mock_story_activity_repository.get_by_story_cluster_id.return_value = None
        mock_story_activity_repository.upsert.return_value = MagicMock()

        result = await use_case.execute()

        assert result["status"] == "completed"
        assert result["evaluated"] == 1
        activity = mock_story_activity_repository.upsert.call_args[0][0]
        assert activity.status == StoryActivityStatus.ONGOING


class TestFalsePositives:
    @pytest.mark.asyncio
    async def test_single_article_not_breaking(
        self,
        use_case: DetectStoryActivityUseCase,
        mock_article_repository: AsyncMock,
        mock_source_repository: AsyncMock,
        mock_claim_repository: AsyncMock,
        mock_conflict_repository: AsyncMock,
        mock_story_activity_repository: AsyncMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from ai_news_digest.core.config import get_settings

        settings = get_settings()


        new_settings = settings.model_copy(


            update={


                "breaking_threshold": 0.3,


                "developing_threshold": 0.1,


                "minimum_independent_sources": 2,


                "max_articles_per_story": 50,


                "max_claims_per_story": 50,


            }


        )


        monkeypatch.setattr(use_case, "_settings", new_settings)

        now = datetime.now(UTC)
        cluster_id = uuid4()
        source_id = uuid4()

        cluster = MagicMock()
        cluster.id = cluster_id
        cluster.status = MagicMock()
        cluster.status.value = "active"

        monkeypatch.setattr(use_case, "_get_candidates", AsyncMock(return_value=[cluster]))

        articles = [
            _make_article_model(
                article_id=uuid4(),
                cluster_id=cluster_id,
                source_id=source_id,
                published_at=now - timedelta(minutes=5),
            )
        ]

        mock_article_repository.list_by_cluster_id.return_value = articles
        mock_source_repository.list_all.return_value = [
            _make_source(source_id, "Source A")
        ]
        mock_claim_repository.list_by_article_id.return_value = []
        mock_conflict_repository.list_by_story_cluster_id.return_value = []

        mock_story_activity_repository.get_by_story_cluster_id.return_value = None
        mock_story_activity_repository.upsert.return_value = MagicMock()

        result = await use_case.execute()

        assert result["status"] == "completed"
        assert result["evaluated"] == 1
        activity = mock_story_activity_repository.upsert.call_args[0][0]
        assert activity.status != StoryActivityStatus.BREAKING


class TestIdempotency:
    @pytest.mark.asyncio
    async def test_upsert_replaces_existing(
        self,
        use_case: DetectStoryActivityUseCase,
        mock_article_repository: AsyncMock,
        mock_source_repository: AsyncMock,
        mock_claim_repository: AsyncMock,
        mock_conflict_repository: AsyncMock,
        mock_story_activity_repository: AsyncMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from ai_news_digest.core.config import get_settings

        settings = get_settings()


        new_settings = settings.model_copy(


            update={


                "breaking_threshold": 0.3,


                "developing_threshold": 0.1,


                "minimum_independent_sources": 2,


                "max_articles_per_story": 50,


                "max_claims_per_story": 50,


            }


        )


        monkeypatch.setattr(use_case, "_settings", new_settings)

        now = datetime.now(UTC)
        cluster_id = uuid4()
        source_ids = [uuid4() for _ in range(5)]

        cluster = MagicMock()
        cluster.id = cluster_id
        cluster.status = MagicMock()
        cluster.status.value = "active"

        monkeypatch.setattr(use_case, "_get_candidates", AsyncMock(return_value=[cluster]))

        articles = [
            _make_article_model(
                article_id=uuid4(),
                cluster_id=cluster_id,
                source_id=source_ids[i % 5],
                published_at=now - timedelta(minutes=i * 10),
            )
            for i in range(10)
        ]

        mock_article_repository.list_by_cluster_id.return_value = articles
        mock_source_repository.list_all.return_value = [
            _make_source(sid, f"Source {i}") for i, sid in enumerate(source_ids)
        ]
        mock_claim_repository.list_by_article_id.return_value = []
        mock_conflict_repository.list_by_story_cluster_id.return_value = []

        existing_activity = StoryActivity.create(
            story_cluster_id=cluster_id,
            status=StoryActivityStatus.DEVELOPING,
            activity_score=0.5,
            confidence=0.5,
            explanation="old",
            evaluated_at=now - timedelta(hours=1),
            detection_version="v1",
        )
        mock_story_activity_repository.get_by_story_cluster_id.return_value = existing_activity
        mock_story_activity_repository.upsert.return_value = MagicMock()

        result = await use_case.execute()

        assert result["status"] == "completed"
        assert result["evaluated"] == 1
        mock_story_activity_repository.upsert.assert_called_once()
        activity = mock_story_activity_repository.upsert.call_args[0][0]
        assert activity.status == StoryActivityStatus.BREAKING


__all__ = [
    "TestBreaking",
    "TestDeveloping",
    "TestFalsePositives",
    "TestIdempotency",
    "TestOngoing",
    "TestStale",
]
