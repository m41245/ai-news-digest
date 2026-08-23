"""
Unit tests for RateLimitMiddleware.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.requests import Request
from starlette.responses import JSONResponse


@pytest.fixture
def mock_cache_store():
    """Create a mock CacheStore."""
    cache = AsyncMock()
    return cache


@pytest.fixture
def rate_limit_middleware(mock_cache_store):
    """Create RateLimitMiddleware instance."""
    from ai_news_digest.api.middleware.rate_limit import RateLimitMiddleware

    return RateLimitMiddleware(
        app=MagicMock(),
        cache_store=mock_cache_store,
        requests_per_minute=60,
    )


@pytest.mark.asyncio
async def test_rate_limit_middleware_first_request(rate_limit_middleware, mock_cache_store) -> None:
    """Test middleware allows first request and sets counter."""
    request = MagicMock(spec=Request)
    request.headers = {}
    request.url.path = "/test"
    request.client = MagicMock()
    request.client.host = "127.0.0.1"

    mock_cache_store.get.return_value = None

    response = MagicMock()
    call_next = AsyncMock(return_value=response)

    await rate_limit_middleware.dispatch(request, call_next)

    mock_cache_store.get.assert_called_once()
    mock_cache_store.set.assert_called_once_with("ratelimit:127.0.0.1", "1", ttl=60)
    call_next.assert_called_once_with(request)


@pytest.mark.asyncio
async def test_rate_limit_middleware_under_limit(rate_limit_middleware, mock_cache_store) -> None:
    """Test middleware allows requests under limit."""
    request = MagicMock(spec=Request)
    request.headers = {}
    request.url.path = "/test"
    request.client = MagicMock()
    request.client.host = "127.0.0.1"

    mock_cache_store.get.return_value = "30"

    response = MagicMock()
    call_next = AsyncMock(return_value=response)

    await rate_limit_middleware.dispatch(request, call_next)

    mock_cache_store.set.assert_called_once_with("ratelimit:127.0.0.1", "31", ttl=60)
    call_next.assert_called_once_with(request)


@pytest.mark.asyncio
async def test_rate_limit_middleware_exceeds_limit(rate_limit_middleware, mock_cache_store) -> None:
    """Test middleware blocks requests exceeding limit with HTTP 429."""
    request = MagicMock(spec=Request)
    request.headers = {}
    request.url.path = "/test"
    request.client = MagicMock()
    request.client.host = "127.0.0.1"

    mock_cache_store.get.return_value = "60"

    response = MagicMock()
    call_next = AsyncMock(return_value=response)

    result = await rate_limit_middleware.dispatch(request, call_next)

    assert isinstance(result, JSONResponse)
    assert result.status_code == 429
    assert result.body is not None
    body = json.loads(result.body.decode())
    assert body["detail"] == "Rate limit exceeded."
    call_next.assert_not_called()


@pytest.mark.asyncio
async def test_rate_limit_middleware_ignores_x_forwarded_for(
    rate_limit_middleware, mock_cache_store
) -> None:
    """Test middleware ignores the spoofable X-Forwarded-For header and uses the direct peer."""
    request = MagicMock(spec=Request)
    request.headers = {"X-Forwarded-For": "10.0.0.1, 10.0.0.2"}
    request.url.path = "/test"
    request.client = MagicMock()
    request.client.host = "127.0.0.1"

    mock_cache_store.get.return_value = None

    response = MagicMock()
    call_next = AsyncMock(return_value=response)

    await rate_limit_middleware.dispatch(request, call_next)

    mock_cache_store.get.assert_called_once_with("ratelimit:127.0.0.1")
    mock_cache_store.set.assert_called_once_with("ratelimit:127.0.0.1", "1", ttl=60)


@pytest.mark.asyncio
async def test_rate_limit_middleware_handles_no_client(
    rate_limit_middleware, mock_cache_store
) -> None:
    """Test middleware handles request without client."""
    request = MagicMock(spec=Request)
    request.headers = {}
    request.url.path = "/test"
    request.client = None

    mock_cache_store.get.return_value = None

    response = MagicMock()
    call_next = AsyncMock(return_value=response)

    await rate_limit_middleware.dispatch(request, call_next)

    mock_cache_store.get.assert_called_once_with("ratelimit:unknown")


@pytest.mark.asyncio
async def test_rate_limit_middleware_exempts_health_live(
    rate_limit_middleware, mock_cache_store
) -> None:
    """Test middleware exempts /health/live from rate limiting."""
    request = MagicMock(spec=Request)
    request.headers = {}
    request.url.path = "/health/live"
    request.client = MagicMock()
    request.client.host = "127.0.0.1"

    response = MagicMock()
    call_next = AsyncMock(return_value=response)

    await rate_limit_middleware.dispatch(request, call_next)

    mock_cache_store.get.assert_not_called()
    mock_cache_store.set.assert_not_called()
    call_next.assert_called_once_with(request)


@pytest.mark.asyncio
async def test_rate_limit_middleware_exempts_health_ready(
    rate_limit_middleware, mock_cache_store
) -> None:
    """Test middleware exempts /health/ready from rate limiting."""
    request = MagicMock(spec=Request)
    request.headers = {}
    request.url.path = "/health/ready"
    request.client = MagicMock()
    request.client.host = "127.0.0.1"

    response = MagicMock()
    call_next = AsyncMock(return_value=response)

    await rate_limit_middleware.dispatch(request, call_next)

    mock_cache_store.get.assert_not_called()
    mock_cache_store.set.assert_not_called()
    call_next.assert_called_once_with(request)


@pytest.mark.asyncio
async def test_rate_limit_middleware_custom_limit(rate_limit_middleware, mock_cache_store) -> None:
    """Test middleware respects custom rate limit."""
    from ai_news_digest.api.middleware.rate_limit import RateLimitMiddleware

    middleware = RateLimitMiddleware(
        app=MagicMock(),
        cache_store=mock_cache_store,
        requests_per_minute=10,
    )

    request = MagicMock(spec=Request)
    request.headers = {}
    request.url.path = "/test"
    request.client = MagicMock()
    request.client.host = "127.0.0.1"

    mock_cache_store.get.return_value = "10"

    response = MagicMock()
    call_next = AsyncMock(return_value=response)

    result = await middleware.dispatch(request, call_next)

    assert isinstance(result, JSONResponse)
    assert result.status_code == 429


@pytest.mark.asyncio
async def test_rate_limit_middleware_handles_redis_outage(
    mock_cache_store,
) -> None:
    """Test middleware allows requests when Redis is unavailable."""
    from ai_news_digest.api.middleware.rate_limit import RateLimitMiddleware
    from ai_news_digest.core.exceptions import ExternalServiceError

    middleware = RateLimitMiddleware(
        app=MagicMock(),
        cache_store=mock_cache_store,
        requests_per_minute=60,
    )

    request = MagicMock(spec=Request)
    request.headers = {}
    request.url.path = "/test"
    request.client = MagicMock()
    request.client.host = "127.0.0.1"

    mock_cache_store.get.side_effect = ExternalServiceError("Redis unavailable")

    response = MagicMock()
    call_next = AsyncMock(return_value=response)

    result = await middleware.dispatch(request, call_next)

    assert result == response
    call_next.assert_called_once_with(request)


__all__ = [
    "test_rate_limit_middleware_custom_limit",
    "test_rate_limit_middleware_exceeds_limit",
    "test_rate_limit_middleware_exempts_health_live",
    "test_rate_limit_middleware_exempts_health_ready",
    "test_rate_limit_middleware_first_request",
    "test_rate_limit_middleware_handles_no_client",
    "test_rate_limit_middleware_handles_redis_outage",
    "test_rate_limit_middleware_ignores_x_forwarded_for",
    "test_rate_limit_middleware_under_limit",
]
