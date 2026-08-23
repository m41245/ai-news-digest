"""
Unit tests for LoggingMiddleware.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.requests import Request
from starlette.responses import Response


@pytest.fixture
def logging_middleware():
    """Create LoggingMiddleware instance."""
    from ai_news_digest.api.middleware.logging import LoggingMiddleware

    return LoggingMiddleware(app=MagicMock())


@pytest.mark.asyncio
async def test_logging_middleware_logs_request(logging_middleware) -> None:
    """Test middleware logs request details."""
    request = MagicMock(spec=Request)
    request.method = "GET"
    request.url.path = "/test"
    request.client = MagicMock()
    request.client.host = "127.0.0.1"

    response = MagicMock()
    response.status_code = 200
    call_next = AsyncMock(return_value=response)

    with patch("ai_news_digest.api.middleware.logging.logger") as mock_logger:
        await logging_middleware.dispatch(request, call_next)

        assert mock_logger.info.call_count >= 2  # Request started and completed


@pytest.mark.asyncio
async def test_logging_middleware_adds_process_time_header(logging_middleware) -> None:
    """Test middleware adds X-Process-Time header to response."""
    request = MagicMock(spec=Request)
    request.method = "GET"
    request.url.path = "/test"
    request.client = MagicMock()
    request.client.host = "127.0.0.1"

    response = Response(status_code=200)
    call_next = AsyncMock(return_value=response)

    await logging_middleware.dispatch(request, call_next)

    assert "X-Process-Time" in response.headers
    assert float(response.headers["X-Process-Time"]) >= 0


@pytest.mark.asyncio
async def test_logging_middleware_handles_no_client(logging_middleware) -> None:
    """Test middleware handles request without client."""
    request = MagicMock(spec=Request)
    request.method = "GET"
    request.url.path = "/test"
    request.client = None

    response = MagicMock()
    response.status_code = 200
    call_next = AsyncMock(return_value=response)

    with patch("ai_news_digest.api.middleware.logging.logger") as mock_logger:
        await logging_middleware.dispatch(request, call_next)

        # Should not raise error
        assert mock_logger.info.call_count >= 2


@pytest.mark.asyncio
async def test_logging_middleware_logs_status_code(logging_middleware) -> None:
    """Test middleware logs response status code."""
    request = MagicMock(spec=Request)
    request.method = "GET"
    request.url.path = "/test"
    request.client = MagicMock()
    request.client.host = "127.0.0.1"

    response = MagicMock()
    response.status_code = 404
    call_next = AsyncMock(return_value=response)

    with patch("ai_news_digest.api.middleware.logging.logger") as mock_logger:
        await logging_middleware.dispatch(request, call_next)

        # Check that status code was logged
        call_args = mock_logger.info.call_args_list
        assert any("status_code" in str(call) for call in call_args)
