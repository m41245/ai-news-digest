from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from ai_news_digest.core.config import settings

# Methods that, by definition, do not carry a request body to protect against.
_BODYLESS_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}


class MaxBodySizeMiddleware(BaseHTTPMiddleware):
    """
    Reject requests whose declared body size exceeds the configured maximum.

    This protects the API from abusive large-payload requests. Enforcement is
    based on the ``Content-Length`` header so the body is never read into
    memory as part of the check.
    """

    def __init__(
        self,
        app: ASGIApp,
        max_content_length: int | None = None,
    ) -> None:
        super().__init__(app)
        self._max_content_length = max_content_length or settings.max_request_size_bytes

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Process the request and enforce the maximum body size."""
        if request.method in _BODYLESS_METHODS:
            return await call_next(request)

        content_length = request.headers.get("content-length")
        if content_length:
            try:
                length = int(content_length)
            except ValueError:
                length = 0
            if length > self._max_content_length:
                return JSONResponse(
                    status_code=413,
                    content={"detail": "Request entity too large."},
                )

        return await call_next(request)


__all__ = ["MaxBodySizeMiddleware"]
