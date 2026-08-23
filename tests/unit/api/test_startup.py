"""
Application startup tests: middleware installation and request lifecycle.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from ai_news_digest.api.middleware.logging import LoggingMiddleware
from ai_news_digest.api.middleware.rate_limit import RateLimitMiddleware
from ai_news_digest.api.middleware.request_id import RequestIDMiddleware
from ai_news_digest.infrastructure.cache.redis_store import RedisStore
from ai_news_digest.main import app


def test_middleware_installed() -> None:
    """The three project middlewares must be registered on the app."""
    middleware_classes = {mw.cls for mw in app.user_middleware}

    assert RequestIDMiddleware in middleware_classes
    assert LoggingMiddleware in middleware_classes
    assert RateLimitMiddleware in middleware_classes


def test_request_id_and_logging_headers_present() -> None:
    """
    A request must receive the X-Request-ID and X-Process-Time headers,
    proving the request-id and logging middleware are active.
    """
    with (
        patch.object(RedisStore, "get", new_callable=AsyncMock, return_value=None),
        patch.object(RedisStore, "set", new_callable=AsyncMock, return_value=None),
        TestClient(app) as client,
    ):
        response = client.get("/health/live")

    assert response.status_code == 200
    assert response.headers["X-Request-ID"]
    assert response.headers["X-Process-Time"]


def test_health_endpoints_bypass_rate_limit() -> None:
    """
    Health endpoints must remain reachable even when the client has
    exceeded the rate limit, proving the middleware exempts them.
    """
    with (
        patch.object(
            RedisStore,
            "get",
            new_callable=AsyncMock,
            return_value="999",
        ),
        patch.object(RedisStore, "set", new_callable=AsyncMock, return_value=None),
        TestClient(app) as client,
    ):
        live_response = client.get("/health/live")
        ready_response = client.get("/health/ready")

    assert live_response.status_code == 200
    assert live_response.json()["status"] == "alive"
    assert ready_response.status_code in (200, 503)


def test_exception_handlers_registered() -> None:
    """Exception handlers must remain registered after middleware setup."""
    from ai_news_digest.core.exceptions import (
        DatabaseError,
        ExternalServiceError,
        ResourceNotFoundError,
        ValidationError,
    )

    handlers = app.exception_handlers

    assert handlers[ResourceNotFoundError] is not None
    assert handlers[ValidationError] is not None
    assert handlers[ExternalServiceError] is not None
    assert handlers[DatabaseError] is not None
