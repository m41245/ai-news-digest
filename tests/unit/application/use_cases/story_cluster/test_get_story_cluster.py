"""
Tests for GetStoryClusterUseCase enhanced with timeline, source roles,
and what-changed detection.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from ai_news_digest.application.exceptions.story_cluster import (
    StoryClusterNotFoundError,
)
from ai_news_digest.application.use_cases.story_cluster.get_story_cluster import (
    GetStoryClusterUseCase,
)
from ai_news_digest.domain.enums.article_status import ArticleStatus
from ai_news_digest.domain.enums.source_type import SourceType
from ai_news_digest.domain.models.article import Article
from ai_news_digest.domain.models.source import Source
from ai_news_digest.domain.models.story_cluster import StoryCluster


def _make_article(
    title: str = "Test Article",
    url: str = "https://example.com/article",
    published_at: datetime | None = None,
    source_id=None,
    cluster_id=None,
    importance_score: float | None = None,
    confidence: float | None = None,
    key_takeaways: tuple[str, ...] = (),
    companies: tuple[str, ...] = (),
    topics: tuple[str, ...] = (),
    summary: str = "Test summary",
):
    if source_id is None:
        source_id = uuid4()
    if published_at is None:
        published_at = datetime(2026, 9, 4, 12, 0, tzinfo=UTC)

    article = Article.create(
        title=title,
        url=url,
        summary=summary,
        content=None,
        source_id=source_id,
        published_at=published_at,
    )
    article.status = ArticleStatus.READY
    article.companies = companies
    article.topics = topics
    article.key_takeaways = key_takeaways
    article.importance_score = importance_score
    article.confidence = confidence
    if cluster_id is not None:
        object.__setattr__(article, "cluster_id", cluster_id)
    return article


def _make_source(
    source_id=None,
    name: str = "Test Source",
    source_type: str = "other",
):
    if source_id is None:
        source_id = uuid4()
    return Source(
        id=source_id,
        name=name,
        feed_url="https://example.com/feed.xml",
        website_url="https://example.com",
        description="A test source",
        is_active=True,
        created_at=datetime(2026, 9, 1, 8, 0, tzinfo=UTC),
        source_type=SourceType(source_type),
    )


def _make_cluster(
    title: str = "Cluster",
    slug: str = "cluster",
    first_published_at: datetime | None = None,
    representative_article_id=None,
    latest_article_id=None,
    importance_score: float | None = None,
    confidence: float | None = None,
):
    if first_published_at is None:
        first_published_at = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)
    cluster = StoryCluster.create(
        title=title,
        slug=slug,
        first_published_at=first_published_at,
        representative_article_id=representative_article_id,
        latest_article_id=latest_article_id,
        importance_score=importance_score,
        confidence=confidence,
    )
    return cluster


@pytest.fixture
def mock_cluster_repository() -> MagicMock:
    repo = MagicMock()
    repo.get_by_slug = AsyncMock()
    repo.list_all = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_article_repository() -> MagicMock:
    repo = MagicMock()
    repo.list_by_cluster_id = AsyncMock(return_value=[])
    repo.get_by_id = AsyncMock(return_value=None)
    return repo


@pytest.fixture
def mock_source_repository() -> MagicMock:
    repo = MagicMock()
    repo.list_all = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def use_case(
    mock_cluster_repository: MagicMock,
    mock_article_repository: MagicMock,
    mock_source_repository: MagicMock,
) -> GetStoryClusterUseCase:
    return GetStoryClusterUseCase(
        cluster_repository=mock_cluster_repository,
        article_repository=mock_article_repository,
        source_repository=mock_source_repository,
    )


@pytest.mark.asyncio
async def test_get_story_cluster_returns_not_found(
    use_case: GetStoryClusterUseCase,
    mock_cluster_repository: MagicMock,
) -> None:
    mock_cluster_repository.get_by_slug.return_value = None

    with pytest.raises(StoryClusterNotFoundError):
        await use_case.execute("missing-slug")


@pytest.mark.asyncio
async def test_get_story_cluster_returns_detail(
    use_case: GetStoryClusterUseCase,
    mock_cluster_repository: MagicMock,
    mock_article_repository: MagicMock,
    mock_source_repository: MagicMock,
) -> None:
    source_id = uuid4()
    cluster = _make_cluster(
        title="AI Story",
        slug="ai-story",
        first_published_at=datetime(2026, 9, 1, 12, 0, tzinfo=UTC),
    )
    article = _make_article(
        title="AI Article",
        source_id=source_id,
        cluster_id=cluster.id,
        published_at=datetime(2026, 9, 1, 12, 0, tzinfo=UTC),
    )
    source = _make_source(source_id=source_id, name="Test Source", source_type="tech_publication")

    mock_cluster_repository.get_by_slug.return_value = cluster
    mock_article_repository.list_by_cluster_id.return_value = [article]
    mock_source_repository.list_all.return_value = [source]

    result = await use_case.execute("ai-story")

    assert result.title == "AI Story"
    assert result.slug == "ai-story"
    assert result.article_count == 1
    assert result.source_count == 1
    assert result.latest_article_id == str(article.id)
    assert len(result.recent_articles) == 1
    assert result.recent_articles[0].source_role == "Independent reporting"


@pytest.mark.asyncio
async def test_timeline_ordering_oldest_first(
    use_case: GetStoryClusterUseCase,
    mock_cluster_repository: MagicMock,
    mock_article_repository: MagicMock,
    mock_source_repository: MagicMock,
) -> None:
    source1 = uuid4()
    source2 = uuid4()
    source3 = uuid4()
    cluster = _make_cluster(
        title="Timeline Story",
        slug="timeline-story",
        first_published_at=datetime(2026, 9, 1, 8, 0, tzinfo=UTC),
    )
    article_latest = _make_article(
        title="Latest",
        source_id=source3,
        cluster_id=cluster.id,
        published_at=datetime(2026, 9, 4, 12, 0, tzinfo=UTC),
    )
    article_earliest = _make_article(
        title="Earliest",
        source_id=source1,
        cluster_id=cluster.id,
        published_at=datetime(2026, 9, 1, 8, 0, tzinfo=UTC),
    )
    article_middle = _make_article(
        title="Middle",
        source_id=source2,
        cluster_id=cluster.id,
        published_at=datetime(2026, 9, 2, 10, 0, tzinfo=UTC),
    )

    mock_cluster_repository.get_by_slug.return_value = cluster
    mock_article_repository.list_by_cluster_id.return_value = [
        article_latest,
        article_earliest,
        article_middle,
    ]
    mock_source_repository.list_all.return_value = [
        _make_source(source_id=source1, name="Source 1"),
        _make_source(source_id=source2, name="Source 2"),
        _make_source(source_id=source3, name="Source 3"),
    ]

    result = await use_case.execute("timeline-story")

    assert result.timeline[0]["title"] == "Earliest"
    assert result.timeline[1]["title"] == "Middle"
    assert result.timeline[2]["title"] == "Latest"


@pytest.mark.asyncio
async def test_source_role_fallback_to_related_coverage(
    use_case: GetStoryClusterUseCase,
    mock_cluster_repository: MagicMock,
    mock_article_repository: MagicMock,
    mock_source_repository: MagicMock,
) -> None:
    source_id = uuid4()
    cluster = _make_cluster(
        title="Story",
        slug="story",
        first_published_at=datetime(2026, 9, 1, 8, 0, tzinfo=UTC),
    )
    article = _make_article(
        title="Article",
        source_id=source_id,
        cluster_id=cluster.id,
        published_at=datetime(2026, 9, 15, 10, 0, tzinfo=UTC),
    )
    source = _make_source(source_id=source_id, name="Test Source", source_type="other")

    mock_cluster_repository.get_by_slug.return_value = cluster
    mock_article_repository.list_by_cluster_id.return_value = [article]
    mock_source_repository.list_all.return_value = [source]

    result = await use_case.execute("story")

    assert result.recent_articles[0].source_role == "Related coverage"


@pytest.mark.asyncio
async def test_what_changed_detects_changes(
    use_case: GetStoryClusterUseCase,
    mock_cluster_repository: MagicMock,
    mock_article_repository: MagicMock,
    mock_source_repository: MagicMock,
) -> None:
    source1 = uuid4()
    source2 = uuid4()
    cluster = _make_cluster(
        title="Evolving Story",
        slug="evolving-story",
        first_published_at=datetime(2026, 9, 1, 8, 0, tzinfo=UTC),
    )
    article_old = _make_article(
        title="Original headline",
        source_id=source1,
        cluster_id=cluster.id,
        published_at=datetime(2026, 9, 1, 8, 0, tzinfo=UTC),
        companies=("OpenAI",),
        topics=("AI",),
        key_takeaways=("Takeaway 1",),
        importance_score=0.5,
    )
    article_new = _make_article(
        title="Updated headline",
        source_id=source2,
        cluster_id=cluster.id,
        published_at=datetime(2026, 9, 4, 12, 0, tzinfo=UTC),
        companies=("OpenAI", "Anthropic"),
        topics=("AI",),
        key_takeaways=("Takeaway 2",),
        importance_score=0.9,
    )

    mock_cluster_repository.get_by_slug.return_value = cluster
    mock_article_repository.list_by_cluster_id.return_value = [article_new, article_old]
    mock_source_repository.list_all.return_value = [
        _make_source(source_id=source1, name="Source 1"),
        _make_source(source_id=source2, name="Source 2"),
    ]

    result = await use_case.execute("evolving-story")

    assert len(result.what_changed) > 0


@pytest.mark.asyncio
async def test_what_changed_empty_when_insufficient_evidence(
    use_case: GetStoryClusterUseCase,
    mock_cluster_repository: MagicMock,
    mock_article_repository: MagicMock,
    mock_source_repository: MagicMock,
) -> None:
    source_id = uuid4()
    cluster = _make_cluster(
        title="Static Story",
        slug="static-story",
        first_published_at=datetime(2026, 9, 1, 8, 0, tzinfo=UTC),
    )
    article1 = _make_article(
        title="Same headline",
        source_id=source_id,
        cluster_id=cluster.id,
        published_at=datetime(2026, 9, 1, 8, 0, tzinfo=UTC),
    )
    article2 = _make_article(
        title="Same headline",
        source_id=source_id,
        cluster_id=cluster.id,
        published_at=datetime(2026, 9, 4, 12, 0, tzinfo=UTC),
    )

    mock_cluster_repository.get_by_slug.return_value = cluster
    mock_article_repository.list_by_cluster_id.return_value = [article1, article2]
    mock_source_repository.list_all.return_value = [
        _make_source(source_id=source_id, name="Source 1"),
    ]

    result = await use_case.execute("static-story")

    assert result.what_changed == []


@pytest.mark.asyncio
async def test_new_article_added_to_cluster(
    use_case: GetStoryClusterUseCase,
    mock_cluster_repository: MagicMock,
    mock_article_repository: MagicMock,
    mock_source_repository: MagicMock,
) -> None:
    source_id = uuid4()
    cluster = _make_cluster(
        title="Cluster",
        slug="cluster",
        first_published_at=datetime(2026, 9, 1, 8, 0, tzinfo=UTC),
        representative_article_id=uuid4(),
    )
    old_article = _make_article(
        title="Old Article",
        source_id=source_id,
        cluster_id=cluster.id,
        published_at=datetime(2026, 9, 1, 8, 0, tzinfo=UTC),
    )
    new_article = _make_article(
        title="New Article",
        source_id=source_id,
        cluster_id=cluster.id,
        published_at=datetime(2026, 9, 4, 12, 0, tzinfo=UTC),
    )

    mock_cluster_repository.get_by_slug.return_value = cluster
    mock_article_repository.list_by_cluster_id.return_value = [new_article, old_article]
    mock_source_repository.list_all.return_value = [
        _make_source(source_id=source_id, name="Test Source"),
    ]

    result = await use_case.execute("cluster")

    assert result.article_count == 2
    assert result.timeline[0]["title"] == "Old Article"
    assert result.timeline[1]["title"] == "New Article"


@pytest.mark.asyncio
async def test_duplicate_articles_do_not_duplicate_in_timeline(
    use_case: GetStoryClusterUseCase,
    mock_cluster_repository: MagicMock,
    mock_article_repository: MagicMock,
    mock_source_repository: MagicMock,
) -> None:
    source_id = uuid4()
    cluster = _make_cluster(
        title="Cluster",
        slug="cluster",
        first_published_at=datetime(2026, 9, 1, 8, 0, tzinfo=UTC),
    )
    article = _make_article(
        title="Article",
        source_id=source_id,
        cluster_id=cluster.id,
        published_at=datetime(2026, 9, 1, 8, 0, tzinfo=UTC),
    )

    mock_cluster_repository.get_by_slug.return_value = cluster
    mock_article_repository.list_by_cluster_id.return_value = [article, article]
    mock_source_repository.list_all.return_value = [
        _make_source(source_id=source_id, name="Test Source"),
    ]

    result = await use_case.execute("cluster")

    assert result.article_count == 2
    assert len(result.timeline) == 2


@pytest.mark.asyncio
async def test_missing_dates_handled_gracefully(
    use_case: GetStoryClusterUseCase,
    mock_cluster_repository: MagicMock,
    mock_article_repository: MagicMock,
    mock_source_repository: MagicMock,
) -> None:
    source_id = uuid4()
    cluster = _make_cluster(
        title="Cluster",
        slug="cluster",
        first_published_at=datetime(2026, 9, 1, 8, 0, tzinfo=UTC),
    )
    article_no_date = Article(
        id=uuid4(),
        title="No Date Article",
        url="https://example.com/no-date",
        summary="Summary",
        content=None,
        source_id=source_id,
        category_id=None,
        published_at=datetime(2026, 9, 1, 8, 0, tzinfo=UTC),
        fetched_at=datetime.now(UTC),
        status=ArticleStatus.READY,
    )
    object.__setattr__(article_no_date, "cluster_id", cluster.id)

    mock_cluster_repository.get_by_slug.return_value = cluster
    mock_article_repository.list_by_cluster_id.return_value = [article_no_date]
    mock_source_repository.list_all.return_value = [
        _make_source(source_id=source_id, name="Test Source"),
    ]

    result = await use_case.execute("cluster")

    assert result.article_count == 1
    assert result.timeline[0]["title"] == "No Date Article"


@pytest.mark.asyncio
async def test_api_response_contract_includes_all_fields(
    use_case: GetStoryClusterUseCase,
    mock_cluster_repository: MagicMock,
    mock_article_repository: MagicMock,
    mock_source_repository: MagicMock,
) -> None:
    source_id = uuid4()
    cluster = _make_cluster(
        title="Full Contract",
        slug="full-contract",
        first_published_at=datetime(2026, 9, 1, 8, 0, tzinfo=UTC),
    )
    article = _make_article(
        title="Article",
        source_id=source_id,
        cluster_id=cluster.id,
        published_at=datetime(2026, 9, 1, 8, 0, tzinfo=UTC),
    )

    mock_cluster_repository.get_by_slug.return_value = cluster
    mock_article_repository.list_by_cluster_id.return_value = [article]
    mock_source_repository.list_all.return_value = [
        _make_source(source_id=source_id, name="Test Source"),
    ]

    result = await use_case.execute("full-contract")

    assert hasattr(result, "id")
    assert hasattr(result, "title")
    assert hasattr(result, "slug")
    assert hasattr(result, "summary")
    assert hasattr(result, "first_published_at")
    assert hasattr(result, "last_updated_at")
    assert hasattr(result, "representative_article_id")
    assert hasattr(result, "latest_article_id")
    assert hasattr(result, "importance_score")
    assert hasattr(result, "confidence")
    assert hasattr(result, "status")
    assert hasattr(result, "article_count")
    assert hasattr(result, "source_count")
    assert hasattr(result, "recent_articles")
    assert hasattr(result, "timeline")
    assert hasattr(result, "what_changed")

    article_response = result.recent_articles[0]
    assert hasattr(article_response, "id")
    assert hasattr(article_response, "title")
    assert hasattr(article_response, "url")
    assert hasattr(article_response, "summary")
    assert hasattr(article_response, "published_at")
    assert hasattr(article_response, "importance_score")
    assert hasattr(article_response, "confidence")
    assert hasattr(article_response, "source_name")
    assert hasattr(article_response, "source_type")
    assert hasattr(article_response, "source_role")
