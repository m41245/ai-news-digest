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

engine: AsyncEngine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    future=True,
    pool_pre_ping=True,
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
