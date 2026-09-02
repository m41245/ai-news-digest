"""
Unit tests for RedisStore.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_news_digest.core.exceptions import ExternalServiceError
from ai_news_digest.infrastructure.cache.redis_store import RedisStore


@pytest.fixture
def redis_store() -> RedisStore:
    """Create a RedisStore instance."""
    return RedisStore(redis_url="redis://localhost:6379/0")


@pytest.mark.asyncio
async def test_redis_store_initialization(redis_store: RedisStore) -> None:
    """Test RedisStore initialization."""
    assert redis_store._redis_url == "redis://localhost:6379/0"
    assert redis_store._client is None
    assert redis_store._pool is None


@pytest.mark.asyncio
async def test_redis_store_get_success(redis_store: RedisStore) -> None:
    """Test successful get operation."""
    mock_client = AsyncMock()
    mock_client.get.return_value = "test_value"
    mock_pool = MagicMock()

    with (
        patch("redis.asyncio.ConnectionPool", return_value=mock_pool),
        patch("redis.asyncio.Redis", return_value=mock_client),
    ):
        result = await redis_store.get("test_key")

        assert result == "test_value"
        mock_client.get.assert_called_once_with("test_key")


@pytest.mark.asyncio
async def test_redis_store_get_not_found(redis_store: RedisStore) -> None:
    """Test get operation when key doesn't exist."""
    mock_client = AsyncMock()
    mock_client.get.return_value = None
    mock_pool = MagicMock()

    with (
        patch("redis.asyncio.ConnectionPool", return_value=mock_pool),
        patch("redis.asyncio.Redis", return_value=mock_client),
    ):
        result = await redis_store.get("nonexistent_key")

        assert result is None


@pytest.mark.asyncio
async def test_redis_store_set_string(redis_store: RedisStore) -> None:
    """Test set operation with string value."""
    mock_client = AsyncMock()
    mock_pool = MagicMock()

    with (
        patch("redis.asyncio.ConnectionPool", return_value=mock_pool),
        patch("redis.asyncio.Redis", return_value=mock_client),
    ):
        await redis_store.set("test_key", "test_value")

        mock_client.set.assert_called_once_with("test_key", "test_value")


@pytest.mark.asyncio
async def test_redis_store_set_with_ttl(redis_store: RedisStore) -> None:
    """Test set operation with TTL."""
    mock_client = AsyncMock()
    mock_pool = MagicMock()

    with (
        patch("redis.asyncio.ConnectionPool", return_value=mock_pool),
        patch("redis.asyncio.Redis", return_value=mock_client),
    ):
        await redis_store.set("test_key", "test_value", ttl=60)

        mock_client.set.assert_called_once_with("test_key", "test_value", ex=60)


@pytest.mark.asyncio
async def test_redis_store_set_int(redis_store: RedisStore) -> None:
    """Test set operation with integer value."""
    mock_client = AsyncMock()
    mock_pool = MagicMock()

    with (
        patch("redis.asyncio.ConnectionPool", return_value=mock_pool),
        patch("redis.asyncio.Redis", return_value=mock_client),
    ):
        await redis_store.set("test_key", 42)

        mock_client.set.assert_called_once_with("test_key", "42")


@pytest.mark.asyncio
async def test_redis_store_set_float(redis_store: RedisStore) -> None:
    """Test set operation with float value."""
    mock_client = AsyncMock()
    mock_pool = MagicMock()

    with (
        patch("redis.asyncio.ConnectionPool", return_value=mock_pool),
        patch("redis.asyncio.Redis", return_value=mock_client),
    ):
        await redis_store.set("test_key", 3.14)

        mock_client.set.assert_called_once_with("test_key", "3.14")


@pytest.mark.asyncio
async def test_redis_store_set_dict(redis_store: RedisStore) -> None:
    """Test set operation with dict value (JSON serialization)."""
    mock_client = AsyncMock()
    mock_pool = MagicMock()

    with (
        patch("redis.asyncio.ConnectionPool", return_value=mock_pool),
        patch("redis.asyncio.Redis", return_value=mock_client),
    ):
        await redis_store.set("test_key", {"key": "value"})

        call_args = mock_client.set.call_args[0]
        assert '"key": "value"' in call_args[1]


@pytest.mark.asyncio
async def test_redis_store_set_list(redis_store: RedisStore) -> None:
    """Test set operation with list value (JSON serialization)."""
    mock_client = AsyncMock()
    mock_pool = MagicMock()

    with (
        patch("redis.asyncio.ConnectionPool", return_value=mock_pool),
        patch("redis.asyncio.Redis", return_value=mock_client),
    ):
        await redis_store.set("test_key", ["a", "b"])

        call_args = mock_client.set.call_args[0]
        assert call_args[1] == '["a", "b"]'


@pytest.mark.asyncio
async def test_redis_store_delete(redis_store: RedisStore) -> None:
    """Test delete operation."""
    mock_client = AsyncMock()
    mock_pool = MagicMock()

    with (
        patch("redis.asyncio.ConnectionPool", return_value=mock_pool),
        patch("redis.asyncio.Redis", return_value=mock_client),
    ):
        await redis_store.delete("test_key")

        mock_client.delete.assert_called_once_with("test_key")


@pytest.mark.asyncio
async def test_redis_store_exists_true(redis_store: RedisStore) -> None:
    """Test exists operation when key exists."""
    mock_client = AsyncMock()
    mock_client.exists.return_value = 1
    mock_pool = MagicMock()

    with (
        patch("redis.asyncio.ConnectionPool", return_value=mock_pool),
        patch("redis.asyncio.Redis", return_value=mock_client),
    ):
        result = await redis_store.exists("test_key")

        assert result is True


