from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ai_news_digest.bootstrap.container import Container
from ai_news_digest.core.config import settings
from ai_news_digest.infrastructure.database.url import get_asyncpg_engine_kwargs


async def get_container() -> AsyncGenerator[Container, None]:
    """
    Provide a Container instance with a fresh database session for worker tasks.

    Creates a dedicated engine/session per task so the connection pool is
    bound to the worker task's event loop. This avoids the asyncpg
    "Future attached to a different loop" failure when the global
    ``SessionLocal`` was imported in a different loop context.
    """
    normalized_url, connect_args = get_asyncpg_engine_kwargs(settings.database_url)
    if normalized_url.startswith("postgresql+asyncpg"):
        server_settings = connect_args.setdefault("server_settings", {})
        if isinstance(server_settings, dict):
            server_settings["statement_timeout"] = str(settings.database_statement_timeout)

    engine = create_async_engine(
        normalized_url,
        echo=settings.debug,
        future=True,
        pool_pre_ping=True,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_timeout=settings.database_pool_timeout,
        pool_recycle=settings.database_pool_recycle,
        connect_args=connect_args,
    )
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    async with session_factory() as session:
        yield Container(session)
    await engine.dispose()


__all__ = ["get_container"]
