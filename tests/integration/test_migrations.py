"""
Integration tests for migration downgrade→re-upgrade cycle.

Regression test for the bug where migration 001's downgrade failed to
explicitly drop the ``articlestatus`` PostgreSQL native enum type, causing
re-upgrade to fail with ``type "articlestatus" already exists``.

These tests run against a real PostgreSQL container and exercise the full
Alembic migration chain (001 → 017) end-to-end.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import inspect as sa_inspect

if TYPE_CHECKING:
    from testcontainers.postgres import PostgresContainer

ALEMBIC_INI = Path(__file__).resolve().parent.parent.parent / "alembic.ini"
EXPECTED_TABLES = frozenset(
    {
        "articles",
        "categories",
        "digest_articles",
        "digests",
        "sources",
        "users",
        "digest_deliveries",
    }
)


def _table_names(sync_conn) -> set[str]:
    return set(sa_inspect(sync_conn).get_table_names())


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
        await engine.dispose()

        assert EXPECTED_TABLES.issubset(
            tables
        ), f"Missing tables after upgrade: {EXPECTED_TABLES - tables}"
    finally:
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
        await engine.dispose()

        assert EXPECTED_TABLES.issubset(
            tables
        ), f"Missing tables after re-upgrade: {EXPECTED_TABLES - tables}"
    finally:
        object.__setattr__(settings, "database_url", original_url)
