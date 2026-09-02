"""
Integration tests for basic application/runtime paths.
"""

from __future__ import annotations

import pytest

from ai_news_digest.bootstrap.container import Container
from ai_news_digest.domain.models.source import Source


@pytest.mark.integration
async def test_container_can_build(db_session) -> None:
    """Verify that the DI container builds with a real database session."""
    container = Container(db_session)
    assert container is not None


@pytest.mark.integration
async def test_source_repository_crud(db_session) -> None:
    """Verify basic repository operations against a real database."""
    from ai_news_digest.infrastructure.database.repositories.source_repository import (
        SourceRepository,
    )

    repo = SourceRepository(db_session)
    source = Source.create(
        name="Integration Test Source",
        feed_url="https://example.com/feed.xml",
    )

    created = await repo.create(source)
    assert created.id is not None
    assert created.name == "Integration Test Source"

    fetched = await repo.get_by_id(created.id)
    assert fetched is not None
    assert fetched.name == "Integration Test Source"
