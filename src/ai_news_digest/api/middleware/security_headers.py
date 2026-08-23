from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware for adding security headers to HTTP responses."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Process the request and add security headers."""
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        # Only add HSTS when not in development mode
        from ai_news_digest.core.config import settings

        if settings.environment != "development":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        # CSP: restrict to self and needed resources for API responses
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'none'; object-src 'none'; frame-ancestors 'none'"
        )
        return response


__all__ = ["SecurityHeadersMiddleware"]
