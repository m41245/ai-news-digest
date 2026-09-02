"""
Shared pytest fixtures for integration tests.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Generator

import pytest

from ai_news_digest.infrastructure.database.base import Base

# Import model modules so that Base.metadata is populated.
from ai_news_digest.infrastructure.database.models import (  # noqa: F401
    article_model,
    category_model,
    digest_article_model,
    digest_delivery_model,
    digest_model,
    source_model,
    user_model,
)

if pytest.importorskip("testcontainers", reason="testcontainers is required for integration tests"):
    from sqlalchemy.ext.asyncio import (
        AsyncEngine,
        AsyncSession,
        async_sessionmaker,
        create_async_engine,
    )
    from testcontainers.postgres import PostgresContainer
    from testcontainers.redis import RedisContainer


@pytest.fixture(scope="function")
def postgres_container() -> Generator[object, None, None]:
    """Create a PostgreSQL test container for each test."""
    try:
        with PostgresContainer("postgres:16-alpine") as container:
            yield container
    except Exception as exc:
        pytest.skip(f"Docker is not available for integration tests: {exc}")


@pytest.fixture(scope="function")
def redis_container() -> Generator[object, None, None]:
    """Create a Redis test container for each test."""
    try:
        with RedisContainer("redis:7-alpine") as container:
            yield container
    except Exception as exc:
        pytest.skip(f"Docker is not available for integration tests: {exc}")


@pytest.fixture(scope="function")
async def async_engine(
    postgres_container: object,
) -> AsyncGenerator[AsyncEngine, None]:
    """Create a test database engine using testcontainers."""
    connection_url = postgres_container.get_connection_url(driver="asyncpg")  # type: ignore[attr-defined]
    engine = create_async_engine(
        connection_url,
        echo=False,
        future=True,
    )

    yield engine

    await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(
    async_engine: AsyncEngine,
) -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session for each test."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session_maker = async_sessionmaker(
        async_engine,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        yield session

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def container(
    db_session: AsyncSession,
) -> AsyncGenerator[object, None]:
    """Create the application DI container for integration tests."""
    from ai_news_digest.bootstrap.container import Container

    yield Container(db_session)
