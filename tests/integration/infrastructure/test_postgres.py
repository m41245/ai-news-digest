"""
Integration tests for PostgreSQL connectivity and schema.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import inspect as sa_inspect
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import insert

from ai_news_digest.infrastructure.database.models.digest_model import DigestModel


@pytest.mark.integration
async def test_postgres_connection(async_engine) -> None:
    """Verify that the test database is reachable."""
    async with async_engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        assert result.scalar_one() == 1


@pytest.mark.integration
async def test_postgres_schema_created(db_session, async_engine) -> None:
    """Verify that all expected tables are created by the schema."""
    async with async_engine.connect() as conn:
        tables = await conn.run_sync(lambda sync_conn: sa_inspect(sync_conn).get_table_names())

    expected_tables = {
        "articles",
        "categories",
        "digest_articles",
        "digests",
        "sources",
        "users",
    }

    for table in expected_tables:
        assert table in tables, f"Expected table '{table}' not found in schema"


@pytest.mark.integration
async def test_postgres_digest_title_unique_constraint(db_session) -> None:
    """Verify that the digest title unique constraint is enforced."""
    stmt = insert(DigestModel).values(
        id=str(uuid4()),
        title="Unique Title",
        content="content",
        format="markdown",
        generated_at=datetime.now(UTC),
    )

    await db_session.execute(stmt)
    await db_session.commit()

    with pytest.raises(IntegrityError):
        await db_session.execute(stmt)
        await db_session.commit()
