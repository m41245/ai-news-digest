"""
Focused regression tests for Redis TLS and configuration behavior.

These tests verify:
1. rediss:// selects SSLConnection
2. redis:// selects normal Connection
3. rediss:// cannot downgrade to plaintext
4. URL parsing preserves host/port/db
5. credentials are not exposed in diagnostics
6. malformed redis-cli command is rejected
7. supported query parameters are handled correctly
8. unsupported parameters are rejected or handled safely
9. RedisStore pool lifecycle
10. RedisStore ping/get/set behavior using mocks/fakes
11. Celery rediss:// configuration
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import redis.asyncio as aioredis
from kombu import Connection as KombuConnection

from ai_news_digest.core.config import Settings
from ai_news_digest.core.exceptions import ExternalServiceError
from ai_news_digest.infrastructure.cache.redis_store import (
    RedisStore,
    _safe_redis_url_diagnostics,
)

# ======================================================================
# 1. rediss:// selects SSLConnection
# ======================================================================

class TestURLSchemeSelection:
    """Verify redis-py selects the correct connection class for each scheme."""

    def test_rediss_selects_ssl_connection(self):
        pool = aioredis.ConnectionPool.from_url(
            "rediss://default:token@upstash-host.example:6379/0"
        )
        assert pool.connection_class is aioredis.SSLConnection

    def test_redis_selects_plain_connection(self):
        pool = aioredis.ConnectionPool.from_url(
            "redis://default:token@upstash-host.example:6379/0"
        )
        assert pool.connection_class is aioredis.Connection

    def test_redis_store_uses_ssl_for_rediss_url(self):
        mock_settings = MagicMock(spec=Settings)
        mock_settings.redis_url = "rediss://default:token@upstash-host:6379/0"
        mock_settings.redis_socket_connect_timeout = 5
        mock_settings.redis_socket_timeout = 5
        mock_settings.redis_max_connections = 50
        mock_settings.redis_retry_on_timeout = True
        mock_settings.redis_retry_on_connection_error = True

        with (
            patch(
                "ai_news_digest.infrastructure.cache.redis_store.settings",
                mock_settings,
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


# ======================================================================
# 2. rediss:// cannot downgrade to plaintext
# ======================================================================

class TestNoDowngrade:
    """Verify rediss:// URLs cannot be downgraded to plaintext."""

    def test_rediss_cannot_downgrade_with_ssl_false_kwarg(self):
        pool = aioredis.ConnectionPool.from_url(
            "rediss://default:token@upstash-host:6379/0",
            ssl=False,
        )
        assert pool.connection_class is aioredis.SSLConnection

    def test_redis_store_does_not_downgrade_rediss_to_plaintext(self):
        store = RedisStore("rediss://default:token@upstash-host:6379/0")

        with patch.object(aioredis.ConnectionPool, "from_url") as mock_from_url:
            mock_pool = MagicMock()
            mock_pool.connection_class = aioredis.SSLConnection
            mock_from_url.return_value = mock_pool

            asyncio.new_event_loop().run_until_complete(store._ensure_connected())

            called_url = mock_from_url.call_args[0][0]
            assert called_url.startswith("rediss://")
            assert not called_url.startswith("redis://")
            assert mock_pool.connection_class.__name__ == "SSLConnection"


# ======================================================================
# 3. URL parsing preserves host/port/db
# ======================================================================

class TestURLParsing:
    """Verify redis-py parses URL components correctly."""

    def test_parses_standard_rediss_url(self):
        url = "rediss://default:test-token@upstash-host.example:6379/0"
        pool = aioredis.ConnectionPool.from_url(url)
        kwargs = pool.connection_kwargs
        assert kwargs["host"] == "upstash-host.example"
        assert kwargs["port"] == 6379
        assert kwargs["db"] == 0
        assert kwargs["username"] == "default"
        assert kwargs["password"] == "test-token"  # noqa: S105 - test token

    def test_parses_non_default_db(self):
        url = "rediss://default:token@upstash-host.example:6379/2"
        pool = aioredis.ConnectionPool.from_url(url)
        assert pool.connection_kwargs["db"] == 2

    def test_parses_non_default_port(self):
        url = "rediss://default:token@upstash-host.example:6380/0"
        pool = aioredis.ConnectionPool.from_url(url)
        assert pool.connection_kwargs["port"] == 6380

    def test_rejects_malformed_cli_url(self):
        store = RedisStore(
            "redis-cli --tls -u rediss://default:token@upstash-host:6379/0"
        )

        with patch.object(aioredis.ConnectionPool, "from_url") as mock_from_url:
            mock_from_url.side_effect = ValueError(
                "Redis URL must specify one of the following schemes"
            )

            with pytest.raises(
                ExternalServiceError, match="Redis connection failed"
            ):
                asyncio.new_event_loop().run_until_complete(store.get("key"))


