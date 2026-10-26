"""
Unit tests for seed_sources script.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from scripts.seed_sources import main as compat_main

from ai_news_digest.domain.enums.source_status import SourceStatus
from ai_news_digest.domain.enums.source_type import SourceType
from ai_news_digest.scripts.seed_sources import main as canonical_main


def _make_session_and_container(repo: MagicMock) -> tuple[MagicMock, object]:
    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)

    async def gen():
        yield session

    container = MagicMock()
    container.source_repository = repo
    return gen, container


@pytest.mark.asyncio
@pytest.mark.parametrize("main", [canonical_main, compat_main], ids=["canonical", "compat"])
async def test_seed_sources_inserts_pending_and_skips_existing(main) -> None:
    existing = SimpleNamespace(
        id=uuid4(),
        status=SourceStatus.VERIFIED,
        is_active=True,
    )
    repo = MagicMock()
    repo.get_by_feed_url = AsyncMock(side_effect=[None] + [existing] * 5)
    repo.create = AsyncMock()
    repo.update = AsyncMock()

    gen, container = _make_session_and_container(repo)

    with (
        patch("ai_news_digest.scripts.seed_sources.get_db_session", return_value=gen()),
        patch("ai_news_digest.scripts.seed_sources.Container", return_value=container),
    ):
        await main()

    assert repo.create.await_count == 1
    created = repo.create.await_args.args[0]
    assert created.status == SourceStatus.PENDING_REVIEW
    assert created.is_eligible() is False
    assert created.publisher == "OpenAI"
    assert created.source_type == SourceType.OFFICIAL_COMPANY
    assert created.verification_notes is None

    # Existing sources are skipped without mutation.
    assert repo.update.await_count == 0
    assert repo.get_by_feed_url.await_count == 6


@pytest.mark.asyncio
@pytest.mark.parametrize("main", [canonical_main, compat_main], ids=["canonical", "compat"])
async def test_seed_sources_skips_all_existing(main) -> None:
    existing = SimpleNamespace(
        id=uuid4(),
        status=SourceStatus.VERIFIED,
        is_active=False,
    )
    repo = MagicMock()
    repo.get_by_feed_url = AsyncMock(return_value=existing)
    repo.create = AsyncMock()
    repo.update = AsyncMock()

    gen, container = _make_session_and_container(repo)

    with (
        patch("ai_news_digest.scripts.seed_sources.get_db_session", return_value=gen()),
        patch("ai_news_digest.scripts.seed_sources.Container", return_value=container),
    ):
        await main()

    assert repo.create.await_count == 0
    assert repo.update.await_count == 0


__all__ = [
    "test_seed_sources_inserts_pending_and_skips_existing",
    "test_seed_sources_skips_all_existing",
]
