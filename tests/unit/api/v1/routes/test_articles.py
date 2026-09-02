"""
Unit tests for articles API routes.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from ai_news_digest.api.middleware.exception_handler import setup_exception_handlers
from ai_news_digest.api.v1.dependencies.auth import get_current_active_user
from ai_news_digest.api.v1.dependencies.dependencies import get_container
from ai_news_digest.api.v1.routes.articles import router
from ai_news_digest.domain.enums.article_status import ArticleStatus
from ai_news_digest.domain.models.article import Article
from ai_news_digest.domain.models.user import User


@pytest.fixture
def mock_user() -> User:
    return User(
        id=uuid4(),
        email="test@example.com",
        hashed_password="hashed",
        is_active=True,
        is_admin=False,
        created_at=datetime.now(UTC),
    )


@pytest.fixture
def mock_container() -> MagicMock:
    container = MagicMock()
    container.article_repository.list_recent = AsyncMock(return_value=[])
    container.article_repository.get_by_id = AsyncMock(return_value=None)
    container.article_repository.count = AsyncMock(return_value=0)
    container.create_article = AsyncMock()
    container.delete_article = AsyncMock()
    return container


@pytest.fixture
def client(mock_container: MagicMock, mock_user: User) -> TestClient:
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_container] = lambda: mock_container
    app.dependency_overrides[get_current_active_user] = lambda: mock_user
    setup_exception_handlers(app)
    with TestClient(app) as test_client:
        yield test_client


def test_list_articles_default_params(client: TestClient, mock_container: MagicMock) -> None:
    """Test listing articles with default parameters."""
    mock_article = Article(
        id=uuid4(),
        title="Test Article",
        url="https://example.com/test",
        summary="Test summary",
        content="Test content",
        source_id=uuid4(),
        category_id=None,
        published_at=datetime.now(UTC),
        fetched_at=datetime.now(UTC),
        status=ArticleStatus.NEW,
    )
    mock_container.article_repository.list_recent.return_value = [mock_article]
    mock_container.article_repository.count.return_value = 1

    response = client.get("/articles/")

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["total"] == 1
    assert data["limit"] == 20
    assert data["offset"] == 0
    assert data["items"][0]["title"] == "Test Article"


def test_list_articles_custom_params(client: TestClient, mock_container: MagicMock) -> None:
    """Test listing articles with custom parameters."""
    response = client.get("/articles/?limit=10&offset=5")

    assert response.status_code == 200
    mock_container.article_repository.list_recent.assert_called_once_with(limit=10, offset=5)
    mock_container.article_repository.count.assert_called_once()


def test_list_articles_limit_validation(client: TestClient) -> None:
    """Test that limit validation works (limit must be between 1 and 100)."""
    response = client.get("/articles/?limit=0")

    assert response.status_code == 422


def test_list_articles_limit_max_validation(client: TestClient) -> None:
    """Test that limit max validation works."""
    response = client.get("/articles/?limit=101")

    assert response.status_code == 422


def test_list_articles_offset_validation(client: TestClient) -> None:
    """Test that offset validation works (offset must be >= 0)."""
    response = client.get("/articles/?offset=-1")

    assert response.status_code == 422


def test_get_article_not_found(client: TestClient, mock_container: MagicMock) -> None:
    """Test get article endpoint returns 404 when not found."""
    mock_container.article_repository.get_by_id.return_value = None

    article_id = uuid4()
    response = client.get(f"/articles/{article_id}")

    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["message"].lower()


def test_create_article(client: TestClient, mock_container: MagicMock) -> None:
    """Test create article endpoint returns 201 with valid data."""
    from ai_news_digest.application.dto.article import ArticleResponse

    mock_response = ArticleResponse(
        id=str(uuid4()),
        title="New Article",
        url="https://example.com/new",
        summary="New summary",
        content="New content",
        source_id=str(uuid4()),
        category_id=None,
        published_at="2024-01-01T00:00:00+00:00",
        fetched_at="2024-01-01T00:00:01+00:00",
        status="new",
    )
    mock_container.create_article.execute.return_value = mock_response

    article_data = {
        "title": "New Article",
        "url": "https://example.com/new",
        "summary": "New summary",
        "content": "New content",
        "source_id": str(uuid4()),
        "published_at": "2024-01-01T00:00:00+00:00",
        "category_id": None,
    }

    response = client.post("/articles/", json=article_data)

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "New Article"
    assert data["url"] == "https://example.com/new"


def test_create_article_validation_error(client: TestClient) -> None:
    """Test create article endpoint returns 422 for invalid data."""
    article_data = {
        "title": "",
        "url": "https://example.com/new",
        "summary": "New summary",
        "source_id": str(uuid4()),
        "published_at": "2024-01-01T00:00:00+00:00",
    }

    response = client.post("/articles/", json=article_data)

    assert response.status_code == 422


def test_delete_article(client: TestClient, mock_container: MagicMock) -> None:
    """Test delete article endpoint returns 204 on success."""
    mock_container.delete_article.execute.return_value = None

    article_id = uuid4()
    response = client.delete(f"/articles/{article_id}")

    assert response.status_code == 204
    mock_container.delete_article.execute.assert_called_once_with(article_id)


def test_delete_article_not_found(client: TestClient, mock_container: MagicMock) -> None:
    """Test delete article endpoint returns 404 when article does not exist."""
    from ai_news_digest.application.exceptions.article import ArticleNotFoundError

    article_id = uuid4()
    mock_container.delete_article.execute.side_effect = ArticleNotFoundError(str(article_id))

    response = client.delete(f"/articles/{article_id}")

    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["message"].lower()
