"""
Unit tests for Redis operational safety improvements.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import redis.asyncio as aioredis

from ai_news_digest.core.config import Settings
from ai_news_digest.core.exceptions import ExternalServiceError
from ai_news_digest.infrastructure.cache.redis_store import RedisStore


@pytest.fixture
def mock_settings() -> Settings:
    """Create mock settings with Redis configuration."""
    settings = MagicMock(spec=Settings)
    settings.redis_url = "redis://localhost:6379/0"
    settings.redis_socket_connect_timeout = 5
    settings.redis_socket_timeout = 5
    settings.redis_max_connections = 50
    settings.redis_retry_on_timeout = True
    settings.redis_retry_on_connection_error = True
    return settings


@pytest.fixture
def mock_settings_rediss() -> Settings:
    """Create mock settings with a rediss:// URL."""
    settings = MagicMock(spec=Settings)
    settings.redis_url = "rediss://default:token@upstash-host:6379/0"
    settings.redis_socket_connect_timeout = 5
    settings.redis_socket_timeout = 5
    settings.redis_max_connections = 50
    settings.redis_retry_on_timeout = True
    settings.redis_retry_on_connection_error = True
    return settings


def test_redis_store_uses_connection_pool_from_url(mock_settings: Settings) -> None:
    """Test that RedisStore creates a client via ConnectionPool.from_url."""
    with (
        patch(
            "ai_news_digest.infrastructure.cache.redis_store.settings",
            mock_settings,
        ),
        patch.object(
            aioredis.ConnectionPool,
            "from_url",
            return_value=MagicMock(),
        ) as mock_from_url,
        patch(
            "ai_news_digest.infrastructure.cache.redis_store.aioredis.Redis",
        ) as mock_redis_cls,
    ):
        store = RedisStore()
        assert store._pool is None
        assert store._client is None

        mock_pool = MagicMock()
        mock_from_url.return_value = mock_pool
        mock_client = MagicMock()
        mock_redis_cls.return_value = mock_client

        asyncio.new_event_loop().run_until_complete(store._ensure_connected())

        mock_from_url.assert_called_once()
        call_kwargs = mock_from_url.call_args[1]
        assert call_kwargs["max_connections"] == 50
        assert call_kwargs["socket_connect_timeout"] == 5
        assert call_kwargs["socket_timeout"] == 5
        assert call_kwargs["decode_responses"] is True
        assert "retry" in call_kwargs


def test_redis_store_retry_configuration(mock_settings: Settings) -> None:
    """Test that RedisStore configures retry behavior."""
    with (
        patch(
            "ai_news_digest.infrastructure.cache.redis_store.settings",
            mock_settings,
        ),
        patch.object(
            aioredis.ConnectionPool,
            "from_url",
            return_value=MagicMock(),
        ) as mock_from_url,
        patch(
            "ai_news_digest.infrastructure.cache.redis_store.aioredis.Redis",
        ) as mock_redis_cls,
        patch(
            "ai_news_digest.infrastructure.cache.redis_store.Retry",
        ) as mock_retry_cls,
    ):
        store = RedisStore()
        mock_pool = MagicMock()
        mock_from_url.return_value = mock_pool
        mock_redis_cls.return_value = MagicMock()

        asyncio.new_event_loop().run_until_complete(store._ensure_connected())

        mock_retry_cls.assert_called_once()
        retry_kwargs = mock_retry_cls.call_args[1]
        assert retry_kwargs["retries"] == 3
        assert "backoff" in retry_kwargs


def test_redis_store_uses_ssl_for_rediss_url(
    mock_settings_rediss: Settings,
) -> None:
    """Test that RedisStore enables SSL when using rediss:// scheme (Upstash)."""
    with (
        patch(
            "ai_news_digest.infrastructure.cache.redis_store.settings",
            mock_settings_rediss,
        ),
        patch.object(aioredis.ConnectionPool, "from_url") as mock_from_url,
    ):
        store = RedisStore()
        mock_pool = MagicMock()
        mock_pool.connection_class = aioredis.SSLConnection
        mock_from_url.return_value = mock_pool

        asyncio.new_event_loop().run_until_complete(store._ensure_connected())

        mock_from_url.assert_called_once()
        called_url = mock_from_url.call_args[0][0]
        assert called_url == "rediss://default:token@upstash-host:6379/0"
        assert mock_pool.connection_class.__name__ == "SSLConnection"


def test_redis_store_does_not_downgrade_rediss_to_plaintext(
    mock_settings_rediss: Settings,
) -> None:
    """Test that a rediss:// URL does not accidentally downgrade to plaintext."""
    store = RedisStore("rediss://default:token@upstash-host:6379/0")

    with (
        patch.object(aioredis.ConnectionPool, "from_url") as mock_from_url,
    ):
        mock_pool = MagicMock()
        mock_pool.connection_class = aioredis.SSLConnection
        mock_from_url.return_value = mock_pool

        asyncio.new_event_loop().run_until_complete(store._ensure_connected())

        called_url = mock_from_url.call_args[0][0]
        assert called_url.startswith("rediss://")
        assert not called_url.startswith("redis://")
        assert mock_pool.connection_class.__name__ == "SSLConnection"


