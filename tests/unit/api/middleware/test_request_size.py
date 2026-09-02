"""
Unit tests for MaxBodySizeMiddleware.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


@pytest.fixture
def max_body_size_middleware():
    """Create MaxBodySizeMiddleware instance with a known limit."""
    from ai_news_digest.api.middleware.request_size import MaxBodySizeMiddleware

    return MaxBodySizeMiddleware(app=MagicMock(), max_content_length=1024)


@pytest.mark.asyncio
async def test_max_body_size_allows_under_limit(
    max_body_size_middleware,
) -> None:
    """Test request under the size limit proceeds normally."""
    request = MagicMock(spec=Request)
    request.method = "POST"
    request.headers = {"content-length": "512"}

    response = Response(status_code=200)
    call_next = AsyncMock(return_value=response)

    result = await max_body_size_middleware.dispatch(request, call_next)

    assert result is response
    call_next.assert_called_once_with(request)


@pytest.mark.asyncio
async def test_max_body_size_rejects_over_limit(
    max_body_size_middleware,
) -> None:
    """Test request exceeding the size limit returns 413."""
    request = MagicMock(spec=Request)
    request.method = "POST"
    request.headers = {"content-length": "2048"}

    response = Response(status_code=200)
    call_next = AsyncMock(return_value=response)

    result = await max_body_size_middleware.dispatch(request, call_next)

    assert isinstance(result, JSONResponse)
    assert result.status_code == 413
    call_next.assert_not_called()


@pytest.mark.asyncio
async def test_max_body_size_allows_exact_limit(
    max_body_size_middleware,
) -> None:
    """Test request exactly at the size limit proceeds normally."""
    request = MagicMock(spec=Request)
    request.method = "POST"
    request.headers = {"content-length": "1024"}

    response = Response(status_code=200)
    call_next = AsyncMock(return_value=response)

    result = await max_body_size_middleware.dispatch(request, call_next)

    assert result is response
    call_next.assert_called_once_with(request)


@pytest.mark.asyncio
async def test_max_body_size_allows_bodyless_methods(
    max_body_size_middleware,
) -> None:
    """Test GET, HEAD, OPTIONS, TRACE bypass body size checks."""
    call_next = AsyncMock(return_value=Response(status_code=200))

    for method in ["GET", "HEAD", "OPTIONS", "TRACE"]:
        request = MagicMock(spec=Request)
        request.method = method
        request.headers = {"content-length": "9999999"}

        result = await max_body_size_middleware.dispatch(request, call_next)

        assert result is call_next.return_value
        call_next.assert_called()


@pytest.mark.asyncio
async def test_max_body_size_allows_missing_content_length(
    max_body_size_middleware,
) -> None:
    """Test request without Content-Length proceeds normally."""
    request = MagicMock(spec=Request)
    request.method = "POST"
    request.headers = {}

    response = Response(status_code=200)
    call_next = AsyncMock(return_value=response)

    result = await max_body_size_middleware.dispatch(request, call_next)

    assert result is response
    call_next.assert_called_once_with(request)


@pytest.mark.asyncio
async def test_max_body_size_handles_invalid_content_length(
    max_body_size_middleware,
) -> None:
    """Test request with non-numeric Content-Length proceeds normally."""
    request = MagicMock(spec=Request)
    request.method = "POST"
    request.headers = {"content-length": "not-a-number"}

    response = Response(status_code=200)
    call_next = AsyncMock(return_value=response)

    result = await max_body_size_middleware.dispatch(request, call_next)

    assert result is response
    call_next.assert_called_once_with(request)


@pytest.mark.asyncio
async def test_max_body_size_uses_configured_default() -> None:
    """Test middleware uses settings.max_request_size_bytes when no override."""
    from ai_news_digest.api.middleware.request_size import MaxBodySizeMiddleware

    middleware = MaxBodySizeMiddleware(app=MagicMock())

    assert middleware._max_content_length == 1048576


@pytest.mark.asyncio
async def test_max_body_size_rejection_returns_json_detail(
    max_body_size_middleware,
) -> None:
    """Test 413 response includes a JSON detail field."""
    request = MagicMock(spec=Request)
    request.method = "POST"
    request.headers = {"content-length": "2048"}

    call_next = AsyncMock(return_value=Response(status_code=200))

    result = await max_body_size_middleware.dispatch(request, call_next)

    assert isinstance(result, JSONResponse)
    assert result.status_code == 413
    assert "detail" in result.body.decode()


__all__ = [
    "test_max_body_size_allows_bodyless_methods",
    "test_max_body_size_allows_exact_limit",
    "test_max_body_size_allows_missing_content_length",
    "test_max_body_size_allows_under_limit",
    "test_max_body_size_handles_invalid_content_length",
    "test_max_body_size_rejection_returns_json_detail",
    "test_max_body_size_rejects_over_limit",
    "test_max_body_size_uses_configured_default",
]
