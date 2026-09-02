from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from ai_news_digest.core.config import settings


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
        is_production = settings.environment == "production"
        # Only add HSTS in production (served over HTTPS)
        if is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        # CSP: restrict scripts and frames to prevent XSS.
        # In production, the API serves JSON only so 'none' is safe.
        # In non-production, allow 'self' so Swagger UI works.
        if is_production:
            csp = (
                "default-src 'self'; script-src 'none'; "
                "object-src 'none'; frame-ancestors 'none'"
            )
        else:
            csp = (
                "default-src 'self'; script-src 'self'; "
                "object-src 'none'; frame-ancestors 'none'"
            )
        response.headers["Content-Security-Policy"] = csp
        return response


__all__ = ["SecurityHeadersMiddleware"]
