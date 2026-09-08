from __future__ import annotations

import json
from typing import TYPE_CHECKING

from fastapi import status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from ai_news_digest.core.config import settings
from ai_news_digest.core.exceptions import ExternalServiceError
from ai_news_digest.core.logging import get_logger
from ai_news_digest.core.metrics import record_auth_failure, record_rate_limit_event

if TYPE_CHECKING:
    from ai_news_digest.domain.ports.cache_store import CacheStore


logger = get_logger(__name__)

_HEALTH_PATHS = {"/health/live", "/health/ready"}


class LoginBruteForceProtector:
    """
    Tracks failed login attempts and applies account lockout.

    Failures are counted per client identifier (client IP, optionally scoped
    to the attempted username). After ``max_attempts`` failures within the
    tracking window, the identifier is locked out. Each successive lockout uses
    a progressively longer duration (exponential backoff capped at
    ``lockout_max_seconds``), which both throttles and delays brute-force
    attempts.
    """

    def __init__(
        self,
        cache_store: CacheStore,
        max_attempts: int = 5,
        window_seconds: int = 900,
        lockout_base_seconds: int = 300,
        lockout_max_seconds: int = 3600,
    ) -> None:
        self._cache = cache_store
        self._max_attempts = max_attempts
        self._window = window_seconds
        self._lockout_base = lockout_base_seconds
        self._lockout_max = lockout_max_seconds
        self._fail_prefix = "auth:fail:"
        self._lock_prefix = "auth:lock:"
        self._lockcount_prefix = "auth:lockcount:"

    async def is_locked_out(self, key: str) -> tuple[bool, int]:
        """
        Return ``(locked, retry_after_seconds)`` for the given identifier.

        Fail-closed: if the cache store is unavailable, treat the identifier
        as locked to prevent brute-force attacks during outages.
        """
        try:
            remaining = await self._cache.ttl(self._lock_prefix + key)
        except ExternalServiceError:
            return True, self._lockout_base
        if remaining is not None and remaining > 0:
            return True, int(remaining)
        return False, 0

    async def record_failure(self, key: str) -> int:
        """
        Record a failed login attempt.

        Returns the lockout duration (seconds) if the identifier was just
        locked out, otherwise ``0``.
        """
        fail_key = self._fail_prefix + key
        try:
            current = await self._cache.get(fail_key)
            count = 1 if current is None or current == "" else int(str(current)) + 1
            await self._cache.set(fail_key, str(count), ttl=self._window)

            if count >= self._max_attempts:
                lock_count_key = self._lockcount_prefix + key
                prior = await self._cache.get(lock_count_key)
                lock_count = 0 if prior is None or prior == "" else int(str(prior))
                duration = min(
                    self._lockout_base * (2**lock_count),
                    self._lockout_max,
                )
                await self._cache.set(self._lock_prefix + key, "1", ttl=duration)
                await self._cache.set(
                    lock_count_key,
                    str(lock_count + 1),
                    ttl=self._window * 10,
                )
                await self._cache.delete(fail_key)
                return int(duration)
        except ExternalServiceError as exc:
            logger.warning("brute_force_record_failure_error", error=str(exc))
        return 0

    async def record_success(self, key: str) -> None:
        """Clear any tracked failures/locks for a successful login."""
        try:
            await self._cache.delete(self._fail_prefix + key)
            await self._cache.delete(self._lock_prefix + key)
            await self._cache.delete(self._lockcount_prefix + key)
        except ExternalServiceError as exc:
            logger.warning("brute_force_record_success_error", error=str(exc))


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for rate limiting HTTP requests using Redis cache."""

    def __init__(
        self,
        app: ASGIApp,
        cache_store: CacheStore,
        requests_per_minute: int | None = None,
        window_seconds: int | None = None,
        auth_requests_per_window: int | None = None,
        auth_window_seconds: int | None = None,
        auth_max_failed_attempts: int | None = None,
        auth_lockout_seconds: int | None = None,
    ) -> None:
        super().__init__(app)
        self._cache_store = cache_store
        self._requests_per_minute = requests_per_minute or settings.rate_limit
        self._window_seconds = window_seconds or settings.rate_limit_window
        self._auth_requests_per_window = auth_requests_per_window or settings.auth_rate_limit
        self._auth_window_seconds = auth_window_seconds or settings.auth_rate_limit_window
        self._protector = LoginBruteForceProtector(
            self._cache_store,
            max_attempts=auth_max_failed_attempts or settings.auth_max_failed_attempts,
            window_seconds=self._auth_window_seconds,
            lockout_base_seconds=auth_lockout_seconds or settings.auth_lockout_seconds,
        )

    def _is_auth_path(self, path: str) -> bool:
        normalized = path.rstrip("/")
        return "/auth/" in path or normalized.endswith("/auth")

    def _is_login_path(self, path: str) -> bool:
        return path.rstrip("/").endswith("/auth/login")

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Process the request and apply rate limiting."""
        path = request.url.path

        if path in _HEALTH_PATHS:
            return await call_next(request)

        bf_key: str | None = None
        if self._is_login_path(path):
            bf_key = await self._login_identifier(request)
            locked, retry_after = await self._protector.is_locked_out(bf_key)
            if locked:
                logger.warning(
                    "login_brute_force_lockout",
                    client_id=self._get_client_id(request),
                )
                record_auth_failure()
                record_rate_limit_event()
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    headers={"Retry-After": str(retry_after)},
                    content={
                        "detail": "Account temporarily locked due to too many "
                        "failed login attempts. Try again later."
                    },
                )

        is_auth = self._is_auth_path(path)
        client_id = self._get_client_id(request)
        key = f"ratelimit:{client_id}:auth" if is_auth else f"ratelimit:{client_id}"
        limit = self._auth_requests_per_window if is_auth else self._requests_per_minute
        window = self._auth_window_seconds if is_auth else self._window_seconds

        try:
            current = await self._cache_store.get(key)

            if current is None:
                await self._cache_store.set(key, "1", ttl=window)
            else:
                count = int(current)
                if count >= limit:
                    logger.warning(
                        "rate_limit_exceeded",
                        client_id=client_id,
                        path=path,
                        auth=is_auth,
                    )
                    record_rate_limit_event()
                    if is_auth:
                        record_auth_failure()
                    return JSONResponse(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        content={"detail": "Rate limit exceeded."},
                    )
                await self._cache_store.set(key, str(count + 1), ttl=window)
        except ExternalServiceError as exc:
            logger.warning(
                "rate_limit_cache_unavailable",
                client_id=client_id,
                error=str(exc),
            )
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"detail": "Rate limit service unavailable."},
            )
        except Exception as exc:
            logger.warning(
                "rate_limit_unexpected_error",
                client_id=client_id,
                error=str(exc),
            )
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"detail": "Rate limit service unavailable."},
            )

        response = await call_next(request)

        if bf_key is not None and self._is_login_path(path):
            if response.status_code == status.HTTP_401_UNAUTHORIZED:
                await self._protector.record_failure(bf_key)
                record_auth_failure()
            elif response.status_code == status.HTTP_200_OK:
                await self._protector.record_success(bf_key)

        return response

    def _get_client_id(self, request: Request) -> str:
        """Get client identifier for rate limiting."""
        client = request.client
        return client.host if client else "unknown"

    async def _login_identifier(self, request: Request) -> str:
        """Build a brute-force tracking key from client IP and attempted username."""
        client_id = self._get_client_id(request)
        username: str | None = None
        try:
            body = await request.body()
            if body:
                data = json.loads(body)
                if isinstance(data, dict):
                    username = data.get("username") or data.get("email")
        except Exception:
            username = None

        if username:
            return f"{client_id}:{username}"
        return client_id


__all__ = ["LoginBruteForceProtector", "RateLimitMiddleware"]
