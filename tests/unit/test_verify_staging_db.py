"""
Unit tests for the staging database verification script.

Validates URL parsing and validation (fail-closed for local/non-Neon/no-SSL),
migration-head discovery, query read-only safety, and the absence of
secret leakage in the connection metadata.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import ClassVar

import pytest
from scripts.verify_staging_db import (
    VERIFICATION_QUERIES,
    _primary_table_for,
    assert_queries_read_only,
    discover_migration_heads,
    parse_database_url,
    validate_connection_target,
)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_MIGRATIONS_DIR = _PROJECT_ROOT / "migrations" / "versions"


# ---------------------------------------------------------------------------
# parse_database_url
# ---------------------------------------------------------------------------


class TestParseDatabaseUrl:
    def test_parses_neon_url_without_exposing_password(self) -> None:
        url = (
            "postgresql://user:s3cr3t@ep-test.us-east-2.aws.neon.tech/"
            "ai_news_staging?sslmode=require"
        )
        parsed = parse_database_url(url)
        assert parsed.host == "ep-test.us-east-2.aws.neon.tech"
        assert parsed.port == 5432
        assert parsed.database == "ai_news_staging"
        assert parsed.scheme == "postgresql"
        # password must never appear in the parsed object
        assert not hasattr(parsed, "password") or parsed.__repr__().find("s3cr3t") == -1

    def test_parses_explicit_port(self) -> None:
        url = "postgresql://u:p@ep-x.eu-central-1.aws.neon.tech:5433/db?sslmode=require"
        parsed = parse_database_url(url)
        assert parsed.port == 5433

    def test_rejects_sqlite_scheme(self) -> None:
        with pytest.raises(ValueError, match="Unsupported URL scheme"):
            parse_database_url("sqlite:///db.sqlite")

    def test_rejects_empty_host(self) -> None:
        with pytest.raises(ValueError, match="does not specify a host"):
            parse_database_url("postgresql://user:pass@/db")

    def test_rejects_empty_database(self) -> None:
        with pytest.raises(ValueError, match="does not specify a database"):
            parse_database_url("postgresql://user:pass@host")

    def test_detects_localhost(self) -> None:
        parsed = parse_database_url("postgresql://u:p@localhost:5432/db?sslmode=require")
        assert parsed.is_local is True
        assert parsed.is_neon is False

    def test_detects_127_0_0_1(self) -> None:
        parsed = parse_database_url("postgresql://u:p@127.0.0.1:5432/db?sslmode=require")
        assert parsed.is_local is True

    def test_detects_neon_host(self) -> None:
        parsed = parse_database_url(
            "postgresql://u:p@ep-test.us-east-2.aws.neon.tech/db?sslmode=require"
        )
        assert parsed.is_neon is True
        assert parsed.is_local is False

    def test_detects_docker_bridge_as_local(self) -> None:
        parsed = parse_database_url("postgresql://u:p@host.docker.internal:5432/db?sslmode=require")
        assert parsed.is_local is True

    def test_non_local_non_neon_is_not_local(self) -> None:
        parsed = parse_database_url("postgresql://u:p@db.example.com/db?sslmode=require")
        assert parsed.is_local is False
        assert parsed.is_neon is False


# ---------------------------------------------------------------------------
# validate_connection_target
# ---------------------------------------------------------------------------


class TestValidateConnectionTarget:
    def test_accepts_valid_neon_url(self) -> None:
        url = (
            "postgresql://user:secret@ep-test.us-east-2.aws.neon.tech/"
            "ai_news_staging?sslmode=require"
        )
        info, connect_args = validate_connection_target(url)
        assert info.host == "ep-test.us-east-2.aws.neon.tech"
        assert info.database == "ai_news_staging"
        assert info.ssl_enabled is True
        assert connect_args.get("ssl") is True

    def test_accepts_neon_url_with_channel_binding(self) -> None:
        url = (
            "postgresql://user:secret@ep-calm-wind-12345.us-east-2.aws.neon.tech/"
            "db_staging?sslmode=require&channel_binding=require"
        )
        info, connect_args = validate_connection_target(url)
        assert info.host == "ep-calm-wind-12345.us-east-2.aws.neon.tech"
        assert connect_args.get("ssl") is True
        assert "sslmode" not in str(connect_args)

    def test_rejects_localhost(self) -> None:
        url = "postgresql://user:pass@localhost:5432/db?sslmode=require"
        with pytest.raises(ValueError, match="local"):
            validate_connection_target(url)

    def test_rejects_127_0_0_1(self) -> None:
        url = "postgresql://user:pass@127.0.0.1:5432/db?sslmode=require"
        with pytest.raises(ValueError, match="local"):
            validate_connection_target(url)

    def test_rejects_docker_internal(self) -> None:
        url = "postgresql://user:pass@host.docker.internal:5432/db?sslmode=require"
        with pytest.raises(ValueError, match="local"):
            validate_connection_target(url)

    def test_rejects_non_neon_host(self) -> None:
        url = "postgresql://user:pass@db.example.com/db?sslmode=require"
        with pytest.raises(ValueError, match="not a recognised Neon endpoint"):
            validate_connection_target(url)

    def test_rejects_non_tls(self) -> None:
        url = "postgresql://user:pass@ep-test.us-east-2.aws.neon.tech/db"
        with pytest.raises(ValueError, match="SSL/TLS"):
            validate_connection_target(url)

    def test_rejects_sslmode_disable(self) -> None:
        url = "postgresql://user:pass@ep-test.us-east-2.aws.neon.tech/db?sslmode=disable"
        with pytest.raises(ValueError, match="SSL/TLS"):
            validate_connection_target(url)

    def test_rejects_sqlite(self) -> None:
        with pytest.raises(ValueError, match="Unsupported URL scheme"):
            validate_connection_target("sqlite:///db.sqlite")

    def test_connection_info_describe_has_no_credentials(self) -> None:
        url = (
            "postgresql://user:s3cr3tpass@ep-test.us-east-2.aws.neon.tech/"
            "ai_news_staging?sslmode=require"
        )
        info, _ = validate_connection_target(url)
        description = info.describe()
        assert "s3cr3tpass" not in description
        assert "user" not in description
        assert "postgresql://" not in description
        assert ":s3cr3t" not in description


# ---------------------------------------------------------------------------
# discover_migration_heads
# ---------------------------------------------------------------------------


class TestDiscoverMigrationHeads:
    def test_returns_single_head_034(self) -> None:
        heads = discover_migration_heads(_MIGRATIONS_DIR)
        assert heads == ["034"]

    def test_no_empty_or_none_heads(self) -> None:
        heads = discover_migration_heads(_MIGRATIONS_DIR)
        assert all(h for h in heads)
        assert all(h != "None" for h in heads)


# ---------------------------------------------------------------------------
# Query safety
# ---------------------------------------------------------------------------


def _extract_query_names() -> list[str]:
    return [name for name, _ in VERIFICATION_QUERIES]


class TestVerificationQueries:
    def test_queries_are_read_only(self) -> None:
        assert_queries_read_only(VERIFICATION_QUERIES)

    def test_all_queries_start_with_select(self) -> None:
        for name, sql in VERIFICATION_QUERIES:
            assert (
                sql.strip().lower().startswith("select")
            ), f"Query '{name}' must start with SELECT"

    def test_queries_contain_no_write_keywords(self) -> None:
        write_keywords = re.compile(
            r"\b(insert|update|delete|create|drop|alter|truncate|grant|revoke|"
            r"vacuum|comment|begin|commit|rollback|savepoint)\b",
            re.IGNORECASE,
        )
        for name, sql in VERIFICATION_QUERIES:
            assert not write_keywords.search(sql), f"Query '{name}' contains a write keyword"

    EXPECTED_QUERIES: ClassVar[set[str]] = {
        "article_counts_by_status",
        "active_verified_sources",
        "extraction_breakdown",
        "eligible_for_categorization",
        "eligible_for_analysis",
    }

    def test_expected_query_set(self) -> None:
        names = set(_extract_query_names())
        assert names == self.EXPECTED_QUERIES

    def test_article_counts_by_status_groups_by_status(self) -> None:
        _, sql = next((n, s) for n, s in VERIFICATION_QUERIES if n == "article_counts_by_status")
        assert "GROUP BY status" in sql

    def test_extraction_breakdown_includes_content_count(self) -> None:
        _, sql = next((n, s) for n, s in VERIFICATION_QUERIES if n == "extraction_breakdown")
        assert "count(content)" in sql
        assert "extraction_method" in sql
        assert "extraction_quality" in sql

    def test_categorization_eligible_uses_summarized_status(self) -> None:
        _, sql = next((n, s) for n, s in VERIFICATION_QUERIES if n == "eligible_for_categorization")
        assert "status = 'summarized'" in sql

    def test_analysis_eligible_uses_categorized_status(self) -> None:
        _, sql = next((n, s) for n, s in VERIFICATION_QUERIES if n == "eligible_for_analysis")
        assert "status = 'categorized'" in sql

    def test_active_verified_sources_uses_both_conditions(self) -> None:
        _, sql = next((n, s) for n, s in VERIFICATION_QUERIES if n == "active_verified_sources")
        assert "is_active = true" in sql
        assert "status = 'verified'" in sql


# ---------------------------------------------------------------------------
# Schema inspection helper
# ---------------------------------------------------------------------------


class TestPrimaryTableFor:
    def test_article_queries_map_to_articles(self) -> None:
        assert _primary_table_for("article_counts_by_status") == "articles"
        assert _primary_table_for("extraction_breakdown") == "articles"
        assert _primary_table_for("eligible_for_categorization") == "articles"
        assert _primary_table_for("eligible_for_analysis") == "articles"

    def test_sources_query_maps_to_sources(self) -> None:
        assert _primary_table_for("active_verified_sources") == "sources"

    def test_unknown_query_returns_none(self) -> None:
        assert _primary_table_for("unknown") is None
