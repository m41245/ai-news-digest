"""
Unit tests for digests API routes.
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
from ai_news_digest.api.v1.routes.digests import router
from ai_news_digest.domain.enums.digest_format import DigestFormat
from ai_news_digest.domain.models.digest import Digest
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
    container.digest_repository.list_recent = AsyncMock(return_value=[])
    container.digest_repository.get_by_id = AsyncMock(return_value=None)
    container.digest_repository.count = AsyncMock(return_value=1)
    container.generate_digest = MagicMock()
    container.generate_digest.execute = AsyncMock()
    container.update_digest = MagicMock()
    container.update_digest.execute = AsyncMock()
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


def test_list_digests(client: TestClient, mock_container: MagicMock) -> None:
    """Test listing digests endpoint."""
    mock_digest = Digest(
        id=uuid4(),
        title="Daily Digest",
        content="Digest content",
        generated_at=datetime.now(UTC),
        format=DigestFormat.MARKDOWN,
    )
    mock_container.digest_repository.list_recent.return_value = [mock_digest]

    response = client.get("/digests/")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["title"] == "Daily Digest"


def test_get_digest_not_found(client: TestClient, mock_container: MagicMock) -> None:
    """Test get digest endpoint returns 404 when not found."""
    mock_container.digest_repository.get_by_id.return_value = None

    digest_id = uuid4()
    response = client.get(f"/digests/{digest_id}")

    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


def test_generate_digest(client: TestClient, mock_container: MagicMock) -> None:
    """Test generate digest endpoint."""
    mock_digest = Digest(
        id=uuid4(),
        title="Generated Digest",
        content="Generated content",
        generated_at=datetime.now(UTC),
        format=DigestFormat.MARKDOWN,
    )
    mock_container.digest_repository.get_by_id.return_value = mock_digest
    mock_container.generate_digest.execute.return_value = MagicMock(digest_id=mock_digest.id)

    response = client.post(
        "/digests/generate", json={"title": "Generated Digest", "content": "Generated content"}
    )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Generated Digest"


def test_replace_digest(client: TestClient, mock_container: MagicMock) -> None:
    """Test replace digest endpoint."""
    mock_digest = Digest(
        id=uuid4(),
        title="Replaced Digest",
        content="Replaced content",
        generated_at=datetime.now(UTC),
        format=DigestFormat.MARKDOWN,
        article_ids=[],
    )
    mock_container.update_digest.execute.return_value = mock_digest

    response = client.put(
        f"/digests/{mock_digest.id}",
        json={"title": "Replaced Digest", "content": "Replaced content"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Replaced Digest"
    assert data["content"] == "Replaced content"
