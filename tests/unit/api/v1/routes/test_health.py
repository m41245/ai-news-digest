"""
Unit tests for health check API routes.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncConnection

from ai_news_digest.api.middleware.exception_handler import setup_exception_handlers
from ai_news_digest.api.v1.routes.health import _readiness_cache, router


@pytest.fixture(autouse=True)
def _clear_readiness_cache() -> None:
    _readiness_cache.clear()


def test_liveness_returns_alive() -> None:
    app = FastAPI()
    app.include_router(router)
    setup_exception_handlers(app)
    with TestClient(app) as test_client:
        response = test_client.get("/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"
    assert "application" in data


def test_readiness_returns_ok_when_dependencies_healthy() -> None:
    app = FastAPI()
    app.include_router(router)
    setup_exception_handlers(app)
    mock_conn = MagicMock(spec=AsyncConnection)
    mock_conn.execute = AsyncMock()

    with (
        patch("ai_news_digest.api.v1.routes.health.engine") as mock_engine,
        patch("ai_news_digest.api.v1.routes.health.RedisStore") as mock_redis_cls,
        patch("ai_news_digest.api.v1.routes.health.settings") as mock_settings,
    ):
        mock_engine.connect.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_engine.connect.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_redis = MagicMock()
        mock_redis.ping = AsyncMock(return_value=True)
        mock_redis_cls.return_value = mock_redis
        mock_settings.redis_url = "redis://localhost:6379"
        mock_settings.app_name = "test-app"
        mock_settings.app_version = "1.0.0"
        mock_settings.environment = "test"
        mock_settings.app_startup_time = None
        with TestClient(app) as test_client:
            response = test_client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert "checks" in data


def test_readiness_returns_degraded_when_database_unavailable() -> None:
    app = FastAPI()
    app.include_router(router)
    setup_exception_handlers(app)

    with (
        patch("ai_news_digest.api.v1.routes.health.engine") as mock_engine,
        patch("ai_news_digest.api.v1.routes.health.RedisStore") as mock_redis_cls,
        patch("ai_news_digest.api.v1.routes.health.settings") as mock_settings,
    ):
        mock_engine.connect.side_effect = RuntimeError("db down")
        mock_redis = MagicMock()
        mock_redis.ping = AsyncMock(return_value=True)
        mock_redis_cls.return_value = mock_redis
        mock_settings.redis_url = "redis://localhost:6379"
        mock_settings.app_name = "test-app"
        mock_settings.app_version = "1.0.0"
        mock_settings.environment = "test"
        mock_settings.app_startup_time = None
        with TestClient(app) as test_client:
            response = test_client.get("/health/ready")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "degraded"
    assert data["checks"]["database"] == "unavailable"


def test_readiness_returns_degraded_when_cache_unavailable() -> None:
    app = FastAPI()
    app.include_router(router)
    setup_exception_handlers(app)
    mock_conn = MagicMock(spec=AsyncConnection)
    mock_conn.execute = AsyncMock()

    with (
        patch("ai_news_digest.api.v1.routes.health.engine") as mock_engine,
        patch("ai_news_digest.api.v1.routes.health.RedisStore") as mock_redis_cls,
        patch("ai_news_digest.api.v1.routes.health.settings") as mock_settings,
    ):
        mock_engine.connect.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_engine.connect.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_redis = MagicMock()
        mock_redis.ping = AsyncMock(return_value=False)
        mock_redis_cls.return_value = mock_redis
        mock_settings.redis_url = "redis://localhost:6379"
        mock_settings.app_name = "test-app"
        mock_settings.app_version = "1.0.0"
        mock_settings.environment = "test"
        mock_settings.app_startup_time = None
        with TestClient(app) as test_client:
            response = test_client.get("/health/ready")
    assert response.status_code == 503
    data = response.json()
    assert data["checks"]["cache"] == "unavailable"


def test_notification_health_check_returns_status() -> None:
    app = FastAPI()
    app.include_router(router)
    setup_exception_handlers(app)
    mock_container = MagicMock()
    mock_container.notification_delivery_repository.list_pending = AsyncMock(return_value=[])

    with patch("ai_news_digest.bootstrap.container.Container") as mock_container_cls:
        mock_container_cls.return_value = mock_container
        with TestClient(app) as test_client:
            response = test_client.get("/health/notifications")
    assert response.status_code == 200
    data = response.json()
    assert "notification_system" in data


def test_notification_health_check_reports_degraded_on_failure() -> None:
    app = FastAPI()
    app.include_router(router)
    setup_exception_handlers(app)

    with patch("ai_news_digest.bootstrap.container.Container") as mock_container_cls:
        mock_container_cls.side_effect = RuntimeError("container init failed")
        with TestClient(app) as test_client:
            response = test_client.get("/health/notifications")
    assert response.status_code == 200
    data = response.json()
    assert data["notification_system"] == "unhealthy"
    assert "error" in data


def test_readiness_caches_result() -> None:
    app = FastAPI()
    app.include_router(router)
    setup_exception_handlers(app)
    mock_conn = MagicMock(spec=AsyncConnection)
    mock_conn.execute = AsyncMock()

    with (
        patch("ai_news_digest.api.v1.routes.health.engine") as mock_engine,
        patch("ai_news_digest.api.v1.routes.health.RedisStore") as mock_redis_cls,
        patch("ai_news_digest.api.v1.routes.health.time") as mock_time,
        patch("ai_news_digest.api.v1.routes.health.settings") as mock_settings,
    ):
        mock_engine.connect.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_engine.connect.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_redis = MagicMock()
        mock_redis.ping = AsyncMock(return_value=True)
        mock_redis_cls.return_value = mock_redis
        mock_settings.redis_url = "redis://localhost:6379"
        mock_settings.app_name = "test-app"
        mock_settings.app_version = "1.0.0"
        mock_settings.environment = "test"
        mock_settings.app_startup_time = None
        mock_time.time.return_value = 1000.0
        with TestClient(app) as test_client:
            response1 = test_client.get("/health/ready")
            mock_time.time.return_value = 1001.0
            response2 = test_client.get("/health/ready")
    assert response1.status_code == 200
    assert response2.status_code == 200


__all__ = [
    "test_liveness_returns_alive",
    "test_notification_health_check_reports_degraded_on_failure",
    "test_notification_health_check_returns_status",
    "test_readiness_caches_result",
    "test_readiness_returns_degraded_when_cache_unavailable",
    "test_readiness_returns_degraded_when_database_unavailable",
    "test_readiness_returns_ok_when_dependencies_healthy",
]
