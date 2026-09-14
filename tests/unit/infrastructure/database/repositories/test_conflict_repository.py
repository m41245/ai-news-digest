"""
Unit tests for ConflictRepository.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from ai_news_digest.domain.enums.conflict_status import ConflictStatus
from ai_news_digest.domain.enums.conflict_type import ConflictType
from ai_news_digest.domain.models.conflict import Conflict
from ai_news_digest.infrastructure.database.repositories.conflict_repository import (
    SqlAlchemyConflictRepository,
)


@pytest.fixture
def mock_session() -> Any:
    """Create a mock AsyncSession."""
    return Any  # We'll use a real session in integration tests


@pytest.fixture
def conflict() -> Conflict:
    """Create a sample Conflict."""
    return Conflict.create(
        claim_a_id=uuid4(),
        claim_b_id=uuid4(),
        article_a_id=uuid4(),
        article_b_id=uuid4(),
        source_a_id=uuid4(),
        source_b_id=uuid4(),
        conflict_type=ConflictType.NUMERIC,
        confidence=0.7,
        explanation="Different numeric values.",
        detection_version="v1",
    )


class TestSqlAlchemyConflictRepository:
    @pytest.mark.asyncio
    async def test_create_and_get(
        self, db_session: AsyncSession, conflict: Conflict
    ) -> None:
        repository = SqlAlchemyConflictRepository(db_session)
        created = await repository.create(conflict)
        assert created.id is not None

        fetched = await repository.get_by_id(created.id)
        assert fetched is not None
        assert fetched.conflict_type == ConflictType.NUMERIC
        assert fetched.status == ConflictStatus.POTENTIAL

    @pytest.mark.asyncio
    async def test_find_existing(
        self, db_session: AsyncSession, conflict: Conflict
    ) -> None:
        repository = SqlAlchemyConflictRepository(db_session)
        created = await repository.create(conflict)
        existing = await repository.find_existing(
            claim_a_id=created.claim_a_id,
            claim_b_id=created.claim_b_id,
            detection_version="v1",
        )
        assert existing is not None
        assert existing.id == created.id

    @pytest.mark.asyncio
    async def test_list_recent(
        self, db_session: AsyncSession, conflict: Conflict
    ) -> None:
        repository = SqlAlchemyConflictRepository(db_session)
        await repository.create(conflict)
        results = await repository.list_recent(limit=10)
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_update_status(
        self, db_session: AsyncSession, conflict: Conflict
    ) -> None:
        repository = SqlAlchemyConflictRepository(db_session)
        created = await repository.create(conflict)
        created.update_status(ConflictStatus.CONFIRMED)
        updated = await repository.update(created)
        assert updated.status == ConflictStatus.CONFIRMED

    @pytest.mark.asyncio
    async def test_count(
        self, db_session: AsyncSession, conflict: Conflict
    ) -> None:
        repository = SqlAlchemyConflictRepository(db_session)
        await repository.create(conflict)
        count = await repository.count()
        assert count >= 1


__all__ = ["TestSqlAlchemyConflictRepository"]
