"""
Unit tests for health check API routes.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncConnection

from ai_news_digest.api.middleware.exception_handler import setup_exception_handlers
from ai_news_digest.api.v1.routes.health import _readiness_cache, router
from ai_news_digest.application.ai.quota import (
    GlobalBudgetState,
    ProviderQuotaConfig,
    QuotaLimit,
    QuotaWindow,
)


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


def test_ai_health_returns_ok_when_providers_available() -> None:
    app = FastAPI()
    app.include_router(router)
    setup_exception_handlers(app)
    mock_provider = MagicMock()
    mock_provider.id = "openai"
    mock_provider.name = "OpenAI"
    mock_provider.model_name = "gpt-4o-mini"
    mock_provider.available = AsyncMock(return_value=True)

    mock_container = MagicMock()
    mock_container.provider_registry.list_all.return_value = [mock_provider]

    with (
        patch("ai_news_digest.bootstrap.container.Container") as mock_container_cls,
        patch("ai_news_digest.infrastructure.database.session.SessionLocal") as mock_session_cls,
        patch("ai_news_digest.api.v1.routes.health.settings") as mock_settings,
        patch("ai_news_digest.api.v1.routes.health.get_settings") as mock_get_settings,
    ):
        mock_container_cls.return_value = mock_container
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session_cls.return_value = mock_session
        mock_settings.ai_enabled = True
        mock_get_settings.return_value = mock_settings
        with TestClient(app) as test_client:
            response = test_client.get("/health/ai")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["ai_enabled"] is True
    assert "providers" in data


def test_ai_health_returns_degraded_when_no_providers() -> None:
    app = FastAPI()
    app.include_router(router)
    setup_exception_handlers(app)
    mock_container = MagicMock()
    mock_container.provider_registry.list_all.return_value = []

    with (
        patch("ai_news_digest.bootstrap.container.Container") as mock_container_cls,
        patch("ai_news_digest.infrastructure.database.session.SessionLocal") as mock_session_cls,
        patch("ai_news_digest.api.v1.routes.health.settings") as mock_settings,
        patch("ai_news_digest.api.v1.routes.health.get_settings") as mock_get_settings,
    ):
        mock_container_cls.return_value = mock_container
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session_cls.return_value = mock_session
        mock_settings.ai_enabled = False
        mock_get_settings.return_value = mock_settings
        with TestClient(app) as test_client:
            response = test_client.get("/health/ai")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["ai_enabled"] is False


def test_ai_health_reports_degraded_on_container_failure() -> None:
    app = FastAPI()
    app.include_router(router)
    setup_exception_handlers(app)

    with patch("ai_news_digest.bootstrap.container.Container") as mock_container_cls:
        mock_container_cls.side_effect = RuntimeError("container init failed")
        with TestClient(app) as test_client:
            response = test_client.get("/health/ai")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert "error" in data


def test_ai_health_reports_quota_info() -> None:
    app = FastAPI()
    app.include_router(router)
    setup_exception_handlers(app)
    mock_provider = MagicMock()
    mock_provider.id = "openai"
    mock_provider.name = "OpenAI"
    mock_provider.model_name = "gpt-4o-mini"
    mock_provider.available = AsyncMock(return_value=True)

    mock_quota_registry = MagicMock()
    mock_quota_registry.get_global_budget = AsyncMock(
        return_value=GlobalBudgetState(
            daily_budget=Decimal("10.0"),
            monthly_budget=Decimal("100.0"),
            daily_spend=Decimal("2.5"),
            monthly_spend=Decimal("25.0"),
        )
    )
    mock_quota_registry.get_provider_quota = AsyncMock(
        return_value=ProviderQuotaConfig(
            provider_id="openai",
            limits=[
                QuotaLimit(
                    window=QuotaWindow.DAY,
                    request_limit=100,
                    token_limit=10000,
                    cost_limit=Decimal("5.0"),
                )
            ],
        )
    )

    mock_container = MagicMock()
    mock_container.provider_registry.list_all.return_value = [mock_provider]
    mock_container.provider_health_registry = None
    mock_container.provider_quota_registry = mock_quota_registry

    with (
        patch("ai_news_digest.bootstrap.container.Container") as mock_container_cls,
        patch("ai_news_digest.infrastructure.database.session.SessionLocal") as mock_session_cls,
        patch("ai_news_digest.api.v1.routes.health.settings") as mock_settings,
        patch("ai_news_digest.api.v1.routes.health.get_settings") as mock_get_settings,
    ):
        mock_container_cls.return_value = mock_container
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session_cls.return_value = mock_session
        mock_settings.ai_enabled = True
        mock_get_settings.return_value = mock_settings
        with TestClient(app) as test_client:
            response = test_client.get("/health/ai")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "global_budget" in data
    assert data["global_budget"]["daily_budget"] == 10.0
    assert data["global_budget"]["daily_spend"] == 2.5
    assert "quota_limits" in data["providers"]["openai"]


def test_ai_health_handles_quota_registry_failure() -> None:
    app = FastAPI()
    app.include_router(router)
    setup_exception_handlers(app)
    mock_provider = MagicMock()
    mock_provider.id = "openai"
    mock_provider.name = "OpenAI"
    mock_provider.model_name = "gpt-4o-mini"
    mock_provider.available = AsyncMock(return_value=True)

    mock_quota_registry = MagicMock()
    mock_quota_registry.get_global_budget = AsyncMock(side_effect=RuntimeError("quota down"))
    mock_quota_registry.get_provider_quota = AsyncMock(side_effect=RuntimeError("quota down"))

    mock_container = MagicMock()
    mock_container.provider_registry.list_all.return_value = [mock_provider]
    mock_container.provider_health_registry = None
    mock_container.provider_quota_registry = mock_quota_registry

    with (
        patch("ai_news_digest.bootstrap.container.Container") as mock_container_cls,
        patch("ai_news_digest.infrastructure.database.session.SessionLocal") as mock_session_cls,
        patch("ai_news_digest.api.v1.routes.health.settings") as mock_settings,
        patch("ai_news_digest.api.v1.routes.health.get_settings") as mock_get_settings,
    ):
        mock_container_cls.return_value = mock_container
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session_cls.return_value = mock_session
        mock_settings.ai_enabled = True
        mock_get_settings.return_value = mock_settings
        with TestClient(app) as test_client:
            response = test_client.get("/health/ai")
    assert response.status_code == 200
    data = response.json()
    assert "global_budget" in data
    assert "error" in data["global_budget"]
    assert "quota_error" in data["providers"]["openai"]


__all__ = [
    "test_ai_health_handles_quota_registry_failure",
    "test_ai_health_reports_degraded_on_container_failure",
    "test_ai_health_reports_quota_info",
    "test_ai_health_returns_degraded_when_no_providers",
    "test_ai_health_returns_ok_when_providers_available",
    "test_liveness_returns_alive",
    "test_notification_health_check_reports_degraded_on_failure",
    "test_notification_health_check_returns_status",
    "test_readiness_caches_result",
    "test_readiness_returns_degraded_when_cache_unavailable",
    "test_readiness_returns_degraded_when_database_unavailable",
    "test_readiness_returns_ok_when_dependencies_healthy",
]
