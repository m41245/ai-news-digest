"""
Unit tests for SemanticDuplicateDetector.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from ai_news_digest.application.services.semantic_duplicate_detector import (
    SemanticDuplicateDetector,
)
from ai_news_digest.domain.enums.article_status import ArticleStatus
from ai_news_digest.domain.enums.semantic_match_type import SemanticMatchType
from ai_news_digest.domain.models.article import Article
from ai_news_digest.domain.models.story_cluster import StoryCluster
from ai_news_digest.domain.ports.article_repository import ArticleRepository


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
    first_published_at: datetime | None = None,
    representative_article_id=None,
) -> StoryCluster:
    if first_published_at is None:
        first_published_at = datetime(2026, 9, 4, 12, 0, tzinfo=UTC)
    return StoryCluster.create(
        title=title,
        slug="cluster",
        first_published_at=first_published_at,
        representative_article_id=representative_article_id,
    )


@pytest.fixture
def detector() -> SemanticDuplicateDetector:
    return SemanticDuplicateDetector(
        semantic_duplicate_threshold=0.65,
        related_story_threshold=0.4,
        story_time_window_hours=72,
    )


@pytest.mark.asyncio
async def test_identical_titles_are_semantic_duplicates(
    detector: SemanticDuplicateDetector,
) -> None:
    article = _make_article(title="OpenAI launches new model")
    cluster = _make_cluster(title="OpenAI launches new model")
    mock_repo = MagicMock(spec=ArticleRepository)
    mock_repo.get_by_id = AsyncMock(return_value=None)

    result = await detector.compare_with_cluster(article, cluster, mock_repo)

    assert result.match_type == SemanticMatchType.SEMANTIC_DUPLICATE
    assert result.score >= 0.65
    assert result.candidate_id == cluster.id


@pytest.mark.asyncio
async def test_completely_different_titles_are_new_story(
    detector: SemanticDuplicateDetector,
) -> None:
    article = _make_article(title="Apple releases new iPhone")
    cluster = _make_cluster(title="NVIDIA reports quarterly earnings")
    mock_repo = MagicMock(spec=ArticleRepository)
    mock_repo.get_by_id = AsyncMock(return_value=None)

    result = await detector.compare_with_cluster(article, cluster, mock_repo)

    assert result.match_type == SemanticMatchType.NEW_STORY
    assert result.score < 0.4


@pytest.mark.asyncio
async def test_same_company_unrelated_event_not_merged(
    detector: SemanticDuplicateDetector,
) -> None:
    article = _make_article(
        title="OpenAI launches new model",
        companies=("OpenAI",),
    )
    cluster = _make_cluster(
        title="OpenAI signs $5B infrastructure deal",
        representative_article_id=uuid4(),
    )
    rep_article = _make_article(
        title="OpenAI signs $5B infrastructure deal",
        companies=("OpenAI",),
    )
    mock_repo = MagicMock(spec=ArticleRepository)
    mock_repo.get_by_id = AsyncMock(return_value=rep_article)

    result = await detector.compare_with_cluster(article, cluster, mock_repo)

    assert result.match_type != SemanticMatchType.SEMANTIC_DUPLICATE


@pytest.mark.asyncio
async def test_shared_companies_boost_score(
    detector: SemanticDuplicateDetector,
) -> None:
    article = _make_article(
        title="OpenAI unveils enterprise AI model",
        companies=("OpenAI", "Microsoft"),
    )
    cluster = _make_cluster(
        title="OpenAI announces new enterprise-focused model",
        representative_article_id=uuid4(),
    )
    rep_article = _make_article(
        title="OpenAI announces new enterprise-focused model",
        companies=("OpenAI", "Microsoft"),
    )
    mock_repo = MagicMock(spec=ArticleRepository)
    mock_repo.get_by_id = AsyncMock(return_value=rep_article)

    result = await detector.compare_with_cluster(article, cluster, mock_repo)

    assert result.score > 0.4
    assert "shared_companies:2" in result.signals


@pytest.mark.asyncio
async def test_time_proximity_boost(
    detector: SemanticDuplicateDetector,
) -> None:
    now = datetime(2026, 9, 4, 12, 0, tzinfo=UTC)
    article = _make_article(
        title="OpenAI new model",
        published_at=now,
    )
    cluster = _make_cluster(
        title="OpenAI new model",
        first_published_at=now,
        representative_article_id=uuid4(),
    )
    rep_article = _make_article(
        title="OpenAI new model",
        published_at=now,
    )
    mock_repo = MagicMock(spec=ArticleRepository)
    mock_repo.get_by_id = AsyncMock(return_value=rep_article)

    result = await detector.compare_with_cluster(article, cluster, mock_repo)

    assert "within_24h" in result.signals
    assert result.score >= 0.65


@pytest.mark.asyncio
async def test_outside_time_window_penalized(
    detector: SemanticDuplicateDetector,
) -> None:
    article = _make_article(
        title="OpenAI new model",
        published_at=datetime(2026, 9, 4, 12, 0, tzinfo=UTC),
    )
    cluster = _make_cluster(
        title="OpenAI new model",
        first_published_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        representative_article_id=uuid4(),
    )
    rep_article = _make_article(
        title="OpenAI new model",
        published_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
    )
    mock_repo = MagicMock(spec=ArticleRepository)
    mock_repo.get_by_id = AsyncMock(return_value=rep_article)

    result = await detector.compare_with_cluster(article, cluster, mock_repo)

    assert "outside_time_window" in result.signals


@pytest.mark.asyncio
async def test_case_and_punctuation_insensitive(
    detector: SemanticDuplicateDetector,
) -> None:
    article = _make_article(title='OpenAI "Launches" New Model!!!')
    cluster = _make_cluster(title="openai launches new model")
    mock_repo = MagicMock(spec=ArticleRepository)
    mock_repo.get_by_id = AsyncMock(return_value=None)

    result = await detector.compare_with_cluster(article, cluster, mock_repo)

    assert result.match_type == SemanticMatchType.SEMANTIC_DUPLICATE


@pytest.mark.asyncio
async def test_same_domain_boost(
    detector: SemanticDuplicateDetector,
) -> None:
    article = _make_article(
        title="OpenAI launches new model",
        url="https://openai.com/blog/new-model",
    )
    cluster = _make_cluster(
        title="OpenAI launches new model",
        representative_article_id=uuid4(),
    )
    rep_article = _make_article(
        title="OpenAI launches new model",
        url="https://openai.com/blog/new-model",
    )
    mock_repo = MagicMock(spec=ArticleRepository)
    mock_repo.get_by_id = AsyncMock(return_value=rep_article)

    result = await detector.compare_with_cluster(article, cluster, mock_repo)

    assert "same_domain" in result.signals


@pytest.mark.asyncio
async def test_cluster_representative_load_failure_is_ignored(
    detector: SemanticDuplicateDetector,
) -> None:
    article = _make_article(title="OpenAI launches new model")
    cluster = _make_cluster(
        title="OpenAI launches new model",
        representative_article_id=uuid4(),
    )
    mock_repo = MagicMock(spec=ArticleRepository)
    mock_repo.get_by_id = AsyncMock(side_effect=RuntimeError("boom"))

    result = await detector.compare_with_cluster(article, cluster, mock_repo)

    assert result.match_type == SemanticMatchType.SEMANTIC_DUPLICATE


@pytest.mark.asyncio
async def test_cluster_medium_jaccard_branch(
    detector: SemanticDuplicateDetector,
) -> None:
    article = _make_article(title="OpenAI launches enterprise model")
    cluster = _make_cluster(title="OpenAI launches enterprise platform")
    mock_repo = MagicMock(spec=ArticleRepository)
    mock_repo.get_by_id = AsyncMock(return_value=None)

    result = await detector.compare_with_cluster(article, cluster, mock_repo)

    assert any(s.startswith("medium_title_jaccard") for s in result.signals)


@pytest.mark.asyncio
async def test_cluster_low_jaccard_branch(
    detector: SemanticDuplicateDetector,
) -> None:
    article = _make_article(title="OpenAI launches new model today")
    cluster = _make_cluster(title="OpenAI launches product update")
    mock_repo = MagicMock(spec=ArticleRepository)
    mock_repo.get_by_id = AsyncMock(return_value=None)

    result = await detector.compare_with_cluster(article, cluster, mock_repo)

    assert any(s.startswith("low_title_jaccard") for s in result.signals)


@pytest.mark.asyncio
async def test_cluster_shared_topics_and_category_branches(
    detector: SemanticDuplicateDetector,
) -> None:
    article = _make_article(
        title="OpenAI launches new model",
        topics=("ai", "ml"),
        categories=("tech",),
    )
    cluster = _make_cluster(
        title="OpenAI launches new model",
        representative_article_id=uuid4(),
    )
    rep_article = _make_article(
        title="OpenAI launches new model",
        topics=("ai", "ml"),
        categories=("tech",),
    )
    mock_repo = MagicMock(spec=ArticleRepository)
    mock_repo.get_by_id = AsyncMock(return_value=rep_article)

    result = await detector.compare_with_cluster(article, cluster, mock_repo)

    assert "shared_topics:2" in result.signals
    assert "shared_category:1" in result.signals


@pytest.mark.asyncio
async def test_cluster_time_window_branches(
    detector: SemanticDuplicateDetector,
) -> None:
    now = datetime(2026, 9, 4, 12, 0, tzinfo=UTC)
    article = _make_article(title="OpenAI new model", published_at=now)
    cluster = _make_cluster(
        title="OpenAI new model",
        first_published_at=now - timedelta(hours=48),
        representative_article_id=uuid4(),
    )
    rep_article = _make_article(
        title="OpenAI new model",
        published_at=now - timedelta(hours=48),
    )
    mock_repo = MagicMock(spec=ArticleRepository)
    mock_repo.get_by_id = AsyncMock(return_value=rep_article)

    result = await detector.compare_with_cluster(article, cluster, mock_repo)

    assert "within_window" in result.signals

    article2 = _make_article(
        title="OpenAI new model",
        published_at=now,
    )
    cluster2 = _make_cluster(
        title="OpenAI new model",
        first_published_at=now - timedelta(days=5),
        representative_article_id=uuid4(),
    )
    rep_article2 = _make_article(
        title="OpenAI new model",
        published_at=now - timedelta(days=5),
    )
    mock_repo2 = MagicMock(spec=ArticleRepository)
    mock_repo2.get_by_id = AsyncMock(return_value=rep_article2)

    result2 = await detector.compare_with_cluster(article2, cluster2, mock_repo2)

    assert "within_7d" in result2.signals


@pytest.mark.asyncio
async def test_compare_with_article_identical(
    detector: SemanticDuplicateDetector,
) -> None:
    now = datetime(2026, 9, 4, 12, 0, tzinfo=UTC)
    article = _make_article(
        title="OpenAI launches new model",
        url="https://openai.com/blog/new-model",
        published_at=now,
        companies=("OpenAI", "Microsoft"),
        topics=("ai", "ml"),
        categories=("tech",),
    )
    candidate = _make_article(
        title="OpenAI launches new model",
        url="https://openai.com/blog/new-model",
        published_at=now,
        companies=("OpenAI", "Microsoft"),
        topics=("ai", "ml"),
        categories=("tech",),
    )

    result = await detector.compare_with_article(article, candidate)

    assert result.match_type == SemanticMatchType.SEMANTIC_DUPLICATE
    assert "high_title_jaccard" in "".join(result.signals)
    assert "shared_companies:2" in result.signals
    assert "shared_topics:2" in result.signals
    assert "within_24h" in result.signals
    assert "same_domain" in result.signals


@pytest.mark.asyncio
async def test_compare_with_article_medium_jaccard(
    detector: SemanticDuplicateDetector,
) -> None:
    article = _make_article(title="OpenAI launches enterprise model")
    candidate = _make_article(title="OpenAI launches enterprise platform")

    result = await detector.compare_with_article(article, candidate)

    assert any(s.startswith("medium_title_jaccard") for s in result.signals)


@pytest.mark.asyncio
async def test_compare_with_article_low_jaccard(
    detector: SemanticDuplicateDetector,
) -> None:
    article = _make_article(title="OpenAI launches new model today")
    candidate = _make_article(title="OpenAI launches product update")

    result = await detector.compare_with_article(article, candidate)

    assert any(s.startswith("low_title_jaccard") for s in result.signals)


@pytest.mark.asyncio
async def test_compare_with_article_no_overlap(
    detector: SemanticDuplicateDetector,
) -> None:
    article = _make_article(title="Apple releases new iPhone")
    candidate = _make_article(title="NVIDIA reports quarterly earnings")

    result = await detector.compare_with_article(article, candidate)

    assert result.match_type == SemanticMatchType.NEW_STORY
    assert not any("jaccard" in s for s in result.signals)


@pytest.mark.asyncio
async def test_compare_with_article_shared_company_single(
    detector: SemanticDuplicateDetector,
) -> None:
    article = _make_article(
        title="OpenAI unveils enterprise model",
        companies=("OpenAI",),
    )
    candidate = _make_article(
        title="OpenAI announces platform",
        companies=("OpenAI",),
    )

    result = await detector.compare_with_article(article, candidate)

    assert "shared_company:1" in result.signals


@pytest.mark.asyncio
async def test_compare_with_article_shared_topic_single(
    detector: SemanticDuplicateDetector,
) -> None:
    article = _make_article(
        title="OpenAI unveils model",
        topics=("ai",),
    )
    candidate = _make_article(
        title="OpenAI announces platform",
        topics=("ai",),
    )

    result = await detector.compare_with_article(article, candidate)

    assert "shared_topic:1" in result.signals


@pytest.mark.asyncio
async def test_compare_with_article_time_windows(
    detector: SemanticDuplicateDetector,
) -> None:
    now = datetime(2026, 9, 4, 12, 0, tzinfo=UTC)
    article = _make_article(title="OpenAI new model", published_at=now)

    candidate_window = _make_article(
        title="OpenAI new model",
        published_at=now - timedelta(hours=48),
    )
    result_window = await detector.compare_with_article(article, candidate_window)
    assert "within_window" in result_window.signals

    candidate_week = _make_article(
        title="OpenAI new model",
        published_at=now - timedelta(days=5),
    )
    result_week = await detector.compare_with_article(article, candidate_week)
    assert "within_7d" in result_week.signals

    candidate_outside = _make_article(
        title="OpenAI new model",
        published_at=now - timedelta(days=10),
    )
    result_outside = await detector.compare_with_article(article, candidate_outside)
    assert "outside_time_window" in result_outside.signals


@pytest.mark.asyncio
async def test_compare_with_article_shared_category_requires_no_shared_companies(
    detector: SemanticDuplicateDetector,
) -> None:
    article = _make_article(
        title="OpenAI launches model",
        companies=(),
        categories=("tech",),
    )
    candidate = _make_article(
        title="Anthropic launches model",
        companies=(),
        categories=("tech",),
    )

    result = await detector.compare_with_article(article, candidate)

    assert "shared_category:1" in result.signals
