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
    container.article_repository.count = AsyncMock(return_value=3)
    container.source_repository.list_all = AsyncMock(return_value=[1, 2, 3])
    container.digest_repository.count = AsyncMock(return_value=2)
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
    with TestClient(app) as test_client:
        yield test_client


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


def test_worker_health(client: TestClient) -> None:
    """Test worker health endpoint when workers are online."""
    mock_ping_result = [
        {"worker1@hostname": {"ok": "pong"}},
    ]

    with patch(
        "ai_news_digest.api.v1.routes.admin.celery_app.control.ping",
        return_value=mock_ping_result,
    ):
        response = client.get("/admin/workers/health")

    assert response.status_code == 200
    data = response.json()
    assert data["workers_online"] is True
    assert data["workers_responded"] == 1
    assert data["broker_connected"] is True
    assert data["status"] == "healthy"


def test_worker_health_no_workers(client: TestClient) -> None:
    """Test worker health endpoint when no workers are available."""
    with patch(
        "ai_news_digest.api.v1.routes.admin.celery_app.control.ping",
        return_value=[],
    ):
        response = client.get("/admin/workers/health")

    assert response.status_code == 200
    data = response.json()
    assert data["workers_online"] is False
    assert data["workers_responded"] == 0
    assert data["status"] == "degraded"


def test_worker_health_broker_error(client: TestClient) -> None:
    """Test worker health endpoint when broker connection fails."""
    with patch(
        "ai_news_digest.api.v1.routes.admin.celery_app.control.ping",
        side_effect=ConnectionError("Broker unavailable"),
    ):
        response = client.get("/admin/workers/health")

    assert response.status_code == 200
    data = response.json()
    assert data["workers_online"] is False
    assert data["workers_responded"] == 0
    assert data["broker_connected"] is False
    assert data["status"] == "unhealthy"


def test_get_task_status_success(client: TestClient) -> None:
    """Test task status endpoint for a successful task."""
    mock_result = MagicMock()
    mock_result.state = "SUCCESS"
    mock_result.ready.return_value = True
    mock_result.successful.return_value = True
    mock_result.failed.return_value = False
    mock_result.result = {"status": "completed"}

    with patch(
        "ai_news_digest.api.v1.routes.admin.celery_app.AsyncResult",
        return_value=mock_result,
    ):
        response = client.get("/admin/tasks/test-task-id")

    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == "test-task-id"
    assert data["state"] == "SUCCESS"
    assert data["ready"] is True
    assert data["successful"] is True
    assert data["result"] == {"status": "completed"}


def test_get_task_status_failed(client: TestClient) -> None:
    """Test task status endpoint for a failed task — error details must be sanitized."""
    mock_result = MagicMock()
    mock_result.state = "FAILURE"
    mock_result.ready.return_value = True
    mock_result.successful.return_value = False
    mock_result.failed.return_value = True
    mock_result.result = Exception("Task failed: internal DB connection string")

    with patch(
        "ai_news_digest.api.v1.routes.admin.celery_app.AsyncResult",
        return_value=mock_result,
    ):
        response = client.get("/admin/tasks/test-task-id")

    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == "test-task-id"
    assert data["state"] == "FAILURE"
    assert data["ready"] is True
    assert data["failed"] is True
    assert "error" in data
    error = data["error"]
    assert isinstance(error, dict)
    assert "type" in error
    assert "message" in error
    assert error["type"] == "Exception"
    assert "internal DB connection string" not in str(data)


def test_get_task_status_pending(client: TestClient) -> None:
    """Test task status endpoint for a pending task."""
    mock_result = MagicMock()
    mock_result.state = "PENDING"
    mock_result.ready.return_value = False
    mock_result.successful.return_value = None
    mock_result.failed.return_value = None

    with patch(
        "ai_news_digest.api.v1.routes.admin.celery_app.AsyncResult",
        return_value=mock_result,
    ):
        response = client.get("/admin/tasks/test-task-id")

    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == "test-task-id"
    assert data["state"] == "PENDING"
    assert data["ready"] is False


def test_pipeline_status_ok(client: TestClient) -> None:
    """Test pipeline status endpoint when pipeline is healthy."""
    from datetime import UTC, datetime, timedelta

    now = datetime.now(UTC)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(
        side_effect=[
            now - timedelta(hours=1),
            now - timedelta(hours=2),
            now - timedelta(hours=3),
            now - timedelta(hours=4),
            0,
            0,
        ]
    )
    mock_session = MagicMock()
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_container = MagicMock()
    mock_container.session = mock_session
    client.app.dependency_overrides[get_container] = lambda: mock_container

    response = client.get("/admin/pipeline/status")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "ingestion" in data
    assert "processing" in data
    assert "digest" in data
    assert "delivery" in data
    assert "warnings" in data
    assert "counts" in data
    assert data["counts"]["new_articles"] == 0
    assert data["counts"]["failed_deliveries"] == 0


def test_pipeline_status_degraded(client: TestClient) -> None:
    """Test pipeline status endpoint when pipeline is degraded."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(side_effect=[None, None, None, None, 5, 2])
    mock_session = MagicMock()
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_container = MagicMock()
    mock_container.session = mock_session
    client.app.dependency_overrides[get_container] = lambda: mock_container

    response = client.get("/admin/pipeline/status")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert "warnings" in data
    assert "pending_articles" in data["warnings"]
    assert "failed_deliveries" in data["warnings"]
    assert data["counts"]["new_articles"] == 5
    assert data["counts"]["failed_deliveries"] == 2
