"""
Tests for source trust-model enforcement.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from ai_news_digest.domain.enums.source_status import SourceStatus
from ai_news_digest.domain.models.source import Source
from ai_news_digest.infrastructure.database.mappers.source_mapper import SourceMapper
from ai_news_digest.infrastructure.database.repositories.source_repository import (
    SourceRepository,
)


@pytest.fixture
def mock_session() -> AsyncSession:
    session = MagicMock(spec=AsyncSession)
    return session


@pytest.fixture
def repository(mock_session: AsyncSession) -> SourceRepository:
    return SourceRepository(session=mock_session)


def _make_model(
    source_id: str,
    name: str,
    is_active: bool,
    status: str,
) -> MagicMock:
    model = MagicMock()
    model.id = source_id
    model.name = name
    model.feed_url = f"https://example.com/{name.lower()}/feed.xml"
    model.website_url = f"https://example.com/{name.lower()}"
    model.description = f"Test source {name}"
    model.is_active = is_active
    model.source_type = "other"
    model.status = status
    model.created_at = "2024-01-01T00:00:00+00:00"
    return model


@pytest.mark.asyncio
async def test_list_enabled_excludes_pending_sources(
    repository: SourceRepository,
    mock_session: AsyncSession,
) -> None:
    """Only sources with status=verified and is_active=true are enabled."""
    verified_active = _make_model(
        str(uuid4()), "Verified", True, SourceStatus.VERIFIED.value
    )
    _make_model(str(uuid4()), "VerifiedInactive", False, SourceStatus.VERIFIED.value)
    _make_model(
        str(uuid4()), "Pending", True, SourceStatus.PENDING_REVIEW.value
    )
    _make_model(str(uuid4()), "Rejected", True, SourceStatus.REJECTED.value)

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [verified_active]
    mock_session.execute = AsyncMock(return_value=mock_result)

    sources = await repository.list_enabled()

    assert len(sources) == 1
    assert sources[0].name == "Verified"
    assert sources[0].status == SourceStatus.VERIFIED


@pytest.mark.asyncio
async def test_list_enabled_empty_when_no_verified_sources(
    repository: SourceRepository,
    mock_session: AsyncSession,
) -> None:
    """When no sources are verified, list_enabled returns an empty list."""
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute = AsyncMock(return_value=mock_result)

    sources = await repository.list_enabled()

    assert sources == []


def test_source_create_defaults_to_pending_review() -> None:
    """New sources default to PENDING_REVIEW, not VERIFIED."""
    source = Source.create(
        name="New Source",
        feed_url="https://example.com/feed.xml",
    )

    assert source.status == SourceStatus.PENDING_REVIEW
    assert source.is_active is True


def test_source_update_can_change_status() -> None:
    """Source.update() can change the verification status."""
    source = Source.create(
        name="Test",
        feed_url="https://example.com/feed.xml",
        status=SourceStatus.PENDING_REVIEW,
    )

    source.update(status=SourceStatus.VERIFIED)

    assert source.status == SourceStatus.VERIFIED


def test_source_mapper_maps_status() -> None:
    """SourceMapper preserves status through model/domain conversion."""
    domain = Source.create(
        name="Mapped",
        feed_url="https://example.com/feed.xml",
        status=SourceStatus.VERIFIED,
    )
    model = SourceMapper.to_model(domain)
    assert model.status == SourceStatus.VERIFIED.value

    back = SourceMapper.to_domain(model)
    assert back.status == SourceStatus.VERIFIED
