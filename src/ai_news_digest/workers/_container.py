from __future__ import annotations

from collections.abc import AsyncGenerator

from ai_news_digest.bootstrap.container import Container
from ai_news_digest.infrastructure.database.session import SessionLocal


async def get_container() -> AsyncGenerator[Container, None]:
    """
    Provide a Container instance with a fresh database session for worker tasks.
    """
    async with SessionLocal() as session:
        yield Container(session)


__all__ = ["get_container"]
