"""
Integration tests for Redis connectivity.
"""

from __future__ import annotations

import pytest

from ai_news_digest.infrastructure.cache.redis_store import RedisStore


@pytest.mark.integration
async def test_redis_connectivity(redis_container) -> None:
    """Verify that the Redis test container is reachable."""
    import redis

    client = redis.Redis(
        host=redis_container.get_container_host_ip(),  # type: ignore[attr-defined]
        port=redis_container.get_exposed_port(6379),  # type: ignore[attr-defined]
        decode_responses=True,
    )
    assert client.ping() is True


@pytest.mark.integration
async def test_redis_store_round_trip(redis_container) -> None:
    """Verify that RedisStore can set and get values."""
    host = redis_container.get_container_host_ip()  # type: ignore[attr-defined]
    port = redis_container.get_exposed_port(6379)  # type: ignore[attr-defined]
    store = RedisStore(redis_url=f"redis://{host}:{port}/0")

    await store.set("integration_test_key", "hello", ttl=60)
    value = await store.get("integration_test_key")
    assert value == "hello"
