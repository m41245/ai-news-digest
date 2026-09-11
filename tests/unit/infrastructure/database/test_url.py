"""Regression tests for PostgreSQL/libpq URL handling with asyncpg."""

from __future__ import annotations

import inspect

import asyncpg
import pytest
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from ai_news_digest.infrastructure.database.url import (
    get_asyncpg_connect_args,
    get_asyncpg_engine_kwargs,
    normalize_database_url,
)

NEON_URL = (
    "postgresql://user:pass@ep-example.us-east-2.aws.neon.tech:5432/news"
    "?sslmode=require&channel_binding=require&application_name=news-api"
    "&target_session_attrs=any"
)


class TestNormalizeDatabaseUrl:
    def test_bare_postgresql_url_is_normalized(self) -> None:
        assert (
            normalize_database_url("postgresql://user:pass@host:5432/dbname")
            == "postgresql+asyncpg://user:pass@host:5432/dbname"
        )

    def test_asyncpg_url_is_preserved(self) -> None:
        assert (
            normalize_database_url("postgresql+asyncpg://user:pass@host:5432/dbname")
            == "postgresql+asyncpg://user:pass@host:5432/dbname"
        )

    def test_neon_libpq_parameters_are_not_left_in_asyncpg_url(self) -> None:
        result = normalize_database_url(NEON_URL)

        assert result.startswith("postgresql+asyncpg://")
        assert "sslmode" not in result
        assert "channel_binding" not in result
        assert "application_name" not in result
        assert "target_session_attrs=any" in result

    def test_supported_asyncpg_query_parameters_are_preserved(self) -> None:
        result = normalize_database_url(
            "postgresql://user:pass@host:5432/dbname"
            "?target_session_attrs=primary&statement_cache_size=0"
        )

        assert "target_session_attrs=primary" in result
        assert "statement_cache_size=0" in result

    def test_unsupported_query_parameters_are_consumed(self) -> None:
        result = normalize_database_url(
            "postgresql://user:pass@host:5432/dbname?channel_binding=require"
            "&unsupported_libpq_option=value"
        )

        assert "channel_binding" not in result
        assert "unsupported_libpq_option" not in result

    def test_non_postgresql_urls_are_unchanged(self) -> None:
        assert normalize_database_url("sqlite:///test.db?mode=memory") == (
            "sqlite:///test.db?mode=memory"
        )

    def test_password_with_special_chars_is_preserved(self) -> None:
        result = normalize_database_url(
            "postgresql://user:p%40ssw0rd@host:5432/dbname?sslmode=require"
        )

        assert result == "postgresql+asyncpg://user:p%40ssw0rd@host:5432/dbname"

    @pytest.mark.parametrize(
        "parameter",
        [
            "sslcert",
            "sslcrl",
            "sslkey",
            "sslrootcert",
            "ssl_min_protocol_version",
        ],
    )
    def test_unsupported_tls_file_parameters_fail_closed(self, parameter: str) -> None:
        with pytest.raises(ValueError, match="unsupported asyncpg TLS parameter"):
            normalize_database_url(f"postgresql://user:pass@host:5432/dbname?{parameter}=value")


class TestGetAsyncpgConnectArgs:
    @pytest.mark.parametrize("sslmode", ["require", "verify-ca", "verify-full"])
    def test_secure_sslmodes_enable_verified_tls(self, sslmode: str) -> None:
        args = get_asyncpg_connect_args(
            f"postgresql://user:pass@host:5432/dbname?sslmode={sslmode}"
        )

        assert args == {"ssl": True}

    def test_sslmode_disable_explicitly_disables_tls(self) -> None:
        assert get_asyncpg_connect_args(
            "postgresql+asyncpg://user:pass@host:5432/dbname?sslmode=disable"
        ) == {"ssl": False}

    @pytest.mark.parametrize("sslmode", ["allow", "prefer"])
    def test_optional_sslmodes_use_asyncpg_ssl_negotiation(self, sslmode: str) -> None:
        assert get_asyncpg_connect_args(
            f"postgresql+asyncpg://user:pass@host:5432/dbname?sslmode={sslmode}"
        ) == {"ssl": sslmode}

    def test_channel_binding_is_consumed_and_tls_is_retained(self) -> None:
        args = get_asyncpg_connect_args(
            "postgresql+asyncpg://user:pass@host:5432/dbname"
            "?sslmode=require&channel_binding=require"
        )

        assert args["ssl"] is True
        assert "channel_binding" not in args

    def test_channel_binding_require_forces_tls_when_sslmode_is_omitted(self) -> None:
        assert get_asyncpg_connect_args(
            "postgresql+asyncpg://user:pass@host:5432/dbname?channel_binding=require"
        ) == {"ssl": True}

    def test_channel_binding_require_cannot_disable_tls(self) -> None:
        with pytest.raises(ValueError, match="cannot be used with sslmode=disable"):
            get_asyncpg_connect_args(
                "postgresql+asyncpg://user:pass@host:5432/dbname"
                "?sslmode=disable&channel_binding=require"
            )

    def test_application_name_is_translated_to_server_settings(self) -> None:
        assert get_asyncpg_connect_args(
            "postgresql+asyncpg://user:pass@host:5432/dbname" "?application_name=news-api"
        ) == {"server_settings": {"application_name": "news-api"}}

    def test_non_postgresql_url_returns_empty_args(self) -> None:
        assert get_asyncpg_connect_args("sqlite:///test.db") == {}


class TestGetAsyncpgEngineKwargs:
    def test_neon_url_has_no_leaking_libpq_arguments(self) -> None:
        normalized, connect_args = get_asyncpg_engine_kwargs(NEON_URL)

        assert normalized.startswith("postgresql+asyncpg://")
        assert "sslmode" not in normalized
        assert "channel_binding" not in normalized
        assert connect_args["ssl"] is True
        assert connect_args["server_settings"] == {"application_name": "news-api"}

    def test_generated_engine_kwargs_cannot_pass_channel_binding_to_asyncpg(self) -> None:
        normalized, connect_args = get_asyncpg_engine_kwargs(
            "postgresql://user:pass@host:5432/dbname" "?sslmode=require&channel_binding=require"
        )
        engine = create_async_engine(normalized, connect_args=connect_args)
        try:
            _, dialect_kwargs = engine.sync_engine.dialect.create_connect_args(make_url(normalized))
        finally:
            engine.sync_engine.dispose()

        asyncpg_parameters = set(inspect.signature(asyncpg.connect).parameters)
        sqlalchemy_parameters = {
            "async_fallback",
            "prepared_statement_cache_size",
            "prepared_statement_name_func",
        }
        assert "sslmode" not in dialect_kwargs
        assert "channel_binding" not in dialect_kwargs
        assert set(dialect_kwargs) <= asyncpg_parameters | sqlalchemy_parameters

    def test_sqlite_url_is_unchanged_and_has_no_asyncpg_args(self) -> None:
        normalized, connect_args = get_asyncpg_engine_kwargs("sqlite:///test.db")

        assert normalized == "sqlite:///test.db"
        assert connect_args == {}
