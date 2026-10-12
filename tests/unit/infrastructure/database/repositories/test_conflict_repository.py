"""
Unit tests for ConflictRepository.
"""

from __future__ import annotations

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


def _make_conflict(claim_a_id: UUID, claim_b_id: UUID, **overrides: Any) -> Conflict:
    """Build a conflict between two fixed claims, preserving the given order."""
    fields: dict[str, Any] = {
        "claim_a_id": claim_a_id,
        "claim_b_id": claim_b_id,
        "article_a_id": uuid4(),
        "article_b_id": uuid4(),
        "source_a_id": uuid4(),
        "source_b_id": uuid4(),
        "conflict_type": ConflictType.NUMERIC,
        "confidence": 0.7,
        "explanation": "Different numeric values.",
        "detection_version": "v1",
    }
    fields.update(overrides)
    return Conflict.create(**fields)


class TestSqlAlchemyConflictRepository:
    @pytest.mark.asyncio
    async def test_create_and_get(self, db_session: AsyncSession, conflict: Conflict) -> None:
        repository = SqlAlchemyConflictRepository(db_session)
        created = await repository.create(conflict)
        assert created.id is not None

        fetched = await repository.get_by_id(created.id)
        assert fetched is not None
        assert fetched.conflict_type == ConflictType.NUMERIC
        assert fetched.status == ConflictStatus.POTENTIAL

    @pytest.mark.asyncio
    async def test_find_existing(self, db_session: AsyncSession, conflict: Conflict) -> None:
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
    async def test_find_existing_matches_pair_in_either_order(
        self, db_session: AsyncSession, conflict: Conflict
    ) -> None:
        """The stored pair must round-trip regardless of argument order.

        ``Conflict.create`` stores the claim pair in the order the detector
        visited the claims, so the lookup cannot assume a canonical ordering.
        Before the fix, a lookup whose order differed from the stored order
        returned ``None``, breaking deduplication for roughly half of the
        randomly generated pairs this fixture produces.
        """
        repository = SqlAlchemyConflictRepository(db_session)
        created = await repository.create(conflict)

        forward = await repository.find_existing(
            claim_a_id=created.claim_a_id,
            claim_b_id=created.claim_b_id,
            detection_version="v1",
        )
        reversed_lookup = await repository.find_existing(
            claim_a_id=created.claim_b_id,
            claim_b_id=created.claim_a_id,
            detection_version="v1",
        )

        assert forward is not None
        assert forward.id == created.id
        assert reversed_lookup is not None
        assert reversed_lookup.id == created.id

    @pytest.mark.asyncio
    async def test_find_existing_matches_pair_written_in_reverse_order(
        self, db_session: AsyncSession
    ) -> None:
        """A row stored with the opposite pair order is still found."""
        repository = SqlAlchemyConflictRepository(db_session)
        first = UUID("00000000-0000-0000-0000-000000000002")
        second = UUID("00000000-0000-0000-0000-000000000001")
        created = await repository.create(_make_conflict(first, second))

        # The stored order is preserved, and the canonical (min, max) order is
        # the reverse of it, which is what the previous implementation queried.
        assert created.claim_a_id == first
        assert created.claim_b_id == second
        assert str(second) < str(first)

        existing = await repository.find_existing(
            claim_a_id=second,
            claim_b_id=first,
            detection_version="v1",
        )

        assert existing is not None
        assert existing.id == created.id

    @pytest.mark.asyncio
    async def test_find_existing_ignores_other_pairs(self, db_session: AsyncSession) -> None:
        """An unrelated claim pair must not match."""
        repository = SqlAlchemyConflictRepository(db_session)
        first = UUID("00000000-0000-0000-0000-000000000001")
        second = UUID("00000000-0000-0000-0000-000000000002")
        await repository.create(_make_conflict(first, second))

        other_a = UUID("00000000-0000-0000-0000-000000000003")
        other_b = UUID("00000000-0000-0000-0000-000000000004")

        assert (
            await repository.find_existing(
                claim_a_id=other_a,
                claim_b_id=other_b,
                detection_version="v1",
            )
            is None
        )

    @pytest.mark.asyncio
    async def test_find_existing_ignores_other_detection_versions(
        self, db_session: AsyncSession
    ) -> None:
        """Only the requested detection version matches."""
        repository = SqlAlchemyConflictRepository(db_session)
        first = UUID("00000000-0000-0000-0000-000000000001")
        second = UUID("00000000-0000-0000-0000-000000000002")
        await repository.create(_make_conflict(first, second))

        assert (
            await repository.find_existing(
                claim_a_id=first,
                claim_b_id=second,
                detection_version="v2",
            )
            is None
        )

    @pytest.mark.asyncio
    async def test_find_existing_tolerates_pair_stored_twice_in_both_orders(
        self, db_session: AsyncSession
    ) -> None:
        """Legacy writes could duplicate a pair in both orders.

        The lookup returns a single conflict instead of raising
        ``MultipleResultsFound`` so that re-running detection does not crash on
        pre-existing rows.
        """
        repository = SqlAlchemyConflictRepository(db_session)
        first = UUID("00000000-0000-0000-0000-000000000001")
        second = UUID("00000000-0000-0000-0000-000000000002")
        created_forward = await repository.create(_make_conflict(first, second))
        created_reverse = await repository.create(_make_conflict(second, first))

        existing = await repository.find_existing(
            claim_a_id=first,
            claim_b_id=second,
            detection_version="v1",
        )

        assert existing is not None
        assert existing.id in {created_forward.id, created_reverse.id}

    @pytest.mark.asyncio
    async def test_list_recent(self, db_session: AsyncSession, conflict: Conflict) -> None:
        repository = SqlAlchemyConflictRepository(db_session)
        await repository.create(conflict)
        results = await repository.list_recent(limit=10)
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_update_status(self, db_session: AsyncSession, conflict: Conflict) -> None:
        repository = SqlAlchemyConflictRepository(db_session)
        created = await repository.create(conflict)
        created.update_status(ConflictStatus.CONFIRMED)
        updated = await repository.update(created)
        assert updated.status == ConflictStatus.CONFIRMED

    @pytest.mark.asyncio
    async def test_count(self, db_session: AsyncSession, conflict: Conflict) -> None:
        repository = SqlAlchemyConflictRepository(db_session)
        await repository.create(conflict)
        count = await repository.count()
        assert count >= 1


__all__ = ["TestSqlAlchemyConflictRepository"]