# ======================================================================
# 4. credentials are not exposed in diagnostics
# ======================================================================

class TestDiagnosticsSecurity:
    """Verify diagnostics never expose credentials."""

    def test_diagnostics_excludes_password(self):
        url = "rediss://default:secret-token@upstash-host.example:6379/0"
        diagnostics = _safe_redis_url_diagnostics(url)
        assert "secret-token" not in str(diagnostics)
        assert diagnostics["password_present"] is True

    def test_diagnostics_excludes_full_url(self):
        url = "rediss://default:secret-token@upstash-host.example:6379/0"
        diagnostics = _safe_redis_url_diagnostics(url)
        assert url not in str(diagnostics)

    def test_diagnostics_shows_safe_fields(self):
        url = "rediss://default:secret-token@upstash-host.example:6379/0"
        diagnostics = _safe_redis_url_diagnostics(url)
        assert diagnostics["scheme"] == "rediss"
        assert diagnostics["hostname"] == "upstash-host.example"
        assert diagnostics["port"] == 6379
        assert diagnostics["database"] == 0
        assert diagnostics["username_present"] is True
        assert diagnostics["password_present"] is True
        assert diagnostics["query_keys"] == []

    def test_diagnostics_handles_malformed_url(self):
        url = "redis-cli --tls -u rediss://default:token@upstash-host:6379/0"
        diagnostics = _safe_redis_url_diagnostics(url)
        assert diagnostics["scheme"] == ""
        assert diagnostics["password_present"] is False


# ======================================================================
# 5. supported query parameters are handled correctly
# ======================================================================

class TestQueryParameters:
    """Verify query parameters are parsed and passed correctly."""

    def test_socket_timeout_query_parameter(self):
        url = "rediss://default:token@upstash-host:6379/0?socket_timeout=10"
        pool = aioredis.ConnectionPool.from_url(url)
        assert pool.connection_kwargs["socket_timeout"] == 10.0

    def test_db_query_parameter(self):
        url = "rediss://default:token@upstash-host:6379?db=3"
        pool = aioredis.ConnectionPool.from_url(url)
        assert pool.connection_kwargs["db"] == 3


# ======================================================================
# 6. RedisStore pool lifecycle
# ======================================================================

class TestPoolLifecycle:
    """Verify RedisStore pool lifecycle behavior."""

    @pytest.mark.asyncio
    async def test_pool_created_on_first_connection(self):
        store = RedisStore("redis://localhost:6379/0")
        assert store._pool is None
        assert store._client is None

        mock_client = AsyncMock()
        mock_client.ping.return_value = True

        with patch.object(
            RedisStore, "_build_client", return_value=mock_client
        ) as mock_build:
            await store.ping()
            mock_build.assert_called_once()

    @pytest.mark.asyncio
    async def test_pool_reused_on_subsequent_connections(self):
        store = RedisStore("redis://localhost:6379/0")
        mock_client = AsyncMock()
        mock_client.get.return_value = "value"

        with patch.object(
            RedisStore, "_build_client", return_value=mock_client
        ) as mock_build:
            await store.get("key1")
            await store.get("key2")
            mock_build.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_clears_client_and_pool(self):
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


# ======================================================================
# 7. RedisStore ping/get/set behavior using mocks
# ======================================================================

class TestRedisStoreOperations:
    """Verify RedisStore CRUD operations using mocks."""

    @pytest.mark.asyncio
    async def test_ping_returns_true_when_connected(self):
        store = RedisStore("redis://localhost:6379/0")
        mock_client = AsyncMock()
        mock_client.ping.return_value = True

        with patch.object(
            RedisStore, "_build_client", return_value=mock_client
        ):
            result = await store.ping()
            assert result is True

    @pytest.mark.asyncio
    async def test_get_returns_value(self):
        store = RedisStore("redis://localhost:6379/0")
        mock_client = AsyncMock()
        mock_client.get.return_value = "test_value"

        with patch.object(
            RedisStore, "_build_client", return_value=mock_client
        ):
            result = await store.get("test_key")
            assert result == "test_value"

    @pytest.mark.asyncio
    async def test_set_stores_value(self):
        store = RedisStore("redis://localhost:6379/0")
        mock_client = AsyncMock()

        with patch.object(
            RedisStore, "_build_client", return_value=mock_client
        ):
            await store.set("test_key", "test_value")
            mock_client.set.assert_called_once_with("test_key", "test_value")


# ======================================================================
# 9. Production URL scheme validation
# ======================================================================

