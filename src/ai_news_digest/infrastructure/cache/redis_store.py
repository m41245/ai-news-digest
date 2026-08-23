from __future__ import annotations

import json
import logging
from typing import Any

import redis.asyncio as aioredis

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

    def __init__(self, redis_url: str) -> None:
        self._redis_url = redis_url
        self._client: aioredis.Redis | None = None

    async def _ensure_connected(self) -> aioredis.Redis:
        """Ensure Redis client is connected."""
        if self._client is None:
            try:
                self._client = aioredis.from_url(  # type: ignore[no-untyped-call]
                    self._redis_url,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                )
            except Exception as exc:
                logger.error("Redis connection failed: %s", exc)
                raise ExternalServiceError(f"Redis connection failed: {exc}") from exc
        return self._client

    async def get(self, key: str) -> str | None:
        """Retrieve a value from Redis by key."""
        try:
            client = await self._ensure_connected()
            value: str | None = await client.get(key)
            return value
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
                await client.setex(key, ttl, value)
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

    async def close(self) -> None:
        """Close the Redis connection."""
        if self._client:
            try:
                await self._client.close()
                self._client = None
            except Exception as exc:
                logger.error("Redis close failed: %s", exc)


__all__ = ["RedisStore"]
