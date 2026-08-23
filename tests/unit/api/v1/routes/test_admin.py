"""
Unit tests for admin API routes.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from ai_news_digest.api.middleware.exception_handler import setup_exception_handlers
from ai_news_digest.api.v1.dependencies.auth import get_current_admin_user
from ai_news_digest.api.v1.dependencies.dependencies import get_container
from ai_news_digest.api.v1.routes.admin import router
from ai_news_digest.domain.models.user import User


@pytest.fixture
def mock_container() -> MagicMock:
    container = MagicMock()
    container.article_repository.list_recent = AsyncMock(return_value=[1, 2, 3])
    container.source_repository.list_all = AsyncMock(return_value=[1, 2, 3])
    container.digest_repository.list_recent = AsyncMock(return_value=[1, 2, 3])
    return container


@pytest.fixture
def mock_admin_user() -> User:
    return User.create(
        email="admin@example.com",
        hashed_password="hashed",
        is_active=True,
        is_admin=True,
    )


@pytest.fixture
def client(mock_container: MagicMock, mock_admin_user: User) -> TestClient:
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_container] = lambda: mock_container
    app.dependency_overrides[get_current_admin_user] = lambda: mock_admin_user
    setup_exception_handlers(app)
    return TestClient(app)


def test_get_system_stats(client: TestClient) -> None:
    """Test get system stats endpoint."""
    response = client.get("/admin/stats")

    assert response.status_code == 200
    data = response.json()
    assert "articles" in data
    assert "sources" in data
    assert "digests" in data
    assert "status" in data
    assert data["status"] == "ok"


def test_trigger_ingestion(client: TestClient) -> None:
    """Test trigger ingestion endpoint."""
    mock_task = MagicMock()
    mock_task.id = "test-task-id"

    with patch(
        "ai_news_digest.workers.tasks.ingest.fetch_all_sources.delay",
        return_value=mock_task,
    ):
        response = client.post("/admin/ingestion/run")

    assert response.status_code == 202
    data = response.json()
    assert data["message"] == "Ingestion triggered."
    assert "task_id" in data


def test_trigger_digest_generation(client: TestClient) -> None:
    """Test trigger digest generation endpoint."""
    mock_task = MagicMock()
    mock_task.id = "test-task-id"

    with patch(
        "ai_news_digest.workers.tasks.digest.generate_daily_digest.delay",
        return_value=mock_task,
    ):
        response = client.post("/admin/digest/run")

    assert response.status_code == 202
    data = response.json()
    assert data["message"] == "Digest generation triggered."
    assert "task_id" in data


def test_cleanup_database(client: TestClient) -> None:
    """Test cleanup database endpoint."""
    mock_task = MagicMock()
    mock_task.id = "test-task-id"

    with patch(
        "ai_news_digest.workers.tasks.cleanup.cleanup_old_articles.delay",
        return_value=mock_task,
    ):
        response = client.post("/admin/cleanup")

    assert response.status_code == 202
    data = response.json()
    assert data["message"] == "Cleanup triggered."
    assert "task_id" in data


def test_admin_health(client: TestClient) -> None:
    """Test admin health endpoint."""
    response = client.get("/admin/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "admin"
