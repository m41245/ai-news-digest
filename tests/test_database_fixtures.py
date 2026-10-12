"""
Regression tests for the shared async database fixtures in ``tests/conftest.py``.

Two defects were fixed in the root ``tests/conftest.py``:

1. ``async_engine`` was session-scoped while pytest-asyncio's default fixture
   loop scope is function-scoped, so the engine was created in one event loop
   and disposed in another (``ScopeMismatch`` at setup, plus pooled connections
   left bound to a closed loop).
2. The PostgreSQL URL was built with a ``postgresql://`` ->
   ``postgresql+asyncpg://`` string replacement that was a no-op because
   testcontainers already returns ``postgresql+psycopg2://``.

These tests deliberately live next to ``tests/conftest.py`` so that they resolve
the *root* ``postgres_container`` (session-scoped) and ``async_engine``
(function-scoped) fixtures. Placing them under ``tests/integration/`` would make
them exercise the identically named but differently scoped fixtures declared in
``tests/integration/conftest.py`` instead.

Docker/testcontainers is required; the tests skip with an explicit reason when
it is unavailable rather than silently passing.
"""

from __future__ import annotations

from collections.abc import Generator
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import make_url, text

pytest.importorskip("testcontainers", reason="testcontainers is required for these fixture tests")

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine

pytestmark = pytest.mark.integration

# Identities of the fixtures observed by each test in this module. They are
# asserted once, after every test has run, so the checks do not depend on
# execution order.
_seen_containers: list[int] = []
_seen_engines: list[int] = []


@pytest.fixture(scope="module", autouse=True)
def _assert_fixture_scopes() -> Generator[None, None, None]:
    """Assert the container is shared while the engine is rebuilt per test."""
    yield

    if _seen_containers:
        assert len(set(_seen_containers)) == 1, (
            "postgres_container must be session-scoped so a single container "
            "serves every test in the module"
        )
    if _seen_engines:
        assert len(set(_seen_engines)) == len(_seen_engines), (
            "async_engine must be function-scoped so each test gets its own "
            "engine bound to its own event loop"
        )


def _track(postgres_container: object, engine: AsyncEngine) -> None:
    """Record the fixture identities used by a single test."""
    _seen_containers.append(id(postgres_container))
    _seen_engines.append(id(engine))


async def test_session_container_and_function_engine_work_together(
    postgres_container: object,
    async_engine: AsyncEngine,
) -> None:
    """The session-scoped container backs the function-scoped engine."""
    _track(postgres_container, async_engine)

    expected_url = make_url(
        postgres_container.get_connection_url(driver="asyncpg")  # type: ignore[attr-defined]
    )
    engine_url = async_engine.url
    assert engine_url.drivername == expected_url.drivername == "postgresql+asyncpg"
    assert engine_url.host == expected_url.host
    assert engine_url.port == expected_url.port
    assert engine_url.database == expected_url.database
    assert engine_url.username == expected_url.username


async def test_async_engine_uses_asyncpg_driver(
    postgres_container: object,
    async_engine: AsyncEngine,
) -> None:
    """The engine speaks the asyncpg dialect, not the psycopg2 default."""
    _track(postgres_container, async_engine)

    assert async_engine.dialect.name == "postgresql"
    assert async_engine.dialect.driver == "asyncpg"
    assert async_engine.dialect.is_async is True
    assert async_engine.url.drivername == "postgresql+asyncpg"


async def test_async_engine_can_execute_query(
    postgres_container: object,
    async_engine: AsyncEngine,
) -> None:
    """The engine is usable in the same event loop that created it."""
    _track(postgres_container, async_engine)

    async with async_engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        assert result.scalar() == 1


async def test_async_engine_survives_two_consecutive_tests(
    postgres_container: object,
    async_engine: AsyncEngine,
) -> None:
    """Each test gets its own loop, so the engine must be re-created per test.

    This is the regression guard for the ScopeMismatch defect: a session-scoped
    async fixture requested from function-scoped loops fails at setup time.
    """
    _track(postgres_container, async_engine)

    async with async_engine.connect() as conn:
        result = await conn.execute(text("SELECT 2"))
        assert result.scalar() == 2


async def test_engine_disposal_does_not_leak_connections(
    postgres_container: object,
    async_engine: AsyncEngine,
) -> None:
    """Disposing the engine closes every pooled connection it opened."""
    _track(postgres_container, async_engine)

    async with async_engine.connect() as conn:
        await conn.execute(text("SELECT 1"))

    pool = async_engine.pool
    assert pool.checkedout() == 0, "connection was not returned to the pool"

    await async_engine.dispose()

    assert pool.checkedin() == 0, "dispose() left idle connections in the pool"
    assert pool.checkedout() == 0, "dispose() left checked-out connections open"
