"""
Tests for the ClusterArticlesUseCase deterministic clustering strategy.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from ai_news_digest.application.use_cases.story_cluster.cluster_articles import (
    ClusterArticlesUseCase,
)
from ai_news_digest.domain.enums.article_status import ArticleStatus
from ai_news_digest.domain.models.article import Article
from ai_news_digest.domain.models.story_cluster import StoryCluster
from ai_news_digest.domain.ports.article_repository import ArticleRepository
from ai_news_digest.domain.ports.story_cluster_repository import StoryClusterRepository


def _make_article(
    title: str = "Test Article",
    url: str = "https://example.com/article",
    published_at: datetime | None = None,
    companies: tuple[str, ...] = (),
    topics: tuple[str, ...] = (),
    categories: tuple[str, ...] = (),
    importance_score: float | None = None,
    confidence: float | None = None,
    cluster_id=None,
) -> Article:
    source_id = uuid4()
    if published_at is None:
        published_at = datetime(2026, 9, 4, 12, 0, tzinfo=UTC)

    article = Article.create(
        title=title,
        url=url,
        summary="Test summary",
        content=None,
        source_id=source_id,
        published_at=published_at,
    )
    article.status = ArticleStatus.READY
    article.companies = companies
    article.topics = topics
    article.categories = categories
    article.importance_score = importance_score
    article.confidence = confidence
    if cluster_id is not None:
        object.__setattr__(article, "cluster_id", cluster_id)
    return article


def _make_cluster(
    title: str = "Cluster",
    slug: str = "cluster",
    first_published_at: datetime | None = None,
    representative_article_id=None,
    importance_score: float | None = None,
    confidence: float | None = None,
) -> StoryCluster:
    if first_published_at is None:
        first_published_at = datetime(2026, 9, 4, 12, 0, tzinfo=UTC)
    cluster = StoryCluster.create(
        title=title,
        slug=slug,
        first_published_at=first_published_at,
        representative_article_id=representative_article_id,
        importance_score=importance_score,
        confidence=confidence,
    )
    return cluster


@pytest.fixture
def mock_article_repository() -> MagicMock:
    repo = MagicMock(spec=ArticleRepository)
    repo.list_all = AsyncMock(return_value=[])
    repo.list_by_cluster_id = AsyncMock(return_value=[])
    repo.get_by_id = AsyncMock(return_value=None)
    repo.set_cluster = AsyncMock()
    return repo


@pytest.fixture
def mock_cluster_repository() -> MagicMock:
    repo = MagicMock(spec=StoryClusterRepository)
    repo.list_all = AsyncMock(return_value=[])
    repo.get_by_id = AsyncMock(return_value=None)
    repo.create = AsyncMock(side_effect=lambda c: c)
    repo.attach_article = AsyncMock()
    repo.update = AsyncMock(side_effect=lambda c: c)
    return repo


@pytest.mark.asyncio
async def test_new_article_creates_new_cluster(
    mock_article_repository: MagicMock,
    mock_cluster_repository: MagicMock,
) -> None:
    use_case = ClusterArticlesUseCase(
        article_repository=mock_article_repository,
        cluster_repository=mock_cluster_repository,
    )

    article = _make_article(title="OpenAI releases new model")
    mock_cluster_repository.list_all.return_value = []

    await use_case.execute(article)

    mock_cluster_repository.create.assert_called_once()
    created_cluster = mock_cluster_repository.create.call_args[0][0]
    assert created_cluster.title == "OpenAI releases new model"
    assert created_cluster.representative_article_id == article.id


@pytest.mark.asyncio
async def test_idempotent_clustering_when_already_clustered(
    mock_article_repository: MagicMock,
    mock_cluster_repository: MagicMock,
) -> None:
    use_case = ClusterArticlesUseCase(
        article_repository=mock_article_repository,
        cluster_repository=mock_cluster_repository,
    )

    existing_cluster = _make_cluster()
    article = _make_article(cluster_id=existing_cluster.id)
    mock_cluster_repository.list_all.return_value = [existing_cluster]
    mock_cluster_repository.get_by_id.return_value = existing_cluster

    result = await use_case.execute(article)

    assert result is existing_cluster
    mock_cluster_repository.create.assert_not_called()
    mock_article_repository.set_cluster.assert_not_called()


@pytest.mark.asyncio
async def test_high_confidence_title_and_company_match(
    mock_article_repository: MagicMock,
    mock_cluster_repository: MagicMock,
) -> None:
    use_case = ClusterArticlesUseCase(
        article_repository=mock_article_repository,
        cluster_repository=mock_cluster_repository,
    )

    cluster = _make_cluster(
        title="OpenAI announces GPT-5",
        slug="openai-announces-gpt-5",
        first_published_at=datetime(2026, 9, 4, 10, 0, tzinfo=UTC),
        representative_article_id=uuid4(),
    )

    representative_article = _make_article(
        title="OpenAI announces GPT-5",
        url="https://openai.com/gpt-5",
        companies=("OpenAI",),
        published_at=datetime(2026, 9, 4, 10, 0, tzinfo=UTC),
        importance_score=0.9,
        confidence=0.85,
    )
    mock_article_repository.get_by_id.return_value = representative_article

    new_article = _make_article(
        title="OpenAI announces GPT-5",
        url="https://techcrunch.com/openai-gpt-5",
        companies=("OpenAI",),
        published_at=datetime(2026, 9, 4, 12, 0, tzinfo=UTC),
    )

    mock_cluster_repository.list_all.return_value = [cluster]

    result = await use_case.execute(new_article)

    assert result is not None
    mock_article_repository.set_cluster.assert_called_once_with(new_article.id, cluster.id)
    mock_cluster_repository.attach_article.assert_called_once_with(cluster.id, new_article.id)


@pytest.mark.asyncio
async def test_low_confidence_does_not_cluster(
    mock_article_repository: MagicMock,
    mock_cluster_repository: MagicMock,
) -> None:
    use_case = ClusterArticlesUseCase(
        article_repository=mock_article_repository,
        cluster_repository=mock_cluster_repository,
    )

    cluster = _make_cluster(
        title="Unrelated event about quantum computing",
        first_published_at=datetime(2026, 9, 1, 12, 0, tzinfo=UTC),
    )
    mock_cluster_repository.list_all.return_value = [cluster]

    article = _make_article(
        title="Apple releases new iPhone",
        url="https://apple.com/iphone",
        companies=("Apple",),
        published_at=datetime(2026, 9, 4, 12, 0, tzinfo=UTC),
    )

    result = await use_case.execute(article)

    assert result is None
    mock_cluster_repository.create.assert_called_once()
    mock_article_repository.set_cluster.assert_called_once()


@pytest.mark.asyncio
async def test_time_window_behavior(
    mock_article_repository: MagicMock,
    mock_cluster_repository: MagicMock,
) -> None:
    use_case = ClusterArticlesUseCase(
        article_repository=mock_article_repository,
        cluster_repository=mock_cluster_repository,
    )

    cluster = _make_cluster(
        title="AI Regulation Update",
        first_published_at=datetime(2026, 9, 1, 12, 0, tzinfo=UTC),
        representative_article_id=uuid4(),
    )
    representative_article = _make_article(
        title="AI Regulation Update",
        url="https://example.com/ai-regulation",
        published_at=datetime(2026, 9, 1, 12, 0, tzinfo=UTC),
        importance_score=0.7,
        companies=("OpenAI",),
    )
    mock_article_repository.get_by_id.return_value = representative_article

    article_within_7d = _make_article(
        title="AI Regulation Update",
        url="https://example.com/ai-regulation",
        published_at=datetime(2026, 9, 4, 12, 0, tzinfo=UTC),
        companies=("OpenAI",),
    )

    mock_cluster_repository.list_all.return_value = [cluster]
    result = await use_case.execute(article_within_7d)
    assert result is not None

    article_outside_7d = _make_article(
        title="AI Regulation Update",
        url="https://example.com/ai-regulation",
        published_at=datetime(2026, 9, 20, 12, 0, tzinfo=UTC),
        companies=("OpenAI",),
    )
    mock_cluster_repository.reset_mock()
    mock_article_repository.reset_mock()
    result = await use_case.execute(article_outside_7d)
    assert result is None


@pytest.mark.asyncio
async def test_duplicate_prevention(
    mock_article_repository: MagicMock,
    mock_cluster_repository: MagicMock,
) -> None:
    use_case = ClusterArticlesUseCase(
        article_repository=mock_article_repository,
        cluster_repository=mock_cluster_repository,
    )

    cluster = _make_cluster()
    mock_cluster_repository.list_all.return_value = [cluster]

    article = _make_article()
    mock_article_repository.get_by_id.return_value = None

    result1 = await use_case.execute(article)
    assert result1 is None
    assert mock_article_repository.set_cluster.call_count == 1

    created_cluster = mock_cluster_repository.create.call_args[0][0]
    article_with_cluster = _make_article(cluster_id=created_cluster.id)
    mock_cluster_repository.get_by_id.return_value = created_cluster

    result2 = await use_case.execute(article_with_cluster)
    assert result2 is created_cluster


@pytest.mark.asyncio
async def test_representative_article_selection(
    mock_article_repository: MagicMock,
    mock_cluster_repository: MagicMock,
) -> None:
    use_case = ClusterArticlesUseCase(
        article_repository=mock_article_repository,
        cluster_repository=mock_cluster_repository,
    )

    low_importance = _make_article(
        title="OpenAI News",
        url="https://example.com/ai/openai-news",
        published_at=datetime(2026, 9, 1, 12, 0, tzinfo=UTC),
        importance_score=0.3,
        companies=("OpenAI",),
        topics=("ai",),
    )
    high_importance = _make_article(
        title="OpenAI News",
        url="https://example.com/ai/openai-news",
        published_at=datetime(2026, 9, 2, 12, 0, tzinfo=UTC),
        importance_score=0.9,
        companies=("OpenAI",),
        topics=("ai",),
    )

    cluster = _make_cluster(
        title="OpenAI News",
        first_published_at=datetime(2026, 9, 1, 12, 0, tzinfo=UTC),
        representative_article_id=low_importance.id,
    )

    mock_article_repository.get_by_id.side_effect = lambda aid: (
        low_importance
        if aid == low_importance.id
        else high_importance
        if aid == high_importance.id
        else None
    )
    mock_article_repository.list_by_cluster_id.return_value = [low_importance, high_importance]

    new_article = _make_article(
        title="OpenAI News",
        url="https://example.com/ai/openai-news",
        published_at=datetime(2026, 9, 3, 12, 0, tzinfo=UTC),
        importance_score=0.5,
        companies=("OpenAI",),
        topics=("ai",),
    )

    mock_cluster_repository.list_all.return_value = [cluster]
    mock_cluster_repository.update.side_effect = lambda c: c

    result = await use_case.execute(new_article)

    assert result is not None
    assert result.representative_article_id == high_importance.id
