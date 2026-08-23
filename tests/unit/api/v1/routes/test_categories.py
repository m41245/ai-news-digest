"""
Unit tests for categories API routes.
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
from ai_news_digest.api.v1.routes.categories import router
from ai_news_digest.domain.models.category import Category
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
    container.category_repository.list_all = AsyncMock(return_value=[])
    container.category_repository.get_by_id = AsyncMock(return_value=None)
    container.category_repository.create = AsyncMock()
    container.category_repository.delete = AsyncMock()
    container.category_repository.update = AsyncMock()
    container.update_category = MagicMock()
    container.update_category.execute = AsyncMock()
    return container


@pytest.fixture
def client(mock_container: MagicMock, mock_user: User) -> TestClient:
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_container] = lambda: mock_container
    app.dependency_overrides[get_current_active_user] = lambda: mock_user
    setup_exception_handlers(app)
    return TestClient(app)


def test_list_categories(client: TestClient, mock_container: MagicMock) -> None:
    """Test listing categories endpoint."""
    mock_category = Category(
        id=uuid4(),
        name="Tech",
        description="Technology news",
        created_at=datetime.now(UTC),
    )
    mock_container.category_repository.list_all.return_value = [mock_category]

    response = client.get("/categories/")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Tech"


def test_get_category_not_found(client: TestClient, mock_container: MagicMock) -> None:
    """Test get category endpoint returns 404 when not found."""
    mock_container.category_repository.get_by_id.return_value = None

    category_id = uuid4()
    response = client.get(f"/categories/{category_id}")

    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


def test_create_category(client: TestClient, mock_container: MagicMock) -> None:
    """Test create category endpoint."""
    mock_category = Category(
        id=uuid4(),
        name="Tech",
        description="Technology news",
        created_at=datetime.now(UTC),
    )
    mock_container.category_repository.create.return_value = mock_category

    response = client.post("/categories/", json={"name": "Tech", "description": "Technology news"})

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Tech"


def test_delete_category_not_implemented(client: TestClient, mock_container: MagicMock) -> None:
    """Test delete category endpoint returns 404 when category does not exist."""
    mock_container.category_repository.get_by_id.return_value = None

    category_id = uuid4()
    response = client.delete(f"/categories/{category_id}")

    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


def test_replace_category(client: TestClient, mock_container: MagicMock) -> None:
    """Test replace category endpoint."""
    mock_category = Category(
        id=uuid4(),
        name="Tech",
        description="Technology news",
        created_at=datetime.now(UTC),
    )
    mock_container.update_category.execute.return_value = mock_category

    response = client.put(
        f"/categories/{mock_category.id}",
        json={"name": "Tech", "description": "Technology news"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Tech"
    assert data["description"] == "Technology news"
