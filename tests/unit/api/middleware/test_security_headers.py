"""
Unit tests for SecurityHeadersMiddleware.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.requests import Request
from starlette.responses import Response


@pytest.fixture
def security_headers_middleware():
    """Create SecurityHeadersMiddleware instance."""
    from ai_news_digest.api.middleware.security_headers import (
        SecurityHeadersMiddleware,
    )

    return SecurityHeadersMiddleware(app=MagicMock())


@pytest.fixture
def mock_request():
    """Create a mock request."""
    request = MagicMock(spec=Request)
    request.url.path = "/test"
    return request


@pytest.mark.asyncio
async def test_security_headers_middleware_sets_x_content_type_options(
    security_headers_middleware,
    mock_request,
) -> None:
    """Test X-Content-Type-Options header is set to 'nosniff'."""
    response = Response(status_code=200)
    call_next = AsyncMock(return_value=response)

    await security_headers_middleware.dispatch(mock_request, call_next)

    assert response.headers["X-Content-Type-Options"] == "nosniff"


@pytest.mark.asyncio
async def test_security_headers_middleware_sets_x_frame_options(
    security_headers_middleware,
    mock_request,
) -> None:
    """Test X-Frame-Options header is set to 'DENY'."""
    response = Response(status_code=200)
    call_next = AsyncMock(return_value=response)

    await security_headers_middleware.dispatch(mock_request, call_next)

    assert response.headers["X-Frame-Options"] == "DENY"


@pytest.mark.asyncio
async def test_security_headers_middleware_sets_referrer_policy(
    security_headers_middleware,
    mock_request,
) -> None:
    """Test Referrer-Policy header is set."""
    response = Response(status_code=200)
    call_next = AsyncMock(return_value=response)

    await security_headers_middleware.dispatch(mock_request, call_next)

    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


@pytest.mark.asyncio
async def test_security_headers_middleware_sets_permissions_policy(
    security_headers_middleware,
    mock_request,
) -> None:
    """Test Permissions-Policy header denies sensitive APIs."""
    response = Response(status_code=200)
    call_next = AsyncMock(return_value=response)

    await security_headers_middleware.dispatch(mock_request, call_next)

    assert "geolocation=()" in response.headers["Permissions-Policy"]
    assert "microphone=()" in response.headers["Permissions-Policy"]
    assert "camera=()" in response.headers["Permissions-Policy"]


@pytest.mark.asyncio
async def test_security_headers_middleware_sets_restrictive_csp_in_production(
    mock_request,
) -> None:
    """Test CSP with script-src 'none' is set in production."""
    response = Response(status_code=200)
    call_next = AsyncMock(return_value=response)

    mock_settings = MagicMock()
    mock_settings.environment = "production"
    with patch(
        "ai_news_digest.api.middleware.security_headers.settings",
        mock_settings,
    ):
        from ai_news_digest.api.middleware.security_headers import (
            SecurityHeadersMiddleware,
        )

        middleware = SecurityHeadersMiddleware(app=MagicMock())
        await middleware.dispatch(mock_request, call_next)

    csp = response.headers["Content-Security-Policy"]
    assert "default-src 'self'" in csp
    assert "script-src 'none'" in csp
    assert "object-src 'none'" in csp
    assert "frame-ancestors 'none'" in csp


@pytest.mark.asyncio
async def test_security_headers_middleware_sets_permissive_csp_in_non_production(
    mock_request,
) -> None:
    """Test CSP with script-src 'self' is set in non-production for Swagger UI."""
    response = Response(status_code=200)
    call_next = AsyncMock(return_value=response)

    mock_settings = MagicMock()
    mock_settings.environment = "development"
    with patch(
        "ai_news_digest.api.middleware.security_headers.settings",
        mock_settings,
    ):
        from ai_news_digest.api.middleware.security_headers import (
            SecurityHeadersMiddleware,
        )

        middleware = SecurityHeadersMiddleware(app=MagicMock())
        await middleware.dispatch(mock_request, call_next)

    csp = response.headers["Content-Security-Policy"]
    assert "default-src 'self'" in csp
    assert "script-src 'self'" in csp
    assert "object-src 'none'" in csp
    assert "frame-ancestors 'none'" in csp


@pytest.mark.asyncio
async def test_security_headers_middleware_adds_hsts_in_production(mock_request) -> None:
    """Test HSTS header is added only in production mode."""
    response = Response(status_code=200)
    call_next = AsyncMock(return_value=response)

    mock_settings = MagicMock()
    mock_settings.environment = "production"
    with patch(
        "ai_news_digest.api.middleware.security_headers.settings",
        mock_settings,
    ):
        from ai_news_digest.api.middleware.security_headers import (
            SecurityHeadersMiddleware,
        )

        middleware = SecurityHeadersMiddleware(app=MagicMock())
        await middleware.dispatch(mock_request, call_next)

    assert "Strict-Transport-Security" in response.headers
    hsts = response.headers["Strict-Transport-Security"]
    assert "max-age=31536000" in hsts
    assert "includeSubDomains" in hsts


@pytest.mark.asyncio
async def test_security_headers_middleware_omits_hsts_in_development(
    mock_request,
) -> None:
    """Test HSTS header is NOT added in development mode."""
    response = Response(status_code=200)
    call_next = AsyncMock(return_value=response)

    mock_settings = MagicMock()
    mock_settings.environment = "development"
    with patch(
        "ai_news_digest.api.middleware.security_headers.settings",
        mock_settings,
    ):
        from ai_news_digest.api.middleware.security_headers import (
            SecurityHeadersMiddleware,
        )

        middleware = SecurityHeadersMiddleware(app=MagicMock())
        await middleware.dispatch(mock_request, call_next)

    assert "Strict-Transport-Security" not in response.headers


@pytest.mark.asyncio
async def test_security_headers_middleware_omits_hsts_in_staging(mock_request) -> None:
    """Test HSTS header is NOT added in staging mode (only prod over HTTPS)."""
    response = Response(status_code=200)
    call_next = AsyncMock(return_value=response)

    mock_settings = MagicMock()
    mock_settings.environment = "staging"
    with patch(
        "ai_news_digest.api.middleware.security_headers.settings",
        mock_settings,
    ):
        from ai_news_digest.api.middleware.security_headers import (
            SecurityHeadersMiddleware,
        )

        middleware = SecurityHeadersMiddleware(app=MagicMock())
        await middleware.dispatch(mock_request, call_next)

    assert "Strict-Transport-Security" not in response.headers


@pytest.mark.asyncio
async def test_security_headers_middleware_calls_next(
    security_headers_middleware,
    mock_request,
) -> None:
    """Test middleware calls the next handler."""
    response = Response(status_code=200)
    call_next = AsyncMock(return_value=response)

    await security_headers_middleware.dispatch(mock_request, call_next)

    call_next.assert_called_once_with(mock_request)


@pytest.mark.asyncio
async def test_security_headers_middleware_preserves_response_status(
    security_headers_middleware,
    mock_request,
) -> None:
    """Test middleware does not alter the response status code."""
    response = Response(status_code=404)
    call_next = AsyncMock(return_value=response)

    await security_headers_middleware.dispatch(mock_request, call_next)

    assert response.status_code == 404


__all__ = [
    "test_security_headers_middleware_adds_hsts_in_production",
    "test_security_headers_middleware_calls_next",
    "test_security_headers_middleware_omits_hsts_in_development",
    "test_security_headers_middleware_omits_hsts_in_staging",
    "test_security_headers_middleware_preserves_response_status",
    "test_security_headers_middleware_sets_permissions_policy",
    "test_security_headers_middleware_sets_permissive_csp_in_non_production",
    "test_security_headers_middleware_sets_referrer_policy",
    "test_security_headers_middleware_sets_restrictive_csp_in_production",
    "test_security_headers_middleware_sets_x_content_type_options",
    "test_security_headers_middleware_sets_x_frame_options",
]
