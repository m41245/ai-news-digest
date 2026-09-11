"""
Regression tests for shared database URL normalization.

These tests cover the behaviour of
``ai_news_digest.infrastructure.database.url`` independently of Pydantic
settings so that the helper logic is directly verifiable.
"""

from __future__ import annotations

from ai_news_digest.infrastructure.database.url import (
    get_asyncpg_connect_args,
    get_asyncpg_engine_kwargs,
    normalize_database_url,
)


class TestNormalizeDatabaseUrl:
    """Tests for the shared PostgreSQL URL normalization helper."""

    def test_bare_postgresql_url_is_normalized(self) -> None:
        assert normalize_database_url(
            "postgresql://user:pass@host:5432/dbname"
        ) == "postgresql+asyncpg://user:pass@host:5432/dbname"

    def test_asyncpg_url_is_preserved(self) -> None:
        assert normalize_database_url(
            "postgresql+asyncpg://user:pass@host:5432/dbname"
        ) == "postgresql+asyncpg://user:pass@host:5432/dbname"

    def test_sslmode_require_is_stripped_and_dialect_normalized(self) -> None:
        result = normalize_database_url(
            "postgresql://user:pass@host:5432/dbname?sslmode=require"
        )
        assert result == "postgresql+asyncpg://user:pass@host:5432/dbname"
        assert "sslmode" not in result

    def test_sslmode_require_on_asyncpg_url_is_stripped(self) -> None:
        result = normalize_database_url(
            "postgresql+asyncpg://user:pass@host:5432/dbname?sslmode=require"
        )
        assert result == "postgresql+asyncpg://user:pass@host:5432/dbname"
        assert "sslmode" not in result

    def test_other_query_params_are_preserved(self) -> None:
        result = normalize_database_url(
            "postgresql://user:pass@host:5432/dbname?sslmode=require&application_name=myapp"
        )
        assert result == "postgresql+asyncpg://user:pass@host:5432/dbname?application_name=myapp"
        assert "sslmode" not in result
        assert "application_name=myapp" in result

    def test_non_postgresql_url_unchanged(self) -> None:
        assert normalize_database_url("sqlite:///test.db") == "sqlite:///test.db"

    def test_sqlite_with_query_unchanged(self) -> None:
        assert (
            normalize_database_url("sqlite:///test.db?mode=memory")
            == "sqlite:///test.db?mode=memory"
        )

    def test_password_with_special_chars_preserved(self) -> None:
        result = normalize_database_url(
            "postgresql://user:p%40ssw0rd@host:5432/dbname?sslmode=require"
        )
        assert result == "postgresql+asyncpg://user:p%40ssw0rd@host:5432/dbname"

    def test_no_password_preserved(self) -> None:
        assert (
            normalize_database_url("postgresql://host:5432/dbname?sslmode=require")
            == "postgresql+asyncpg://host:5432/dbname"
        )


class TestGetAsyncpgConnectArgs:
    """Tests for the asyncpg connect_args helper."""

    def test_sslmode_require_enables_tls(self) -> None:
        args = get_asyncpg_connect_args(
            "postgresql+asyncpg://user:pass@host:5432/dbname?sslmode=require"
        )
        assert args == {"ssl": True}

    def test_sslmode_verify_ca_enables_tls(self) -> None:
        args = get_asyncpg_connect_args(
            "postgresql+asyncpg://user:pass@host:5432/dbname?sslmode=verify-ca"
        )
        assert args == {"ssl": True}

    def test_sslmode_verify_full_enables_tls(self) -> None:
        args = get_asyncpg_connect_args(
            "postgresql+asyncpg://user:pass@host:5432/dbname?sslmode=verify-full"
        )
        assert args == {"ssl": True}

    def test_no_sslmode_returns_empty(self) -> None:
        args = get_asyncpg_connect_args(
            "postgresql+asyncpg://user:pass@host:5432/dbname"
        )
        assert args == {}

    def test_plain_postgresql_url_returns_empty(self) -> None:
        args = get_asyncpg_connect_args("postgresql://user:pass@host:5432/dbname")
        assert args == {}

    def test_sqlite_url_returns_empty(self) -> None:
        args = get_asyncpg_connect_args("sqlite:///test.db")
        assert args == {}

    def test_sslmode_disable_returns_empty(self) -> None:
        args = get_asyncpg_connect_args(
            "postgresql+asyncpg://user:pass@host:5432/dbname?sslmode=disable"
        )
        assert args == {}


class TestGetAsyncpgEngineKwargs:
    """Integration tests for the combined engine kwargs helper."""

    def test_neon_url_returns_normalized_url_and_ssl_args(self) -> None:
        normalized, connect_args = get_asyncpg_engine_kwargs(
            "postgresql://user:pass@host:5432/dbname?sslmode=require"
        )
        assert normalized == "postgresql+asyncpg://user:pass@host:5432/dbname"
        assert "sslmode" not in normalized
        assert connect_args == {"ssl": True}

    def test_local_postgresql_without_ssl(self) -> None:
        normalized, connect_args = get_asyncpg_engine_kwargs(
            "postgresql://user:pass@localhost:5432/dbname"
        )
        assert normalized == "postgresql+asyncpg://user:pass@localhost:5432/dbname"
        assert connect_args == {}

    def test_already_asyncpg_url_with_ssl(self) -> None:
        normalized, connect_args = get_asyncpg_engine_kwargs(
            "postgresql+asyncpg://user:pass@host:5432/dbname?sslmode=require"
        )
        assert normalized == "postgresql+asyncpg://user:pass@host:5432/dbname"
        assert "sslmode" not in normalized
        assert connect_args == {"ssl": True}

    def test_sqlite_url_unchanged(self) -> None:
        normalized, connect_args = get_asyncpg_engine_kwargs("sqlite:///test.db")
        assert normalized == "sqlite:///test.db"
        assert connect_args == {}
