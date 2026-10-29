"""
Integration tests for migration downgrade→re-upgrade cycle.

Regression test for the bug where migration 001's downgrade failed to
explicitly drop the ``articlestatus`` PostgreSQL native enum type, causing
re-upgrade to fail with ``type "articlestatus" already exists``.

These tests run against a real PostgreSQL container and exercise the full
Alembic migration chain (001 → 035) end-to-end.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from sqlalchemy import inspect as sa_inspect
from sqlalchemy import text

if TYPE_CHECKING:
    from testcontainers.postgres import PostgresContainer

ALEMBIC_INI = Path(__file__).resolve().parent.parent.parent / "alembic.ini"
EXPECTED_TABLES = frozenset(
    {
        "article_categories",
        "article_companies",
        "article_topics",
        "articles",
        "categories",
        "claim_evidence",
        "claims",
        "companies",
        "component_health_snapshots",
        "conflicts",
        "digest_articles",
        "digest_deliveries",
        "digests",
        "evaluation_metrics",
        "evaluation_runs",
        "followed_stories",
        "notification_deliveries",
        "notification_preferences",
        "notifications",
        "operational_alerts",
        "quality_gate_results",
        "quality_snapshots",
        "relationships",
        "saved_stories",
        "source_trust_decisions",
        "sources",
        "story_activity",
        "story_clusters",
        "story_event_articles",
        "story_event_claims",
        "story_events",
        "topics",
        "trends",
        "user_collections",
        "user_followed_categories",
        "user_followed_companies",
        "user_followed_sources",
        "user_followed_topics",
        "user_muted_categories",
        "user_muted_companies",
        "user_muted_sources",
        "user_muted_topics",
        "user_preference_profiles",
        "users",
    }
)


def _table_names(sync_conn) -> set[str]:
    return set(sa_inspect(sync_conn).get_table_names())


def _assert_topics_name_schema(sync_conn) -> None:
    inspector = sa_inspect(sync_conn)
    name_column = next(
        (column for column in inspector.get_columns("topics") if column["name"] == "name"),
        None,
    )
    assert name_column is not None, "topics.name column is missing"
    assert name_column["type"].length == 255

    has_unique_constraint = any(
        tuple(constraint.get("column_names") or ()) == ("name",)
        for constraint in inspector.get_unique_constraints("topics")
    )
    has_unique_index = any(
        index.get("unique") and tuple(index.get("column_names") or ()) == ("name",)
        for index in inspector.get_indexes("topics")
    )
    assert has_unique_constraint or has_unique_index, (
        "topics.name must have a unique constraint or unique index"
    )


@pytest.mark.integration
async def test_migration_upgrade_to_head(
    postgres_container: PostgresContainer,
) -> None:
    """Fresh database should upgrade cleanly from base to head."""
    from alembic import command
    from alembic.config import Config

    from ai_news_digest.core.config import settings

    container_url = postgres_container.get_connection_url(driver="asyncpg")
    original_url = settings.database_url
    object.__setattr__(settings, "database_url", container_url)

    config = Config(str(ALEMBIC_INI))

    try:
        await asyncio.to_thread(command.upgrade, config, "head")

        from sqlalchemy.ext.asyncio import create_async_engine

        engine = create_async_engine(container_url)
        async with engine.connect() as conn:
            tables = await conn.run_sync(_table_names)
            await conn.run_sync(_assert_topics_name_schema)
        await engine.dispose()

        assert EXPECTED_TABLES.issubset(tables), (
            f"Missing tables after upgrade: {EXPECTED_TABLES - tables}"
        )
    finally:
        object.__setattr__(settings, "database_url", original_url)


@pytest.mark.integration
async def test_migration_035_downgrade_rejects_long_topic_name(
    postgres_container: PostgresContainer,
) -> None:
    """A rejected downgrade must preserve both the revision and long topic data."""
    from alembic import command
    from alembic.config import Config
    from sqlalchemy.ext.asyncio import create_async_engine

    from ai_news_digest.core.config import settings

    container_url = postgres_container.get_connection_url(driver="asyncpg")
    original_url = settings.database_url
    object.__setattr__(settings, "database_url", container_url)

    config = Config(str(ALEMBIC_INI))
    topic_id = str(uuid4())
    topic_name = "topic name longer than the old limit " + ("x" * 40)
    topic_slug = f"migration-035-downgrade-guard-{uuid4().hex[:8]}"
    try:
        await asyncio.to_thread(command.upgrade, config, "035")

        engine = create_async_engine(container_url)
        try:
            async with engine.connect() as conn:
                await conn.run_sync(_assert_topics_name_schema)
            async with engine.begin() as conn:
                await conn.execute(
                    text("INSERT INTO topics (id, slug, name) VALUES (:id, :slug, :name)"),
                    {"id": topic_id, "slug": topic_slug, "name": topic_name},
                )
        finally:
            await engine.dispose()

        with pytest.raises(
            RuntimeError,
            match=r"Cannot downgrade topics.name to VARCHAR\(64\)",
        ):
            await asyncio.to_thread(command.downgrade, config, "034")

        engine = create_async_engine(container_url)
        try:
            async with engine.connect() as conn:
                revision = (
                    await conn.execute(text("SELECT version_num FROM alembic_version"))
                ).scalar_one()
                stored_name = (
                    await conn.execute(
                        text("SELECT name FROM topics WHERE id = :id"),
                        {"id": topic_id},
                    )
                ).scalar_one()
                await conn.run_sync(_assert_topics_name_schema)
        finally:
            await engine.dispose()

        assert revision == "035"
        assert stored_name == topic_name
        assert len(stored_name) > 64

    finally:
        cleanup_engine = create_async_engine(container_url)
        try:
            async with cleanup_engine.begin() as conn:
                await conn.execute(
                    text("DELETE FROM topics WHERE id = :id"),
                    {"id": topic_id},
                )
        finally:
            await cleanup_engine.dispose()
        object.__setattr__(settings, "database_url", original_url)


@pytest.mark.integration
async def test_migration_downgrade_reupgrade_cycle(
    postgres_container: PostgresContainer,
) -> None:
    """Regression test: downgrade to base then re-upgrade to head must succeed.

    This guards against the migration 001 downgrade bug where the
    ``articlestatus`` native enum was not explicitly dropped, causing
    re-upgrade to fail with ``type "articlestatus" already exists``.
    """
    from alembic import command
    from alembic.config import Config

    from ai_news_digest.core.config import settings

    container_url = postgres_container.get_connection_url(driver="asyncpg")
    original_url = settings.database_url
    object.__setattr__(settings, "database_url", container_url)

    config = Config(str(ALEMBIC_INI))

    def _run_migrations() -> None:
        # Step 1: upgrade from base to head (fresh database → fully migrated)
        command.upgrade(config, "head")

        # Step 2: downgrade from head to base (drop everything, including the
        #         articlestatus enum via migration 001's downgrade)
        command.downgrade(config, "base")

        # Step 3: re-upgrade from base to head — this is the regression check.
        #         Without the DROP TYPE fix in migration 001, the
        #         articlestatus type would still exist and this call would
        #         raise "type already exists".
        command.upgrade(config, "head")

    try:
        await asyncio.to_thread(_run_migrations)

        # Verify all expected tables exist after re-upgrade
        from sqlalchemy.ext.asyncio import create_async_engine

        engine = create_async_engine(container_url)
        async with engine.connect() as conn:
            tables = await conn.run_sync(_table_names)
            await conn.run_sync(_assert_topics_name_schema)
        await engine.dispose()

        assert EXPECTED_TABLES.issubset(tables), (
            f"Missing tables after re-upgrade: {EXPECTED_TABLES - tables}"
        )
    finally:
        object.__setattr__(settings, "database_url", original_url)
