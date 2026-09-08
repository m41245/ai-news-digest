"""
Unit tests for public, unauthenticated API routes.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from ai_news_digest.api.middleware.exception_handler import setup_exception_handlers
from ai_news_digest.api.v1.dependencies.dependencies import get_container
from ai_news_digest.api.v1.routes.public import router
from ai_news_digest.domain.enums.article_status import ArticleStatus
from ai_news_digest.domain.enums.source_type import SourceType
from ai_news_digest.domain.models.article import Article
from ai_news_digest.domain.models.category import Category
from ai_news_digest.domain.models.source import Source


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
