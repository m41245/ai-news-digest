"""
Unit tests for health API routes.
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from ai_news_digest.api.v1.routes.health import _readiness_cache, router


@pytest.fixture(autouse=True)
def _clear_readiness_cache() -> None:
    _readiness_cache.clear()
    yield
    _readiness_cache.clear()


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the health router."""
    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as test_client:
        yield test_client


def test_liveness_returns_200(client: TestClient) -> None:
    """Test liveness endpoint always returns 200."""
    response = client.get("/health/live")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"
    assert data["application"] == "AI News Digest"


def test_liveness_does_not_depend_on_external_services(client: TestClient) -> None:
    """Test liveness endpoint never fails due to external services."""
    with (
        patch(
            "ai_news_digest.api.v1.routes.health.engine",
            MagicMock(),
        ),
        patch(
            "ai_news_digest.api.v1.routes.health.RedisStore",
            side_effect=Exception("redis down"),
        ),
    ):
        response = client.get("/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"


def test_readiness_returns_200_when_healthy(
    client: TestClient,
) -> None:
    """Test readiness endpoint returns 200 when dependencies are healthy."""
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock(return_value=None)

    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    mock_engine = MagicMock()
    mock_engine.connect = MagicMock(return_value=mock_ctx)

    mock_store = AsyncMock()
    mock_store.set = AsyncMock(return_value=None)
    mock_store.delete = AsyncMock(return_value=None)

    with (
        patch("ai_news_digest.api.v1.routes.health.engine", mock_engine),
        patch(
            "ai_news_digest.api.v1.routes.health.RedisStore",
            return_value=mock_store,
        ),
    ):
        response = client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["checks"]["database"] == "ok"
        assert data["checks"]["cache"] == "ok"


def test_readiness_returns_503_when_database_fails(
    client: TestClient,
) -> None:
    """Test readiness returns 503 when database is unavailable."""
    mock_engine = MagicMock()
    mock_engine.connect = MagicMock(
        side_effect=OperationalError("SELECT 1", None, Exception("db down"))
    )

    with (
        patch("ai_news_digest.api.v1.routes.health.engine", mock_engine),
        patch(
            "ai_news_digest.api.v1.routes.health.RedisStore",
            return_value=AsyncMock(),
        ),
    ):
        response = client.get("/health/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "degraded"
        assert data["checks"]["database"] == "unavailable"


def test_readiness_returns_503_when_redis_fails(
    client: TestClient,
) -> None:
    """Test readiness returns 503 when Redis is unavailable."""
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock(return_value=None)

    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    mock_engine = MagicMock()
    mock_engine.connect = MagicMock(return_value=mock_ctx)

    with (
        patch("ai_news_digest.api.v1.routes.health.engine", mock_engine),
        patch(
            "ai_news_digest.api.v1.routes.health.RedisStore",
            side_effect=Exception("redis down"),
        ),
    ):
        response = client.get("/health/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "degraded"
        assert data["checks"]["cache"] == "unavailable"


def test_readiness_caches_result(client: TestClient) -> None:
    """Test readiness caches result to avoid thundering herd."""
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock(return_value=None)

    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    mock_engine = MagicMock()
    mock_engine.connect = MagicMock(return_value=mock_ctx)

    mock_store = AsyncMock()
    mock_store.set = AsyncMock(return_value=None)
    mock_store.delete = AsyncMock(return_value=None)

    with (
        patch("ai_news_digest.api.v1.routes.health.engine", mock_engine),
        patch(
            "ai_news_digest.api.v1.routes.health.RedisStore",
            return_value=mock_store,
        ),
    ):
        response1 = client.get("/health/ready")
        assert response1.status_code == 200
        response2 = client.get("/health/ready")
        assert response2.status_code == 200
        assert mock_engine.connect.call_count == 1


def test_readiness_bypasses_cache_after_ttl(client: TestClient) -> None:
    """Test readiness bypasses cache after TTL expires."""
    with patch("ai_news_digest.api.v1.routes.health.time") as mock_time:
        mock_time.time.return_value = 1000.0
        _readiness_cache["result"] = ({}, 503)
        _readiness_cache["ts"] = 990.0

        mock_time.time.return_value = 1007.0

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value=None)

        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_engine = MagicMock()
        mock_engine.connect = MagicMock(return_value=mock_ctx)

        mock_store = AsyncMock()
        mock_store.set = AsyncMock(return_value=None)
        mock_store.delete = AsyncMock(return_value=None)

        with (
            patch("ai_news_digest.api.v1.routes.health.engine", mock_engine),
            patch(
                "ai_news_digest.api.v1.routes.health.RedisStore",
                return_value=mock_store,
            ),
        ):
            response = client.get("/health/ready")
            assert response.status_code == 200
            assert mock_engine.connect.call_count == 1


def test_readiness_includes_startup_time(client: TestClient) -> None:
    """Test readiness includes startup_time when configured."""
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock(return_value=None)

    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    mock_engine = MagicMock()
    mock_engine.connect = MagicMock(return_value=mock_ctx)

    mock_store = AsyncMock()
    mock_store.set = AsyncMock(return_value=None)
    mock_store.delete = AsyncMock(return_value=None)

    mock_settings = MagicMock()
    mock_settings.app_name = "AI News Digest"
    mock_settings.app_version = "0.1.0"
    mock_settings.environment = "testing"
    mock_settings.app_startup_time = 1700000000.0

    with (
        patch("ai_news_digest.api.v1.routes.health.engine", mock_engine),
        patch(
            "ai_news_digest.api.v1.routes.health.RedisStore",
            return_value=mock_store,
        ),
        patch(
            "ai_news_digest.api.v1.routes.health.settings",
            mock_settings,
        ),
    ):
        response = client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert "startup_time" in data
        assert data["startup_time"] == 1700000000.0


def test_readiness_returns_503_when_both_dependencies_fail(
    client: TestClient,
) -> None:
    """Test readiness returns 503 when both database and Redis fail."""
    mock_engine = MagicMock()
    mock_engine.connect = MagicMock(
        side_effect=OperationalError("SELECT 1", None, Exception("db down"))
    )

    with (
        patch("ai_news_digest.api.v1.routes.health.engine", mock_engine),
        patch(
            "ai_news_digest.api.v1.routes.health.RedisStore",
            side_effect=Exception("redis down"),
        ),
    ):
        response = client.get("/health/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "degraded"
        assert data["checks"]["database"] == "unavailable"
        assert data["checks"]["cache"] == "unavailable"


def test_health_check_speed(client: TestClient) -> None:
    """Test health checks are fast."""
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock(return_value=None)

    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    mock_engine = MagicMock()
    mock_engine.connect = MagicMock(return_value=mock_ctx)

    mock_store = AsyncMock()
    mock_store.set = AsyncMock(return_value=None)
    mock_store.delete = AsyncMock(return_value=None)

    with (
        patch("ai_news_digest.api.v1.routes.health.engine", mock_engine),
        patch(
            "ai_news_digest.api.v1.routes.health.RedisStore",
            return_value=mock_store,
        ),
    ):
        start = time.time()
        response = client.get("/health/ready")
        elapsed = time.time() - start
        assert response.status_code == 200
        assert elapsed < 1.0


__all__ = ["router"]
