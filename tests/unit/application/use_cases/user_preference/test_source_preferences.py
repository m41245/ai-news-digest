"""
Unit tests for M86 source preference use cases and personalized feed source integration.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from ai_news_digest.application.use_cases.user_preference.follow_source import (
    FollowSourceUseCase,
    UnfollowSourceUseCase,
)
from ai_news_digest.application.use_cases.user_preference.get_personalized_feed import (
    GetPersonalizedFeedUseCase,
)
from ai_news_digest.application.use_cases.user_preference.mute_source import (
    MuteSourceUseCase,
    UnmuteSourceUseCase,
)
from ai_news_digest.domain.enums.article_status import ArticleStatus
from ai_news_digest.domain.enums.source_status import SourceStatus
from ai_news_digest.domain.enums.source_type import SourceType
from ai_news_digest.domain.models.article import Article
from ai_news_digest.domain.models.source import Source
from ai_news_digest.domain.models.user import User
from ai_news_digest.domain.models.user_preference import UserPreferenceProfile
from ai_news_digest.domain.ports.article_repository import ArticleRepository
from ai_news_digest.domain.ports.category_repository import CategoryRepository
from ai_news_digest.domain.ports.company_repository import CompanyRepository
from ai_news_digest.domain.ports.source_repository import SourceRepository
from ai_news_digest.domain.ports.story_cluster_repository import StoryClusterRepository
from ai_news_digest.domain.ports.user_preference_repository import UserPreferenceRepository


def _make_user() -> User:
    return User(
        id=uuid4(),
        email="me@example.com",
        hashed_password="hashed",  # noqa: S106
        is_active=True,
        is_admin=False,
        created_at=datetime.now(UTC),
    )


def _make_source() -> Source:
    return Source(
        id=uuid4(),
        name="Test Source",
        feed_url="https://example.com/feed",
        website_url=None,
        description=None,
        is_active=True,
        source_type=SourceType.TECH_PUBLICATION,
        status=SourceStatus.VERIFIED,
        created_at=datetime.now(UTC),
    )


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


@pytest.fixture
def mock_preference_repo() -> AsyncMock:
    return AsyncMock(spec=UserPreferenceRepository)


@pytest.fixture
def mock_source_repo() -> AsyncMock:
    return AsyncMock(spec=SourceRepository)


class TestFollowSourceUseCase:
    @pytest.mark.asyncio
    async def test_execute_calls_repository(self, mock_preference_repo: AsyncMock) -> None:
        user = _make_user()
        source = _make_source()
        use_case = FollowSourceUseCase(preference_repository=mock_preference_repo)
        await use_case.execute(user, source.id)
        mock_preference_repo.add_followed_source.assert_awaited_once_with(user.id, source.id)


class TestUnfollowSourceUseCase:
    @pytest.mark.asyncio
    async def test_execute_calls_repository(self, mock_preference_repo: AsyncMock) -> None:
        user = _make_user()
        source = _make_source()
        use_case = UnfollowSourceUseCase(preference_repository=mock_preference_repo)
        await use_case.execute(user, source.id)
        mock_preference_repo.remove_followed_source.assert_awaited_once_with(user.id, source.id)


class TestMuteSourceUseCase:
    @pytest.mark.asyncio
    async def test_execute_calls_repository(self, mock_preference_repo: AsyncMock) -> None:
        user = _make_user()
        source = _make_source()
        use_case = MuteSourceUseCase(preference_repository=mock_preference_repo)
        await use_case.execute(user, source.id)
        mock_preference_repo.add_muted_source.assert_awaited_once_with(user.id, source.id)


class TestUnmuteSourceUseCase:
    @pytest.mark.asyncio
    async def test_execute_calls_repository(self, mock_preference_repo: AsyncMock) -> None:
        user = _make_user()
        source = _make_source()
        use_case = UnmuteSourceUseCase(preference_repository=mock_preference_repo)
        await use_case.execute(user, source.id)
        mock_preference_repo.remove_muted_source.assert_awaited_once_with(user.id, source.id)


class TestPersonalizedFeedSourceIntegration:
    @pytest.fixture
    def use_case(self) -> GetPersonalizedFeedUseCase:
        return GetPersonalizedFeedUseCase(
            preference_repository=AsyncMock(spec=UserPreferenceRepository),
            article_repository=AsyncMock(spec=ArticleRepository),
            story_cluster_repository=AsyncMock(spec=StoryClusterRepository),
            source_repository=AsyncMock(spec=SourceRepository),
            category_repository=AsyncMock(spec=CategoryRepository),
            company_repository=AsyncMock(spec=CompanyRepository),
        )

    @pytest.mark.asyncio
    async def test_muted_source_excluded_before_scoring(
        self, use_case: GetPersonalizedFeedUseCase
    ) -> None:
        user = _make_user()
        source_id = uuid4()
        _make_article(source_id=source_id)

        profile = UserPreferenceProfile(
            user_id=user.id,
            muted_source_ids=frozenset([source_id]),
        )
        use_case._preference_repository.get_by_user_id = AsyncMock(return_value=profile)
        use_case._article_repository.list_personalized_feed_story_candidates = (
            AsyncMock(return_value=[])
        )
        use_case._source_repository.list_all = AsyncMock(return_value=[])
        use_case._category_repository.list_all = AsyncMock(return_value=[])

        await use_case.execute(user, page=1, page_size=20)
        call_kwargs = (
            use_case._article_repository.list_personalized_feed_story_candidates.call_args.kwargs
        )
        assert source_id in call_kwargs["muted_source_ids"]

    @pytest.mark.asyncio
    async def test_followed_source_boosts_score(
        self, use_case: GetPersonalizedFeedUseCase
    ) -> None:
        user = _make_user()
        source_id = uuid4()
        article = _make_article(source_id=source_id)

        source = MagicMock()
        source.id = source_id
        source.name = "Test Source"
        source.source_type.value = "tech_publication"

        profile = UserPreferenceProfile(
            user_id=user.id,
            followed_source_ids=frozenset([source_id]),
        )
        use_case._preference_repository.get_by_user_id = AsyncMock(return_value=profile)
        use_case._article_repository.list_personalized_feed_story_candidates = AsyncMock(
            return_value=[article]
        )
        use_case._story_cluster_repository.get_by_id = AsyncMock(return_value=None)
        use_case._source_repository.list_all = AsyncMock(return_value=[source])
        use_case._category_repository.list_all = AsyncMock(return_value=[])

        response = await use_case.execute(user, page=1, page_size=20)
        assert response.total == 1
        assert any(
            "followed source" in r.lower() for r in response.items[0].relevance_reasons
        )