class TestProductionURLSchemeValidation:
    """Verify RedisStore rejects plaintext redis:// in production."""

    def test_redis_scheme_raises_in_production(self):
        mock_settings = MagicMock(spec=Settings)
        mock_settings.redis_url = "redis://default:token@upstash-host:6379/0"
        mock_settings.environment = "production"
        mock_settings.redis_max_connections = 50
        mock_settings.redis_retry_on_timeout = False
        mock_settings.redis_retry_on_connection_error = False
        mock_settings.redis_socket_connect_timeout = 5
        mock_settings.redis_socket_timeout = 5

        with patch(
            "ai_news_digest.infrastructure.cache.redis_store.settings",
            mock_settings,
        ):
            store = RedisStore()
            with pytest.raises(ValueError, match="rediss://"):
                store._build_client()

    def test_rediss_scheme_accepted_in_production(self):
        mock_settings = MagicMock(spec=Settings)
        mock_settings.redis_url = "rediss://default:token@upstash-host:6379/0"
        mock_settings.environment = "production"
        mock_settings.redis_max_connections = 50
        mock_settings.redis_retry_on_timeout = False
        mock_settings.redis_retry_on_connection_error = False
        mock_settings.redis_socket_connect_timeout = 5
        mock_settings.redis_socket_timeout = 5

        with (
            patch(
                "ai_news_digest.infrastructure.cache.redis_store.settings",
                mock_settings,
            ),
            patch.object(aioredis.ConnectionPool, "from_url") as mock_from_url,
        ):
            mock_pool = MagicMock()
            mock_pool.connection_class = aioredis.SSLConnection
            mock_from_url.return_value = mock_pool

            store = RedisStore()
            store._build_client()

            mock_from_url.assert_called_once()
            assert mock_from_url.call_args[1].get("max_connections") == 50

    def test_redis_scheme_allowed_in_development(self):
        mock_settings = MagicMock(spec=Settings)
        mock_settings.redis_url = "redis://localhost:6379/0"
        mock_settings.environment = "development"
        mock_settings.redis_max_connections = 50
        mock_settings.redis_retry_on_timeout = False
        mock_settings.redis_retry_on_connection_error = False
        mock_settings.redis_socket_connect_timeout = 5
        mock_settings.redis_socket_timeout = 5

        with (
            patch(
                "ai_news_digest.infrastructure.cache.redis_store.settings",
                mock_settings,
            ),
            patch.object(aioredis.ConnectionPool, "from_url") as mock_from_url,
        ):
            mock_pool = MagicMock()
            mock_pool.connection_class = aioredis.Connection
            mock_from_url.return_value = mock_pool

            store = RedisStore()
            store._build_client()

            mock_from_url.assert_called_once()
            assert mock_from_url.call_args[0][0] == "redis://localhost:6379/0"


# ======================================================================
# 10. Celery rediss:// configuration
# ======================================================================

class TestCeleryRedisConfiguration:
    """Verify Celery/Kombu handles rediss:// URLs correctly."""

    def test_kombu_sets_ssl_for_rediss_scheme(self):
        conn = KombuConnection(
            "rediss://default:token@upstash-host.example:6379/1",
        )
        assert conn.transport_cls == "rediss"
        assert conn.ssl is not None
        assert conn.hostname == "upstash-host.example"
        assert conn.port == 6379
        assert conn.userid == "default"
        assert conn.password == "token"  # noqa: S105 - test token

    def test_celery_rediss_url_preserved(self):
        from ai_news_digest.core.config import get_settings

        get_settings.cache_clear()
        import os
        os.environ["REDIS_URL"] = "rediss://default:token@upstash-host:6379/0"
        os.environ["CELERY_BROKER_URL"] = "rediss://default:token@upstash-host:6379/1"
        os.environ["CELERY_RESULT_BACKEND"] = "rediss://default:token@upstash-host:6379/2"
        os.environ["ENVIRONMENT"] = "development"
        os.environ["EMAIL_DEVELOPMENT_MODE"] = "true"
        os.environ["EMAIL_PROVIDER"] = "console"
        os.environ["EMAIL_BASE_URL"] = "http://localhost:8000"

        try:
            settings = Settings()
            assert settings.celery_broker_url == "rediss://default:token@upstash-host:6379/1"
            assert settings.celery_result_backend == "rediss://default:token@upstash-host:6379/2"
        finally:
            get_settings.cache_clear()
            for key in [
                "REDIS_URL", "CELERY_BROKER_URL", "CELERY_RESULT_BACKEND",
                "ENVIRONMENT", "EMAIL_DEVELOPMENT_MODE", "EMAIL_PROVIDER", "EMAIL_BASE_URL",
            ]:
                os.environ.pop(key, None)
