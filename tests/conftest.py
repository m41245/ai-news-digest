"""
Shared pytest fixtures and configuration for AI News Digest tests.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Generator
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from ai_news_digest.infrastructure.database.base import Base

if TYPE_CHECKING:
    from ai_news_digest.bootstrap.container import Container


@pytest.fixture(scope="session")
def event_loop_policy() -> asyncio.WindowsSelectorEventLoopPolicy | None:
    """
    Use the default event loop policy.

    On Windows, this may need to be adjusted for async test compatibility.
    """
    return None


@pytest.fixture(scope="session")
def postgres_container() -> Generator[object, None, None]:
    """
    Create a PostgreSQL test container.

    This fixture starts a PostgreSQL container for the test session
    and stops it after all tests complete.
    """
    try:
        from testcontainers.postgres import PostgresContainer

        container = PostgresContainer("postgres:16-alpine")
        with container:
            yield container
    except Exception as exc:
        pytest.skip(f"Docker is not available for integration tests: {exc}")


@pytest.fixture(scope="session")
def redis_container() -> Generator[object, None, None]:
    """
    Create a Redis test container.

    This fixture starts a Redis container for the test session
    and stops it after all tests complete.
    """
    try:
        from testcontainers.redis import RedisContainer

        container = RedisContainer("redis:7-alpine")
        with container:
            yield container
    except Exception as exc:
        pytest.skip(f"Docker is not available for integration tests: {exc}")


@pytest.fixture(scope="session")
async def async_engine(
    postgres_container: object,
) -> AsyncGenerator[AsyncEngine, None]:
    """
    Create a test database engine using testcontainers.

    This fixture creates an async SQLAlchemy engine connected to the
    test PostgreSQL container.
    """
    connection_url = postgres_container.get_connection_url()
    engine = create_async_engine(
        connection_url.replace("postgresql://", "postgresql+asyncpg://"),
        echo=False,
        future=True,
    )

    yield engine

    await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(
    async_engine,
) -> AsyncGenerator[AsyncSession, None]:
    """
    Create a fresh database session for each test.

    This fixture:
    - Creates all tables before the test
    - Yields a session
    - Drops all tables after the test
    """
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
def mock_article_repository() -> MagicMock:
    """Mock article repository for unit tests."""
    return AsyncMock()


@pytest.fixture
def mock_source_repository() -> MagicMock:
    """Mock source repository for unit tests."""
    return AsyncMock()


@pytest.fixture
def mock_category_repository() -> MagicMock:
    """Mock category repository for unit tests."""
    return AsyncMock()


@pytest.fixture
def mock_digest_repository() -> MagicMock:
    """Mock digest repository for unit tests."""
    return AsyncMock()


@pytest.fixture
def mock_rss_fetcher() -> MagicMock:
    """Mock RSS fetcher for unit tests."""
    return AsyncMock()


@pytest.fixture
def mock_llm_client() -> MagicMock:
    """Mock LLM client for unit tests."""
    return AsyncMock()


@pytest.fixture
def mock_email_sender() -> MagicMock:
    """Mock email sender for unit tests."""
    return AsyncMock()


@pytest.fixture
def mock_cache_store() -> MagicMock:
    """Mock cache store for unit tests."""
    return AsyncMock()


@pytest.fixture
def mock_feed_service() -> MagicMock:
    """Mock feed service for unit tests."""
    return AsyncMock()


@pytest.fixture
def mock_rss_client() -> MagicMock:
    """Mock RSS client for unit tests."""
    return AsyncMock()


@pytest.fixture
def mock_rss_parser() -> MagicMock:
    """Mock RSS parser for unit tests."""
    return MagicMock()


@pytest.fixture
def mock_ingest_from_source() -> MagicMock:
    """Mock ingest from source use case for unit tests."""
    return AsyncMock()


@pytest.fixture
def mock_user_repository() -> MagicMock:
    """Mock user repository for unit tests."""
    return AsyncMock()


@pytest.fixture
async def container(
    db_session: AsyncSession,
) -> AsyncGenerator[Container, None]:
    """
    Create a DI container with a real database session.

    This fixture provides a Container instance with a real database session
    for integration tests. For unit tests, use the mock fixtures instead.
    """
    from ai_news_digest.bootstrap.container import Container

    container = Container(db_session)
    yield container