@pytest.mark.asyncio
async def test_redis_store_exists_false(redis_store: RedisStore) -> None:
    """Test exists operation when key doesn't exist."""
    mock_client = AsyncMock()
    mock_client.exists.return_value = 0
    mock_pool = MagicMock()

    with (
        patch("redis.asyncio.ConnectionPool", return_value=mock_pool),
        patch("redis.asyncio.Redis", return_value=mock_client),
    ):
        result = await redis_store.exists("test_key")

        assert result is False


@pytest.mark.asyncio
async def test_redis_store_clear(redis_store: RedisStore) -> None:
    """Test clear operation."""
    mock_client = AsyncMock()
    mock_pool = MagicMock()

    with (
        patch("redis.asyncio.ConnectionPool", return_value=mock_pool),
        patch("redis.asyncio.Redis", return_value=mock_client),
    ):
        await redis_store.clear()

        mock_client.flushdb.assert_called_once()


@pytest.mark.asyncio
async def test_redis_store_close(redis_store: RedisStore) -> None:
    """Test close operation."""
    mock_client = AsyncMock()
    mock_pool = AsyncMock()
    redis_store._client = mock_client
    redis_store._pool = mock_pool

    await redis_store.close()

    mock_client.close.assert_called_once()
    mock_pool.disconnect.assert_called_once()
    assert redis_store._client is None
    assert redis_store._pool is None


@pytest.mark.asyncio
async def test_redis_store_connection_failure(redis_store: RedisStore) -> None:
    """Test connection failure raises ExternalServiceError."""
    with (
        patch("redis.asyncio.ConnectionPool", side_effect=Exception("Connection failed")),
        pytest.raises(ExternalServiceError, match="Redis connection failed"),
    ):
        await redis_store.get("test_key")


@pytest.mark.asyncio
async def test_redis_store_get_failure(redis_store: RedisStore) -> None:
    """Test get operation failure raises ExternalServiceError."""
    mock_client = AsyncMock()
    mock_client.get.side_effect = Exception("Redis error")
    mock_pool = MagicMock()

    with (
        patch("redis.asyncio.ConnectionPool", return_value=mock_pool),
        patch("redis.asyncio.Redis", return_value=mock_client),
        pytest.raises(ExternalServiceError, match="Redis get failed"),
    ):
        await redis_store.get("test_key")


@pytest.mark.asyncio
async def test_redis_store_set_failure(redis_store: RedisStore) -> None:
    """Test set operation failure raises ExternalServiceError."""
    mock_client = AsyncMock()
    mock_client.set.side_effect = Exception("Redis error")
    mock_pool = MagicMock()

    with (
        patch("redis.asyncio.ConnectionPool", return_value=mock_pool),
        patch("redis.asyncio.Redis", return_value=mock_client),
        pytest.raises(ExternalServiceError, match="Redis set failed"),
    ):
        await redis_store.set("test_key", "value")


@pytest.mark.asyncio
async def test_redis_store_delete_failure(redis_store: RedisStore) -> None:
    """Test delete operation failure raises ExternalServiceError."""
    mock_client = AsyncMock()
    mock_client.delete.side_effect = Exception("Redis error")
    mock_pool = MagicMock()

    with (
        patch("redis.asyncio.ConnectionPool", return_value=mock_pool),
        patch("redis.asyncio.Redis", return_value=mock_client),
        pytest.raises(ExternalServiceError, match="Redis delete failed"),
    ):
        await redis_store.delete("test_key")


@pytest.mark.asyncio
async def test_redis_store_exists_failure(redis_store: RedisStore) -> None:
    """Test exists operation failure raises ExternalServiceError."""
    mock_client = AsyncMock()
    mock_client.exists.side_effect = Exception("Redis error")
    mock_pool = MagicMock()

    with (
        patch("redis.asyncio.ConnectionPool", return_value=mock_pool),
        patch("redis.asyncio.Redis", return_value=mock_client),
        pytest.raises(ExternalServiceError, match="Redis exists check failed"),
    ):
        await redis_store.exists("test_key")


@pytest.mark.asyncio
async def test_redis_store_clear_failure(redis_store: RedisStore) -> None:
    """Test clear operation failure raises ExternalServiceError."""
    mock_client = AsyncMock()
    mock_client.flushdb.side_effect = Exception("Redis error")
    mock_pool = MagicMock()

    with (
        patch("redis.asyncio.ConnectionPool", return_value=mock_pool),
        patch("redis.asyncio.Redis", return_value=mock_client),
        pytest.raises(ExternalServiceError, match="Redis clear failed"),
    ):
        await redis_store.clear()


@pytest.mark.asyncio
async def test_redis_store_reuse_connection(redis_store: RedisStore) -> None:
    """Test that connection pool is reused after first connection."""
    mock_client = AsyncMock()
    mock_client.get.return_value = "value"
    mock_pool = MagicMock()

    with (
        patch("redis.asyncio.ConnectionPool", return_value=mock_pool) as mock_pool_cls,
        patch("redis.asyncio.Redis", return_value=mock_client) as mock_redis_cls,
    ):
        await redis_store.get("key1")
        await redis_store.get("key2")

        # Should only create pool and client once
        mock_pool_cls.assert_called_once()
        mock_redis_cls.assert_called_once()
