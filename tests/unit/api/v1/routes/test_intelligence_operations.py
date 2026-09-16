"""Tests for M94 intelligence operations API routes."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from ai_news_digest.api.middleware.exception_handler import setup_exception_handlers
from ai_news_digest.api.v1.dependencies.auth import get_current_admin_user
from ai_news_digest.api.v1.dependencies.dependencies import get_container
from ai_news_digest.api.v1.routes.intelligence_operations import router
from ai_news_digest.domain.models.user import User


def _make_admin_user() -> User:
    return User.create(
        email="admin@example.com",
        hashed_password="hashed",  # noqa: S106
        is_active=True,
        is_admin=True,
    )


def _make_container() -> MagicMock:
    container = MagicMock()
    container.session = AsyncMock()
    return container


@pytest.fixture
def client() -> TestClient:
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_container] = _make_container
    app.dependency_overrides[get_current_admin_user] = _make_admin_user
    setup_exception_handlers(app)
    with TestClient(app) as test_client:
        yield test_client


class TestIntelligenceOperationsRoutes:
    def test_get_intelligence_health(self, client: TestClient) -> None:
        with patch(
            "ai_news_digest.infrastructure.database.repositories.intelligence_operations_repository.ComponentHealthRepository"
        ) as mock_repo:
            mock_repo.return_value.list_snapshots = AsyncMock(return_value=([], 0))
            response = client.get("/api/v1/intelligence/health")
        assert response.status_code == 200
        data = response.json()
        assert "overall_status" in data
        assert "components" in data

    def test_list_quality_gate_results(self, client: TestClient) -> None:
        with patch(
            "ai_news_digest.infrastructure.database.repositories.intelligence_operations_repository.QualityGateRepository"
        ) as mock_repo:
            mock_repo.return_value.list_results = AsyncMock(return_value=([], 0))
            response = client.get("/api/v1/intelligence/gates")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    def test_list_quality_gate_definitions(self, client: TestClient) -> None:
        response = client.get("/api/v1/intelligence/gates/definitions")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_operational_alerts(self, client: TestClient) -> None:
        with patch(
            "ai_news_digest.infrastructure.database.repositories.intelligence_operations_repository.OperationalAlertRepository"
        ) as mock_repo:
            mock_repo.return_value.list_alerts = AsyncMock(return_value=([], 0))
            response = client.get("/api/v1/intelligence/alerts")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    def test_trigger_quality_gate_evaluation(self, client: TestClient) -> None:
        mock_task = MagicMock()
        mock_task.id = "test-task-id"
        with patch(
            "ai_news_digest.workers.tasks.quality_gates.evaluate_quality_gates.delay",
            return_value=mock_task,
        ):
            response = client.post("/api/v1/intelligence/gates/evaluate")
        assert response.status_code == 202
        data = response.json()
        assert data["message"] == "Quality gate evaluation triggered."
        assert "task_id" in data

    def test_trigger_quality_gate_evaluation_disabled(self, client: TestClient) -> None:
        with patch(
            "ai_news_digest.api.v1.routes.intelligence_operations.get_settings"
        ) as mock_settings:
            mock_settings.return_value.quality_gates_enabled = False
            response = client.post("/api/v1/intelligence/gates/evaluate")
        assert response.status_code == 400


def test_unauthenticated_access_returns_401() -> None:
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    setup_exception_handlers(app)

    with TestClient(app) as test_client:
        response = test_client.get("/api/v1/intelligence/health")

    assert response.status_code == 401


def test_non_admin_access_returns_403() -> None:
    from fastapi import FastAPI

    from ai_news_digest.api.v1.dependencies.auth import get_current_active_user

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_container] = _make_container
    app.dependency_overrides[get_current_active_user] = lambda: User.create(
        email="user@example.com",
        hashed_password="hashed",  # noqa: S106
        is_active=True,
        is_admin=False,
    )
    setup_exception_handlers(app)

    with TestClient(app) as test_client:
        response = test_client.get("/api/v1/intelligence/health")

    assert response.status_code == 403


__all__ = ["TestIntelligenceOperationsRoutes"]
