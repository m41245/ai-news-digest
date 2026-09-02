"""
Unit tests for sources API routes.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from ai_news_digest.api.middleware.exception_handler import setup_exception_handlers
from ai_news_digest.api.v1.dependencies.auth import get_current_active_user
from ai_news_digest.api.v1.dependencies.dependencies import get_container
from ai_news_digest.api.v1.routes.sources import router
from ai_news_digest.api.v1.schemas.source import SourceCreate
from ai_news_digest.domain.models.source import Source
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
    container.source_repository.list_all = AsyncMock(return_value=[])
    container.source_repository.count = AsyncMock(return_value=0)
    container.source_repository.get_by_id = AsyncMock(return_value=None)
    container.source_repository.create = AsyncMock()
    container.source_repository.delete = AsyncMock()
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


def test_list_sources(client: TestClient, mock_container: MagicMock) -> None:
    """Test listing sources endpoint."""
    mock_source = Source(
        id=uuid4(),
        name="Test Source",
        feed_url="https://example.com/feed.xml",
        website_url=None,
        description=None,
        is_active=True,
        created_at=datetime.now(UTC),
    )
    mock_container.source_repository.list_all.return_value = [mock_source]
    mock_container.source_repository.count.return_value = 1

    response = client.get("/sources/")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["name"] == "Test Source"


def test_create_source_not_implemented(client: TestClient, mock_container: MagicMock) -> None:
    """Test create source endpoint returns 201 with valid data."""
    mock_source = Source(
        id=uuid4(),
        name="Test Source",
        feed_url="https://example.com/feed.xml",
        website_url=None,
        description=None,
        is_active=True,
        created_at=datetime.now(UTC),
    )
    mock_container.source_repository.create.return_value = mock_source

    source_data = {
        "name": "Test Source",
        "feed_url": "https://example.com/feed.xml",
        "website_url": None,
        "description": None,
    }

    response = client.post("/sources/", json=source_data)

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Source"


def test_delete_source_not_implemented(client: TestClient, mock_container: MagicMock) -> None:
    """Test delete source endpoint returns 404 when source does not exist."""
    mock_container.source_repository.get_by_id.return_value = None

    source_id = uuid4()
    response = client.delete(f"/sources/{source_id}")

    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["message"].lower()


def test_source_create_validation_name_too_short() -> None:
    """Test SourceCreate validation for name too short."""
    with pytest.raises(ValidationError):
        SourceCreate(name="", feed_url="https://example.com", description="test")


def test_source_create_validation_name_too_long() -> None:
    """Test SourceCreate validation for name too long."""
    with pytest.raises(ValidationError):
        SourceCreate(name="a" * 201, feed_url="https://example.com", description="test")


def test_source_create_validation_url_too_long() -> None:
    """Test SourceCreate validation for URL too long."""
    with pytest.raises(ValidationError):
        SourceCreate(name="Test", feed_url="a" * 2049, description="test")


def test_source_create_validation_description_too_long() -> None:
    """Test SourceCreate validation for description too long."""
    with pytest.raises(ValidationError):
        SourceCreate(name="Test", feed_url="https://example.com", description="a" * 501)


def test_source_create_valid() -> None:
    """Test SourceCreate with valid data."""
    source = SourceCreate(
        name="Test Source",
        feed_url="https://example.com/feed.xml",
        description="tech",
    )

    assert source.name == "Test Source"
    assert source.feed_url == "https://example.com/feed.xml"
    assert source.description == "tech"
