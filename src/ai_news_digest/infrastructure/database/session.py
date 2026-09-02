from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from ai_news_digest.core.config import settings

# ---------------------------------------------------------------------
# SQLAlchemy Engine
# ---------------------------------------------------------------------

connect_args: dict[str, dict[str, str]] = {}
if settings.database_url.startswith("postgresql+asyncpg"):
    connect_args["server_settings"] = {
        "statement_timeout": str(settings.database_statement_timeout)
    }

engine: AsyncEngine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    future=True,
    pool_pre_ping=True,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_timeout=settings.database_pool_timeout,
    pool_recycle=settings.database_pool_recycle,
    connect_args=connect_args,
)

# ---------------------------------------------------------------------
# Session Factory
# ---------------------------------------------------------------------

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# ---------------------------------------------------------------------
# Dependency
# ---------------------------------------------------------------------


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides an async database session.

    The session is automatically closed after the request completes.
    """
    async with SessionLocal() as session:
        yield session


def get_pool_metrics() -> dict[str, int]:
    """Return current connection pool metrics.

    ``checkedout``/``active`` report the number of connections currently in
    use, ``checkedin``/``idle`` the number returned to the pool, and
    ``overflow`` the number of connections beyond ``pool_size`` that are open.
    """
    pool = engine.pool
    checkedin = pool.checkedin()  # type: ignore[attr-defined]
    checkedout = pool.checkedout()  # type: ignore[attr-defined]
    overflow = pool.overflow()  # type: ignore[attr-defined]
    return {
        "size": pool.size(),  # type: ignore[attr-defined]
        "checkedin": checkedin,
        "checkedout": checkedout,
        "idle": checkedin,
        "active": checkedout,
        "overflow": overflow,
    }
