"""
Unit tests for personalized feed use case hardening.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from ai_news_digest.application.services.ranking.constants import (
    FeedDefaults,
    RankingWeights,
)
from ai_news_digest.application.use_cases.user_preference.get_personalized_feed import (
    GetPersonalizedFeedUseCase,
)
from ai_news_digest.domain.enums.article_status import ArticleStatus
from ai_news_digest.domain.models.article import Article
from ai_news_digest.domain.models.story_cluster import StoryCluster
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


def _make_article(
    article_id: UUID,
    source_id: UUID,
    cluster_id: UUID | None = None,
) -> Article:
    return Article(
        id=article_id,
        title=f"Article {article_id}",
        url=f"https://example.com/{article_id}",
        summary="Summary",
        content=None,
        source_id=source_id,
        category_id=None,
        published_at=datetime(2026, 8, 23, 12, 0, 0, tzinfo=UTC),
        fetched_at=datetime(2026, 8, 23, 12, 0, 0, tzinfo=UTC),
        status=ArticleStatus.READY,
        importance_score=0.9,
        confidence=0.9,
        company_ids=(),
        topic_ids=(),
        category_ids=(),
        companies=(),
        topics=(),
        categories=(),
        cluster_id=cluster_id,
    )


def _make_story_cluster(cluster_id: UUID) -> StoryCluster:
    return StoryCluster(
        id=cluster_id,
        title="Cluster",
        slug="cluster",
        importance_score=0.9,
        confidence=0.9,
        last_updated_at=datetime(2026, 8, 23, 12, 0, 0, tzinfo=UTC),
    )


@pytest.fixture
def mock_repositories() -> dict[str, Any]:
    return {
        "preference": AsyncMock(spec=UserPreferenceRepository),
        "article": AsyncMock(spec=ArticleRepository),
        "story_cluster": AsyncMock(spec=StoryClusterRepository),
        "source": AsyncMock(spec=SourceRepository),
        "category": AsyncMock(spec=CategoryRepository),
        "company": AsyncMock(spec=CompanyRepository),
    }


@pytest.fixture
def use_case(mock_repositories: dict[str, Any]) -> GetPersonalizedFeedUseCase:
    return GetPersonalizedFeedUseCase(
        preference_repository=mock_repositories["preference"],
        article_repository=mock_repositories["article"],
        story_cluster_repository=mock_repositories["story_cluster"],
        source_repository=mock_repositories["source"],
        category_repository=mock_repositories["category"],
        company_repository=mock_repositories["company"],
    )


@pytest.mark.asyncio
async def test_get_feed_uses_story_level_candidates(
    use_case: GetPersonalizedFeedUseCase,
    mock_repositories: dict[str, Any],
) -> None:
    user = _make_user()
    profile = UserPreferenceProfile(user_id=user.id)
    mock_repositories["preference"].get_by_user_id = AsyncMock(return_value=profile)
    mock_repositories["article"].list_personalized_feed_story_candidates = AsyncMock(
        return_value=[]
    )
    mock_repositories["source"].list_all = AsyncMock(return_value=[])
    mock_repositories["category"].list_all = AsyncMock(return_value=[])

    await use_case.execute(user, page=1, page_size=20)

    mock_repositories["article"].list_personalized_feed_story_candidates.assert_awaited_once()
    call_kwargs = mock_repositories[
        "article"
    ].list_personalized_feed_story_candidates.call_args.kwargs
    assert call_kwargs["limit"] == FeedDefaults.CANDIDATE_LIMIT + 20
    assert call_kwargs["offset"] == 0


@pytest.mark.asyncio
async def test_get_feed_enforces_max_page_size(
    use_case: GetPersonalizedFeedUseCase,
    mock_repositories: dict[str, Any],
) -> None:
    user = _make_user()
    profile = UserPreferenceProfile(user_id=user.id)
    mock_repositories["preference"].get_by_user_id = AsyncMock(return_value=profile)
    mock_repositories["article"].list_personalized_feed_story_candidates = AsyncMock(
        return_value=[]
    )
    mock_repositories["source"].list_all = AsyncMock(return_value=[])
    mock_repositories["category"].list_all = AsyncMock(return_value=[])

    await use_case.execute(user, page=1, page_size=999)

    call_kwargs = mock_repositories[
        "article"
    ].list_personalized_feed_story_candidates.call_args.kwargs
    assert call_kwargs["limit"] == FeedDefaults.CANDIDATE_LIMIT + FeedDefaults.MAX_PAGE_SIZE


@pytest.mark.asyncio
async def test_get_feed_paginates_correctly(
    use_case: GetPersonalizedFeedUseCase,
    mock_repositories: dict[str, Any],
) -> None:
    user = _make_user()
    profile = UserPreferenceProfile(user_id=user.id)
    mock_repositories["preference"].get_by_user_id = AsyncMock(return_value=profile)
    mock_repositories["article"].list_personalized_feed_story_candidates = AsyncMock(
        return_value=[]
    )
    mock_repositories["source"].list_all = AsyncMock(return_value=[])
    mock_repositories["category"].list_all = AsyncMock(return_value=[])

    await use_case.execute(user, page=3, page_size=10)

    call_kwargs = mock_repositories[
        "article"
    ].list_personalized_feed_story_candidates.call_args.kwargs
    assert call_kwargs["limit"] == FeedDefaults.CANDIDATE_LIMIT + 10
    assert call_kwargs["offset"] == 0


@pytest.mark.asyncio
async def test_story_level_deduplication(
    use_case: GetPersonalizedFeedUseCase,
    mock_repositories: dict[str, Any],
) -> None:
    user = _make_user()
    company_id = uuid4()
    cluster_id = uuid4()
    article1 = _make_article(uuid4(), uuid4(), cluster_id=cluster_id)
    article1.company_ids = (company_id,)
    article1.companies = ("Acme",)
    article2 = _make_article(uuid4(), uuid4(), cluster_id=cluster_id)
    article2.company_ids = (company_id,)
    article2.companies = ("Acme",)
    standalone = _make_article(uuid4(), uuid4(), cluster_id=None)

    profile = UserPreferenceProfile(user_id=user.id)
    mock_repositories["preference"].get_by_user_id = AsyncMock(return_value=profile)
    mock_repositories["article"].list_personalized_feed_story_candidates = AsyncMock(
        return_value=[article1, article2, standalone]
    )
    mock_repositories["story_cluster"].get_by_id = AsyncMock(
        return_value=_make_story_cluster(cluster_id)
    )
    mock_repositories["source"].list_all = AsyncMock(return_value=[])
    mock_repositories["category"].list_all = AsyncMock(return_value=[])

    response = await use_case.execute(user, page=1, page_size=20)

    assert response.total == 2
    cluster_items = [item for item in response.items if item.cluster_id == str(cluster_id)]
    assert len(cluster_items) == 1
    assert cluster_items[0].article_count == 2
    standalone_items = [item for item in response.items if item.is_fallback]
    assert len(standalone_items) == 1


@pytest.mark.asyncio
async def test_muted_entities_excluded_before_scoring(
    use_case: GetPersonalizedFeedUseCase,
    mock_repositories: dict[str, Any],
) -> None:
    user = _make_user()
    company_id = uuid4()
    followed_company_id = uuid4()
    article = _make_article(uuid4(), uuid4())
    article.company_ids = (company_id,)
    article.companies = ("Acme",)

    profile = UserPreferenceProfile(
        user_id=user.id,
        followed_company_ids=frozenset([followed_company_id]),
        muted_company_ids=frozenset([company_id]),
    )
    mock_repositories["preference"].get_by_user_id = AsyncMock(return_value=profile)
    mock_repositories["article"].list_personalized_feed_story_candidates = AsyncMock(
        return_value=[]
    )
    mock_repositories["source"].list_all = AsyncMock(return_value=[])
    mock_repositories["category"].list_all = AsyncMock(return_value=[])

    response = await use_case.execute(user, page=1, page_size=20)

    assert response.total == 0
    assert response.empty_reason == "No matching stories found. Try adjusting your filters."


@pytest.mark.asyncio
async def test_ranking_uses_centralized_weights(
    use_case: GetPersonalizedFeedUseCase,
    mock_repositories: dict[str, Any],
) -> None:
    user = _make_user()
    company_id = uuid4()
    topic_id = uuid4()
    category_id = uuid4()
    source_id = uuid4()
    cluster_id = uuid4()
    article = _make_article(uuid4(), source_id, cluster_id=cluster_id)
    article.company_ids = (company_id,)
    article.companies = ("Acme",)
    article.topic_ids = (topic_id,)
    article.topics = ("AI",)
    article.category_ids = (category_id,)
    article.categories = ("Technology",)

    cluster = _make_story_cluster(cluster_id)
    cluster.importance_score = 0.9
    cluster.confidence = 0.9
    cluster.last_updated_at = datetime(2026, 8, 23, 12, 0, 0, tzinfo=UTC)

    source = MagicMock()
    source.id = source_id
    source.name = "Test Source"
    source.source_type.value = "official_company"

    profile = UserPreferenceProfile(
        user_id=user.id,
        followed_company_ids=frozenset([company_id]),
        followed_topic_ids=frozenset([topic_id]),
        followed_category_ids=frozenset([category_id]),
        preferred_source_types=("official_company",),
    )
    mock_repositories["preference"].get_by_user_id = AsyncMock(return_value=profile)
    mock_repositories["article"].list_personalized_feed_story_candidates = AsyncMock(
        return_value=[article]
    )
    mock_repositories["story_cluster"].get_by_id = AsyncMock(return_value=cluster)
    mock_repositories["source"].list_all = AsyncMock(return_value=[source])
    mock_repositories["category"].list_all = AsyncMock(return_value=[])

    response = await use_case.execute(user, page=1, page_size=20)

    assert response.total == 1
    item = response.items[0]
    expected_score = (
        RankingWeights.FOLLOWED_COMPANY
        + RankingWeights.FOLLOWED_TOPIC
        + RankingWeights.FOLLOWED_CATEGORY
        + RankingWeights.HIGH_IMPORTANCE
        + RankingWeights.STRONG_CONFIDENCE
        + RankingWeights.PREFERRED_SOURCE_TYPE
    )
    assert item.relevance_score == expected_score
    assert "Matches followed company" in item.relevance_reasons
    assert "Matches followed topic" in item.relevance_reasons
    assert "Matches followed category" in item.relevance_reasons
    assert "High importance" in item.relevance_reasons
    assert "Strong confidence" in item.relevance_reasons
    assert "Preferred source type" in item.relevance_reasons


@pytest.mark.asyncio
async def test_empty_preferences_empty_state(
    use_case: GetPersonalizedFeedUseCase,
    mock_repositories: dict[str, Any],
) -> None:
    user = _make_user()
    profile = UserPreferenceProfile(user_id=user.id)
    mock_repositories["preference"].get_by_user_id = AsyncMock(return_value=profile)
    mock_repositories["article"].list_personalized_feed_story_candidates = AsyncMock(
        return_value=[]
    )
    mock_repositories["source"].list_all = AsyncMock(return_value=[])
    mock_repositories["category"].list_all = AsyncMock(return_value=[])

    response = await use_case.execute(user, page=1, page_size=20)

    assert response.total == 0
    assert response.empty_reason == "Configure your interests to see personalized stories."


@pytest.mark.asyncio
async def test_preferred_source_types_are_ranking_signal_not_filter(
    use_case: GetPersonalizedFeedUseCase,
    mock_repositories: dict[str, Any],
) -> None:
    user = _make_user()
    source_id = uuid4()
    article = _make_article(uuid4(), source_id)
    article.importance_score = 0.5
    article.confidence = 0.5

    source = MagicMock()
    source.id = source_id
    source.name = "Other Source"
    source.source_type.value = "other"

    profile = UserPreferenceProfile(
        user_id=user.id,
        preferred_source_types=("official_company",),
    )
    mock_repositories["preference"].get_by_user_id = AsyncMock(return_value=profile)
    mock_repositories["article"].list_personalized_feed_story_candidates = AsyncMock(
        return_value=[article]
    )
    mock_repositories["story_cluster"].get_by_id = AsyncMock(return_value=None)
    mock_repositories["source"].list_all = AsyncMock(return_value=[source])
    mock_repositories["category"].list_all = AsyncMock(return_value=[])

    response = await use_case.execute(user, page=1, page_size=20)

    assert response.total == 1
    assert response.items[0].is_fallback is True
    assert "Preferred source type" not in response.items[0].relevance_reasons


@pytest.mark.asyncio
async def test_contradiction_signals_detected(
    use_case: GetPersonalizedFeedUseCase,
    mock_repositories: dict[str, Any],
) -> None:
    user = _make_user()
    cluster_id = uuid4()
    article1 = _make_article(uuid4(), uuid4(), cluster_id=cluster_id)
    article1.title = "OpenAI releases GPT-5 model"
    article2 = _make_article(uuid4(), uuid4(), cluster_id=cluster_id)
    article2.title = "Anthropic Claude passes new Turing test benchmarks"

    profile = UserPreferenceProfile(user_id=user.id)
    mock_repositories["preference"].get_by_user_id = AsyncMock(return_value=profile)
    mock_repositories["article"].list_personalized_feed_story_candidates = AsyncMock(
        return_value=[article1, article2]
    )
    cluster = _make_story_cluster(cluster_id)
    mock_repositories["story_cluster"].get_by_id = AsyncMock(return_value=cluster)
    mock_repositories["source"].list_all = AsyncMock(return_value=[])
    mock_repositories["category"].list_all = AsyncMock(return_value=[])

    response = await use_case.execute(user, page=1, page_size=20)

    assert response.total == 1
    assert response.items[0].contradiction_signals is True


@pytest.mark.asyncio
async def test_ranking_explanation_has_at_least_one_reason(
    use_case: GetPersonalizedFeedUseCase,
    mock_repositories: dict[str, Any],
) -> None:
    user = _make_user()
    article = _make_article(uuid4(), uuid4())
    article.importance_score = 0.3
    article.confidence = 0.3
    article.published_at = datetime(2026, 8, 20, 12, 0, 0, tzinfo=UTC)

    profile = UserPreferenceProfile(user_id=user.id)
    mock_repositories["preference"].get_by_user_id = AsyncMock(return_value=profile)
    mock_repositories["article"].list_personalized_feed_story_candidates = AsyncMock(
        return_value=[article]
    )
    mock_repositories["story_cluster"].get_by_id = AsyncMock(return_value=None)
    mock_repositories["source"].list_all = AsyncMock(return_value=[])
    mock_repositories["category"].list_all = AsyncMock(return_value=[])

    response = await use_case.execute(user, page=1, page_size=20)

    assert response.total == 1
    assert len(response.items[0].relevance_reasons) >= 1


@pytest.mark.asyncio
async def test_followed_entity_filters_passed_to_repository(
    use_case: GetPersonalizedFeedUseCase,
    mock_repositories: dict[str, Any],
) -> None:
    user = _make_user()
    company_id = uuid4()
    topic_id = uuid4()
    category_id = uuid4()
    profile = UserPreferenceProfile(
        user_id=user.id,
        followed_company_ids=frozenset([company_id]),
        followed_topic_ids=frozenset([topic_id]),
        followed_category_ids=frozenset([category_id]),
    )
    mock_repositories["preference"].get_by_user_id = AsyncMock(return_value=profile)
    mock_repositories["article"].list_personalized_feed_story_candidates = AsyncMock(
        return_value=[]
    )
    mock_repositories["source"].list_all = AsyncMock(return_value=[])
    mock_repositories["category"].list_all = AsyncMock(return_value=[])

    await use_case.execute(user, page=1, page_size=20)

    call_kwargs = mock_repositories[
        "article"
    ].list_personalized_feed_story_candidates.call_args.kwargs
    assert company_id in call_kwargs["followed_company_ids"]
    assert topic_id in call_kwargs["followed_topic_ids"]
    assert category_id in call_kwargs["followed_category_ids"]


@pytest.mark.asyncio
async def test_preferred_source_type_ids_passed_to_repository(
    use_case: GetPersonalizedFeedUseCase,
    mock_repositories: dict[str, Any],
) -> None:
    user = _make_user()
    source_id = uuid4()
    source = MagicMock()
    source.id = source_id
    source.name = "Test Source"
    source.source_type.value = "official_company"

    profile = UserPreferenceProfile(
        user_id=user.id,
        preferred_source_types=("official_company",),
    )
    mock_repositories["preference"].get_by_user_id = AsyncMock(return_value=profile)
    mock_repositories["article"].list_personalized_feed_story_candidates = AsyncMock(
        return_value=[]
    )
    mock_repositories["source"].list_all = AsyncMock(return_value=[source])
    mock_repositories["category"].list_all = AsyncMock(return_value=[])

    await use_case.execute(user, page=1, page_size=20)

    call_kwargs = mock_repositories[
        "article"
    ].list_personalized_feed_story_candidates.call_args.kwargs
    assert source_id in call_kwargs["preferred_source_type_ids"]


@pytest.mark.asyncio
async def test_tie_breaking_stability(
    use_case: GetPersonalizedFeedUseCase,
    mock_repositories: dict[str, Any],
) -> None:
    user = _make_user()
    source_id = uuid4()
    article1 = _make_article(uuid4(), source_id, cluster_id=None)
    article1.published_at = datetime(2026, 8, 23, 12, 0, 0, tzinfo=UTC)
    article1.importance_score = 0.8
    article2 = _make_article(uuid4(), source_id, cluster_id=None)
    article2.published_at = datetime(2026, 8, 23, 12, 0, 0, tzinfo=UTC)
    article2.importance_score = 0.8

    profile = UserPreferenceProfile(user_id=user.id)
    mock_repositories["preference"].get_by_user_id = AsyncMock(return_value=profile)
    mock_repositories["article"].list_personalized_feed_story_candidates = AsyncMock(
        return_value=[article1, article2]
    )
    mock_repositories["story_cluster"].get_by_id = AsyncMock(return_value=None)
    mock_repositories["source"].list_all = AsyncMock(return_value=[])
    mock_repositories["category"].list_all = AsyncMock(return_value=[])

    response = await use_case.execute(user, page=1, page_size=20)

    assert response.total == 2
    ids = [item.id for item in response.items]
    assert ids == sorted(ids)


@pytest.mark.asyncio
async def test_empty_page_returns_no_items(
    use_case: GetPersonalizedFeedUseCase,
    mock_repositories: dict[str, Any],
) -> None:
    user = _make_user()
    profile = UserPreferenceProfile(user_id=user.id)
    mock_repositories["preference"].get_by_user_id = AsyncMock(return_value=profile)
    mock_repositories["article"].list_personalized_feed_story_candidates = AsyncMock(
        return_value=[]
    )
    mock_repositories["source"].list_all = AsyncMock(return_value=[])
    mock_repositories["category"].list_all = AsyncMock(return_value=[])

    response = await use_case.execute(user, page=2, page_size=10)

    assert response.items == []
    assert response.offset == 10
    assert response.limit == 10