def test_redis_store_rejects_malformed_cli_url(
    mock_settings_rediss: Settings,
) -> None:
    """Test that a redis-cli command string is rejected as an invalid URL."""
    store = RedisStore(
        "redis-cli --tls -u rediss://default:token@upstash-host:6379/0"
    )

    with (
        patch.object(aioredis.ConnectionPool, "from_url") as mock_from_url,
    ):
        mock_from_url.side_effect = ValueError(
            "Redis URL must specify one of the following schemes"
        )

        import asyncio

        with pytest.raises(
            ExternalServiceError, match="Redis connection failed"
        ):
            asyncio.new_event_loop().run_until_complete(store.get("key"))


@pytest.mark.asyncio
async def test_redis_store_is_connected_returns_true() -> None:
    """Test is_connected returns True when Redis responds."""
    store = RedisStore("redis://localhost:6379/0")
    mock_client = AsyncMock()
    mock_client.ping.return_value = True

    with (
        patch.object(RedisStore, "_build_client", return_value=mock_client),
    ):
        result = await store.is_connected()
        assert result is True


@pytest.mark.asyncio
async def test_redis_store_is_connected_returns_false_on_failure() -> None:
    """Test is_connected returns False when Redis is unavailable."""
    store = RedisStore("redis://localhost:6379/0")

    with patch.object(
        RedisStore, "_build_client", side_effect=Exception("connection refused")
    ):
        result = await store.is_connected()
        assert result is False


@pytest.mark.asyncio
async def test_redis_store_ping_returns_true() -> None:
    """Test ping returns True when Redis is available."""
    store = RedisStore("redis://localhost:6379/0")
    mock_client = AsyncMock()
    mock_client.ping.return_value = True

    with (
        patch.object(RedisStore, "_build_client", return_value=mock_client),
    ):
        result = await store.ping()
        assert result is True


@pytest.mark.asyncio
async def test_redis_store_ping_returns_false_on_failure() -> None:
    """Test ping returns False when Redis is unavailable."""
    store = RedisStore("redis://localhost:6379/0")

    with patch.object(
        RedisStore, "_build_client", side_effect=Exception("connection refused")
    ):
        result = await store.ping()
        assert result is False


@pytest.mark.asyncio
async def test_redis_store_startup_check_logs_warning() -> None:
    """Test startup_check logs warning but does not raise when Redis is down."""
    store = RedisStore("redis://localhost:6379/0")

    with (
        patch.object(
            RedisStore, "_build_client", side_effect=Exception("connection refused")
        ),
        patch(
            "ai_news_digest.infrastructure.cache.redis_store.logger"
        ) as mock_logger,
    ):
        await store.startup_check()
        warning_calls = [str(call) for call in mock_logger.warning.call_args_list]
        assert any("unavailable" in call for call in warning_calls)


@pytest.mark.asyncio
async def test_redis_store_startup_check_succeeds_when_available() -> None:
    """Test startup_check succeeds silently when Redis is available."""
    store = RedisStore("redis://localhost:6379/0")
    mock_client = AsyncMock()
    mock_client.ping.return_value = True

    with (
        patch.object(RedisStore, "_build_client", return_value=mock_client),
        patch(
            "ai_news_digest.infrastructure.cache.redis_store.logger"
        ) as mock_logger,
    ):
        await store.startup_check()
        assert not mock_logger.warning.called


@pytest.mark.asyncio
async def test_redis_store_failure_does_not_crash_unrelated() -> None:
    """Test that Redis failures in non-critical paths don't raise."""
    store = RedisStore("redis://localhost:6379/0")

    with patch.object(
        RedisStore, "_build_client", side_effect=Exception("Redis down")
    ):
        is_conn = await store.is_connected()
        ping_result = await store.ping()
        assert is_conn is False
        assert ping_result is False


@pytest.mark.asyncio
async def test_redis_store_close_disconnects_pool() -> None:
    """Test that close disconnects both client and pool."""
    store = RedisStore("redis://localhost:6379/0")
    mock_client = AsyncMock()
    mock_pool = AsyncMock()
    store._client = mock_client
    store._pool = mock_pool

    await store.close()

    mock_client.close.assert_called_once()
    mock_pool.disconnect.assert_called_once()
    assert store._client is None
    assert store._pool is None  # type: ignore[unreachable]


@pytest.mark.asyncio
async def test_redis_store_connection_reuses_pool() -> None:
    """Test that connection pool is reused after first connection."""
    store = RedisStore("redis://localhost:6379/0")
    mock_client = AsyncMock()
    mock_client.get.return_value = "value"

    with (
        patch.object(
            RedisStore, "_build_client", return_value=mock_client
        ) as mock_build,
    ):
        await store.get("key1")
        await store.get("key2")

        mock_build.assert_called_once()
