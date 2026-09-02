from __future__ import annotations

import json
import logging
from typing import Any
from urllib.parse import urlparse

import redis.asyncio as aioredis
from redis.backoff import NoBackoff
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError
from redis.retry import Retry

from ai_news_digest.core.config import settings
from ai_news_digest.core.exceptions import ExternalServiceError
from ai_news_digest.domain.ports.cache_store import CacheStore

logger = logging.getLogger(__name__)


class RedisStore(CacheStore):
    """
    Redis implementation of the Cache port.

    Failure behavior: fail-closed. If Redis is unavailable, operations raise
    ExternalServiceError rather than silently falling back to an unauthenticated
    or unthrottled path. This preserves the security guarantees of rate limiting
    and other cache-dependent features.
    """

    def __init__(self, redis_url: str | None = None) -> None:
        self._redis_url = redis_url or settings.redis_url
        self._client: aioredis.Redis | None = None
        self._pool: aioredis.ConnectionPool | None = None

    def _build_client(self) -> aioredis.Redis:
        """Build a Redis client with connection pooling and retry configuration."""
        supported_errors: list[type[Exception]] = []
        if settings.redis_retry_on_connection_error:
            supported_errors.append(RedisConnectionError)
        if settings.redis_retry_on_timeout:
            supported_errors.append(RedisTimeoutError)

        retry = Retry(
            backoff=NoBackoff(),
            retries=3 if supported_errors else 0,
            supported_errors=tuple(supported_errors) if supported_errors else (),
        )
        parsed = urlparse(self._redis_url)
        pool = aioredis.ConnectionPool(
            host=parsed.hostname or "localhost",
            port=parsed.port or 6379,
            db=int(parsed.path.lstrip("/") or 0),
            username=parsed.username or None,
            password=parsed.password or None,
            max_connections=settings.redis_max_connections,
            retry=retry,
            socket_connect_timeout=settings.redis_socket_connect_timeout,
            socket_timeout=settings.redis_socket_timeout,
            decode_responses=True,
        )
        self._pool = pool
        return aioredis.Redis(connection_pool=pool)

    async def _ensure_connected(self) -> aioredis.Redis:
        """Ensure Redis client is connected."""
        if self._client is None:
            try:
                self._client = self._build_client()
            except Exception as exc:
                logger.error("Redis connection failed: %s", exc)
                raise ExternalServiceError(f"Redis connection failed: {exc}") from exc
        return self._client

    async def is_connected(self) -> bool:
        """Check if Redis is available without raising on failure."""
        try:
            client = await self._ensure_connected()
            return bool(await client.ping())
        except Exception as exc:
            logger.warning("Redis is not connected: %s", exc)
            return False

    async def ping(self) -> bool:
        """Health check ping for Redis. Returns True if available, False otherwise."""
        return await self.is_connected()

    async def connectivity_metric(self) -> int:
        """Return ``1`` when Redis is connected, ``0`` otherwise.

        Intended for use by the metrics endpoint (``redis_connected`` gauge).
        Never raises: a connectivity problem is reported as ``0``.
        """
        return 1 if await self.is_connected() else 0

    async def startup_check(self) -> None:
        """
        Startup health check.

        Logs a warning if Redis is unavailable but does not raise,
        allowing the application to continue for non-critical operations.
        """
        if not await self.is_connected():
            logger.warning(
                "Redis is unavailable at startup. Cache-dependent features will be degraded."
            )

    async def get(self, key: str) -> str | None:
        """Retrieve a value from Redis by key."""
        try:
            client = await self._ensure_connected()
            value = await client.get(key)
            return str(value) if value is not None else None
        except Exception as exc:
            logger.error("Redis get failed for key %s: %s", key, exc)
            raise ExternalServiceError(f"Redis get failed: {exc}") from exc

    async def set(
        self,
        key: str,
        value: str | bytes | int | float | dict[str, Any] | list[Any],
        ttl: int | None = None,
    ) -> None:
        """Store a value in Redis with optional TTL."""
        try:
            client = await self._ensure_connected()
            if isinstance(value, int | float):
                value = str(value)
            elif isinstance(value, dict | list):
                value = json.dumps(value)

            if ttl:
                await client.set(key, value, ex=ttl)
            else:
                await client.set(key, value)
        except Exception as exc:
            logger.error("Redis set failed for key %s: %s", key, exc)
            raise ExternalServiceError(f"Redis set failed: {exc}") from exc

    async def delete(self, key: str) -> None:
        """Delete a key from Redis."""
        try:
            client = await self._ensure_connected()
            await client.delete(key)
        except Exception as exc:
            logger.error("Redis delete failed for key %s: %s", key, exc)
            raise ExternalServiceError(f"Redis delete failed: {exc}") from exc

    async def exists(self, key: str) -> bool:
        """Check if a key exists in Redis."""
        try:
            client = await self._ensure_connected()
            return bool(await client.exists(key))
        except Exception as exc:
            logger.error("Redis exists check failed for key %s: %s", key, exc)
            raise ExternalServiceError(f"Redis exists check failed: {exc}") from exc

    async def clear(self) -> None:
        """Clear all keys from the current database."""
        try:
            client = await self._ensure_connected()
            await client.flushdb()
            logger.info("Redis cache cleared")
        except Exception as exc:
            logger.error("Redis clear failed: %s", exc)
            raise ExternalServiceError(f"Redis clear failed: {exc}") from exc

    async def ttl(self, key: str) -> int | None:
        """Return the remaining TTL (seconds) for a key, or None if absent/no TTL."""
        try:
            client = await self._ensure_connected()
            value = await client.ttl(key)
            if value is None or value < 0:
                return None
            return int(value)
        except Exception as exc:
            logger.error("Redis ttl failed for key %s: %s", key, exc)
            raise ExternalServiceError(f"Redis ttl failed: {exc}") from exc

    async def close(self) -> None:
        """Close the Redis connection."""
        if self._client:
            try:
                await self._client.close()
                self._client = None
            except Exception as exc:
                logger.error("Redis close failed: %s", exc)
        if self._pool:
            try:
                await self._pool.disconnect()
                self._pool = None
            except Exception as exc:
                logger.error("Redis pool disconnect failed: %s", exc)

    async def __aenter__(self) -> RedisStore:
        """Enter async context manager."""
        await self._ensure_connected()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit async context manager and close connection."""
        await self.close()


__all__ = ["RedisStore"]
