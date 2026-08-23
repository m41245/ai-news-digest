from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from ai_news_digest.core.logging import get_logger

logger = get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware for adding unique request IDs to HTTP requests."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Process the request and add request ID."""
        existing_id = request.headers.get("X-Request-ID")

        request_id = existing_id if existing_id else str(uuid.uuid4())

        request.state.request_id = request_id

        logger.info(
            "request_id_assigned",
            request_id=request_id,
            path=request.url.path,
        )

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


__all__ = ["RequestIDMiddleware"]
