from __future__ import annotations

from collections.abc import AsyncGenerator

from ai_news_digest.bootstrap.container import Container
from ai_news_digest.infrastructure.database.session import get_db_session


async def get_container() -> AsyncGenerator[Container, None]:
    """Provide a Container instance backed by a fresh database session."""
    async for session in get_db_session():
        yield Container(session)


__all__ = ["get_container"]
