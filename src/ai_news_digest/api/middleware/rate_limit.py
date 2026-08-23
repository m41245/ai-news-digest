from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from ai_news_digest.core.config import settings
from ai_news_digest.core.exceptions import ExternalServiceError
from ai_news_digest.core.logging import get_logger

if TYPE_CHECKING:
    from ai_news_digest.domain.ports.cache_store import CacheStore


logger = get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for rate limiting HTTP requests using Redis cache."""

    def __init__(
        self,
        app: ASGIApp,
        cache_store: CacheStore,
        requests_per_minute: int | None = None,
        window_seconds: int | None = None,
    ) -> None:
        super().__init__(app)
        self._cache_store = cache_store
        self._requests_per_minute = requests_per_minute or settings.rate_limit
        self._window_seconds = window_seconds or settings.rate_limit_window

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Process the request and apply rate limiting."""
        if request.url.path in {"/health/live", "/health/ready"}:
            return await call_next(request)

        client_id = self._get_client_id(request)
        key = f"ratelimit:{client_id}"

        try:
            current = await self._cache_store.get(key)

            if current is None:
                await self._cache_store.set(key, "1", ttl=self._window_seconds)
            else:
                count = int(current)
                if count >= self._requests_per_minute:
                    logger.warning(
                        "rate_limit_exceeded",
                        client_id=client_id,
                        path=request.url.path,
                    )
                    return JSONResponse(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        content={"detail": "Rate limit exceeded."},
                    )
                await self._cache_store.set(key, str(count + 1), ttl=self._window_seconds)
        except ExternalServiceError as exc:
            logger.warning(
                "rate_limit_cache_unavailable",
                client_id=client_id,
                error=str(exc),
            )
        except Exception as exc:
            logger.warning(
                "rate_limit_unexpected_error",
                client_id=client_id,
                error=str(exc),
            )

        response = await call_next(request)
        return response

    def _get_client_id(self, request: Request) -> str:
        """Get client identifier for rate limiting."""
        client = request.client
        return client.host if client else "unknown"


__all__ = ["RateLimitMiddleware"]
