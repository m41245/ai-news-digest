"""
Unit tests for RequestIDMiddleware.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.requests import Request
from starlette.responses import Response


@pytest.fixture
def request_id_middleware():
    """Create RequestIDMiddleware instance."""
    from ai_news_digest.api.middleware.request_id import RequestIDMiddleware

    return RequestIDMiddleware(app=MagicMock())


@pytest.mark.asyncio
async def test_request_id_middleware_generates_new_id(request_id_middleware) -> None:
    """Test middleware generates new request ID when not provided."""
    request = MagicMock(spec=Request)
    request.headers = {}
    request.url.path = "/test"
    request.state = MagicMock()

    response = Response(status_code=200)
    call_next = AsyncMock(return_value=response)

    await request_id_middleware.dispatch(request, call_next)

    assert hasattr(request.state, "request_id")
    assert request.state.request_id is not None
    assert response.headers["X-Request-ID"] == request.state.request_id
    call_next.assert_called_once_with(request)


@pytest.mark.asyncio
async def test_request_id_middleware_uses_existing_id(request_id_middleware) -> None:
    """Test middleware uses existing request ID from header."""
    request = MagicMock(spec=Request)
    request.headers = {"X-Request-ID": "existing-id-123"}
    request.url.path = "/test"
    request.state = MagicMock()

    response = Response(status_code=200)
    call_next = AsyncMock(return_value=response)

    await request_id_middleware.dispatch(request, call_next)

    assert request.state.request_id == "existing-id-123"
    assert response.headers["X-Request-ID"] == "existing-id-123"


@pytest.mark.asyncio
async def test_request_id_middleware_assigns_to_state(request_id_middleware) -> None:
    """Test middleware assigns request ID to request state."""
    request = MagicMock(spec=Request)
    request.headers = {}
    request.url.path = "/test"
    request.state = MagicMock()

    response = MagicMock()
    call_next = AsyncMock(return_value=response)

    await request_id_middleware.dispatch(request, call_next)

    assert hasattr(request.state, "request_id")
