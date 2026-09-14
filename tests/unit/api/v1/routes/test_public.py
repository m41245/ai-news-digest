"""
Unit tests for public, unauthenticated API routes.
"""

from __future__ import annotations

import unittest.mock
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from ai_news_digest.api.middleware.exception_handler import setup_exception_handlers
from ai_news_digest.api.v1.dependencies.dependencies import get_container
from ai_news_digest.api.v1.routes.public import router
from ai_news_digest.domain.enums.article_status import ArticleStatus
from ai_news_digest.domain.enums.cluster_status import ClusterStatus
from ai_news_digest.domain.enums.digest_format import DigestFormat
from ai_news_digest.domain.enums.source_status import SourceStatus
from ai_news_digest.domain.enums.source_type import SourceType
from ai_news_digest.domain.models.article import Article
from ai_news_digest.domain.models.category import Category
from ai_news_digest.domain.models.digest import Digest
from ai_news_digest.domain.models.source import Source
from ai_news_digest.domain.models.story_cluster import StoryCluster


@pytest.fixture
def sample_source() -> Source:
    return Source(
        id=uuid4(),
        name="Test Source",
        feed_url="https://example.com/feed.xml",
        website_url="https://example.com",
        description="A source",
        is_active=True,
        source_type=SourceType.OTHER,
        status=SourceStatus.VERIFIED,
        created_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_category() -> Category:
    return Category(
        id=uuid4(),
        name="Technology",
        description="Tech news",
        created_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_article(sample_source: Source, sample_category: Category) -> Article:
    return Article(
        id=uuid4(),
        title="A test article",
        url="https://example.com/article",
        summary="An AI summary",
        content=None,
        source_id=sample_source.id,
        category_id=sample_category.id,
        published_at=datetime(2026, 8, 23, 12, 0, tzinfo=UTC),
        fetched_at=datetime.now(UTC),
        status=ArticleStatus.READY,
    )


@pytest.fixture
def mock_container(
    sample_article: Article,
    sample_source: Source,
    sample_category: Category,
) -> MagicMock:
    container = MagicMock()
    container.article_repository.list_public_articles = AsyncMock(return_value=[sample_article])
    container.article_repository.count_public_articles = AsyncMock(return_value=1)
    container.article_repository.get_public_article = AsyncMock(return_value=sample_article)
    container.source_repository.list_all = AsyncMock(return_value=[sample_source])
    container.category_repository.list_all = AsyncMock(return_value=[sample_category])
    container.digest_repository.list_recent = AsyncMock(return_value=[])
    container.digest_repository.get_by_id = AsyncMock(return_value=None)
    container.digest_repository.count = AsyncMock(return_value=0)
    return container


@pytest.fixture
def client(mock_container: MagicMock) -> TestClient:
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_container] = lambda: mock_container
    setup_exception_handlers(app)
    with TestClient(app) as test_client:
        yield test_client


def test_list_public_articles_returns_enriched_response(
    client: TestClient,
    mock_container: MagicMock,
) -> None:
    response = client.get("/public/articles")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1

    item = data["items"][0]
    assert item["title"] == "A test article"
    assert item["source_name"] == "Test Source"
    assert item["category_name"] == "Technology"
    assert "content" not in item
    assert "source_id" not in item
    assert "category_id" not in item


def test_list_public_articles_passes_filters_to_repository(
    client: TestClient,
    mock_container: MagicMock,
) -> None:
    response = client.get(
        "/public/articles",
        params={"category_id": str(uuid4()), "search": "ai", "limit": 10, "offset": 5},
    )

    assert response.status_code == 200
    mock_container.article_repository.list_public_articles.assert_awaited_once()
    _, kwargs = mock_container.article_repository.list_public_articles.await_args
    assert kwargs["limit"] == 10
    assert kwargs["offset"] == 5
    assert kwargs["search"] == "ai"


def test_get_public_article_not_found_returns_404(
    client: TestClient,
    mock_container: MagicMock,
) -> None:
    mock_container.article_repository.get_public_article = AsyncMock(return_value=None)

    response = client.get(f"/public/articles/{uuid4()}")

    assert response.status_code == 404


def test_public_endpoints_require_no_auth(client: TestClient) -> None:
    """Public endpoints must not require an Authorization header."""
    response = client.get("/public/articles")
    assert response.status_code == 200

    response = client.get("/public/categories")
    assert response.status_code == 200

    response = client.get("/public/digests")
    assert response.status_code == 200


def test_list_public_categories(
    client: TestClient,
) -> None:
    response = client.get("/public/categories")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Technology"


def test_list_public_digests_returns_paginated_envelope(
    client: TestClient,
) -> None:
    response = client.get("/public/digests")

    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


def test_public_article_includes_intelligence_fields(
    client: TestClient,
    mock_container: MagicMock,
) -> None:
    from ai_news_digest.domain.models.article import Article

    article_with_intelligence = Article(
        id=uuid4(),
        title="Intelligence article",
        url="https://example.com/intel",
        summary="Summary with intelligence",
        content=None,
        source_id=mock_container.source_repository.list_all.return_value[0].id,
        category_id=mock_container.category_repository.list_all.return_value[0].id,
        published_at=datetime(2026, 8, 23, 12, 0, tzinfo=UTC),
        fetched_at=datetime.now(UTC),
        status=ArticleStatus.READY,
        importance_score=0.85,
        confidence=0.92,
        key_takeaways=("Takeaway 1", "Takeaway 2"),
        why_it_matters="This matters because...",
        companies=("Acme Corp",),
        topics=("AI", "Technology"),
    )
    mock_container.article_repository.list_public_articles = AsyncMock(return_value=[article_with_intelligence])
    mock_container.article_repository.count_public_articles = AsyncMock(return_value=1)

    response = client.get("/public/articles")
    assert response.status_code == 200
    data = response.json()
    item = data["items"][0]
    assert item["importance_score"] == 0.85
    assert item["confidence"] == 0.92
    assert item["key_takeaways"] == ["Takeaway 1", "Takeaway 2"]
    assert item["why_it_matters"] == "This matters because..."
    assert item["companies"] == ["Acme Corp"]
    assert item["topics"] == ["AI", "Technology"]


def test_public_digest_includes_stories_and_top_story(
    client: TestClient,
    mock_container: MagicMock,
) -> None:
    from ai_news_digest.domain.models.digest import Digest

    digest = Digest(
        id=uuid4(),
        title="Test Digest",
        content="Digest content",
        generated_at=datetime.now(UTC),
        format=DigestFormat.MARKDOWN,
        article_ids=[uuid4()],
        top_story_cluster_id=uuid4(),
        stories=[
            {
                "cluster_id": str(uuid4()),
                "headline": "Story headline",
                "summary": "Story summary",
                "key_takeaways": ["Takeaway"],
                "why_it_matters": "Why it matters",
            }
        ],
        generation_method="ai",
    )
    mock_cluster = MagicMock()
    mock_cluster.id = digest.top_story_cluster_id
    mock_cluster.title = "Top Story Cluster"
    mock_cluster.slug = "top-story-cluster"
    mock_cluster.summary = "Top story summary"
    mock_cluster.importance_score = 0.9
    mock_cluster.confidence = 0.95
    mock_cluster.ranking_score = 0.88
    mock_cluster.ranking_explanation = "High ranking"

    mock_container.digest_repository.list_recent = AsyncMock(return_value=[digest])
    mock_container.digest_repository.count = AsyncMock(return_value=1)
    mock_container.digest_repository.get_by_id = AsyncMock(return_value=digest)
    mock_container.story_cluster_repository.get_by_id = AsyncMock(return_value=mock_cluster)

    response = client.get("/public/digests")
    assert response.status_code == 200
    data = response.json()
    item = data["items"][0]
    assert item["stories"] is not None
    assert len(item["stories"]) == 1
    assert item["top_story"] is not None
    assert item["top_story"]["title"] == "Top Story Cluster"


def test_public_top_story_endpoint(
    client: TestClient,
    mock_container: MagicMock,
) -> None:
    from ai_news_digest.domain.models.story_cluster import StoryCluster
    from ai_news_digest.domain.enums.cluster_status import ClusterStatus

    mock_cluster = StoryCluster(
        id=uuid4(),
        title="Top Story",
        slug="top-story",
        summary="Summary",
        importance_score=0.9,
        confidence=0.95,
        ranking_score=0.88,
        ranking_explanation="High ranking",
        status=ClusterStatus.ACTIVE,
    )

    class FakeTopStoryResult:
        top_story_cluster_id = str(mock_cluster.id)
        top_story_score = 0.88
        total_candidates = 1
        eligible_candidates = 1
        ranking_window_start = datetime(2026, 1, 1, tzinfo=UTC)
        ranking_window_end = datetime(2026, 1, 2, tzinfo=UTC)
        generated_at = datetime(2026, 1, 1, tzinfo=UTC)

    mock_container.story_cluster_repository.find_recent_active_clusters = AsyncMock(return_value=[mock_cluster])
    mock_container.story_cluster_repository.get_by_id = AsyncMock(return_value=mock_cluster)
    mock_container.article_repository.list_by_cluster_id = AsyncMock(return_value=[])
    mock_container.source_repository.list_all = AsyncMock(return_value=[])
    mock_container.category_repository.list_all = AsyncMock(return_value=[])
    mock_container.company_repository.list_all = AsyncMock(return_value=[])
    mock_container.topic_repository.list_all = AsyncMock(return_value=[])

    with unittest.mock.patch(
        "ai_news_digest.api.v1.routes.public.TopStorySelector"
    ) as MockSelector:
        mock_selector = MockSelector.return_value
        mock_selector.rank_and_select.return_value = ([], FakeTopStoryResult())

        response = client.get("/public/story-ranking/top-story")
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Top Story"
        assert data["slug"] == "top-story"
        assert data["importance_score"] == 0.9


def test_public_story_cluster_endpoint(
    client: TestClient,
    mock_container: MagicMock,
) -> None:
    from ai_news_digest.domain.models.story_cluster import StoryCluster
    from ai_news_digest.domain.enums.cluster_status import ClusterStatus

    mock_cluster = StoryCluster(
        id=uuid4(),
        title="Test Cluster",
        slug="test-cluster",
        summary="Cluster summary",
        importance_score=0.8,
        confidence=0.85,
        status=ClusterStatus.ACTIVE,
    )
    mock_container.story_cluster_repository.get_by_slug = AsyncMock(return_value=mock_cluster)
    mock_container.article_repository.list_by_cluster_id = AsyncMock(return_value=[])
    mock_container.source_repository.list_all = AsyncMock(return_value=[])

    response = client.get("/public/story-clusters/test-cluster")
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Cluster"
    assert data["slug"] == "test-cluster"
    assert data["article_count"] == 0


def test_public_sources_endpoint(
    client: TestClient,
) -> None:
    response = client.get("/public/sources")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Test Source"


def test_list_public_story_clusters_returns_paginated(
    client: TestClient,
    mock_container: MagicMock,
) -> None:
    from ai_news_digest.domain.models.story_cluster import StoryCluster
    from ai_news_digest.domain.enums.cluster_status import ClusterStatus

    mock_cluster = StoryCluster(
        id=uuid4(),
        title="Test Cluster",
        slug="test-cluster",
        summary="Cluster summary",
        importance_score=0.8,
        confidence=0.85,
        status=ClusterStatus.ACTIVE,
    )
    mock_container.story_cluster_repository.search_public = AsyncMock(return_value=[mock_cluster])
    mock_container.story_cluster_repository.count_public = AsyncMock(return_value=1)

    response = client.get("/public/story-clusters")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["title"] == "Test Cluster"


def test_list_public_story_clusters_search_filter(
    client: TestClient,
    mock_container: MagicMock,
) -> None:
    mock_container.story_cluster_repository.search_public = AsyncMock(return_value=[])
    mock_container.story_cluster_repository.count_public = AsyncMock(return_value=0)

    response = client.get("/public/story-clusters", params={"search": "AI"})
    assert response.status_code == 200
    mock_container.story_cluster_repository.search_public.assert_awaited_once()
    _, kwargs = mock_container.story_cluster_repository.search_public.await_args
    assert kwargs["search"] == "AI"


def test_list_public_companies_returns_list(
    client: TestClient,
    mock_container: MagicMock,
) -> None:
    from ai_news_digest.domain.models.company import Company

    mock_company = MagicMock()
    mock_company.id = uuid4()
    mock_company.name = "Acme Corp"
    mock_company.description = "A test company"
    mock_company.article_count = 5
    mock_container.company_repository.list_all_with_counts = AsyncMock(return_value=[mock_company])

    response = client.get("/public/companies")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Acme Corp"
    assert data[0]["article_count"] == 5


def test_list_public_topics_returns_list(
    client: TestClient,
    mock_container: MagicMock,
) -> None:
    from ai_news_digest.domain.models.topic import Topic

    mock_topic = MagicMock()
    mock_topic.id = uuid4()
    mock_topic.name = "AI"
    mock_topic.description = "Artificial Intelligence"
    mock_topic.article_count = 10
    mock_container.topic_repository.list_all_with_counts = AsyncMock(return_value=[mock_topic])

    response = client.get("/public/topics")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "AI"
    assert data[0]["article_count"] == 10


def test_article_search_includes_why_it_matters(
    client: TestClient,
    mock_container: MagicMock,
) -> None:
    from ai_news_digest.domain.models.article import Article

    article_with_intelligence = Article(
        id=uuid4(),
        title="Regular title",
        url="https://example.com/intel",
        summary="Summary",
        content=None,
        source_id=mock_container.source_repository.list_all.return_value[0].id,
        category_id=mock_container.category_repository.list_all.return_value[0].id,
        published_at=datetime(2026, 8, 23, 12, 0, tzinfo=UTC),
        fetched_at=datetime.now(UTC),
        status=ArticleStatus.READY,
        why_it_matters="This is very important for AI development",
    )
    mock_container.article_repository.list_public_articles = AsyncMock(return_value=[article_with_intelligence])
    mock_container.article_repository.count_public_articles = AsyncMock(return_value=1)

    response = client.get("/public/articles", params={"search": "important"})
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["why_it_matters"] == "This is very important for AI development"


def test_combined_filters_company_and_topic(
    client: TestClient,
    mock_container: MagicMock,
) -> None:
    mock_container.article_repository.list_public_articles = AsyncMock(return_value=[])
    mock_container.article_repository.count_public_articles = AsyncMock(return_value=0)

    response = client.get(
        "/public/articles",
        params={"company_id": str(uuid4()), "topic_id": str(uuid4())},
    )
    assert response.status_code == 200
    mock_container.article_repository.list_public_articles.assert_awaited_once()
    _, kwargs = mock_container.article_repository.list_public_articles.await_args
    assert kwargs["company_id"] is not None
    assert kwargs["topic_id"] is not None
