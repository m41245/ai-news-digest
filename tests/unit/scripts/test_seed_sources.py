"""
Unit tests for seed_sources script.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from ai_news_digest.scripts.seed_sources import main


@pytest.mark.asyncio
async def test_seed_sources_inserts_and_skips() -> None:
    source = SimpleNamespace(id=uuid4())
    repo = MagicMock()
    repo.get_by_feed_url = AsyncMock(side_effect=[None, source, source, source, source, source])
    repo.create = AsyncMock()

    container = MagicMock()
    container.source_repository = repo

    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)

    async def gen():
        yield session

    with (
        patch("ai_news_digest.scripts.seed_sources.get_db_session", return_value=gen()),
        patch("ai_news_digest.scripts.seed_sources.Container", return_value=container),
    ):
        await main()

    assert repo.create.await_count == 1


__all__ = ["test_seed_sources_inserts_and_skips"]
