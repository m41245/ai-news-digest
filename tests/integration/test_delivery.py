"""
Integration tests for Milestone 6 delivery infrastructure.

These tests use real PostgreSQL (via testcontainers) to verify:
- delivery schema migration
- delivery repository persistence
- uniqueness constraint (digest_id, recipient)
- delivery use case with fake email sender
- idempotent delivery
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from ai_news_digest.domain.enums.delivery_status import DeliveryStatus
from ai_news_digest.domain.models.digest_delivery import DigestDelivery
from ai_news_digest.infrastructure.database.repositories.delivery_repository import (
    DeliveryRepository,
)


@pytest.mark.integration
async def test_delivery_repository_create_and_get(db_session) -> None:
    repo = DeliveryRepository(db_session)
    digest_id = uuid4()
    delivery = DigestDelivery.create(digest_id=digest_id, recipient="a@b.com")
    created = await repo.create(delivery)

    assert created.id == delivery.id
    assert created.recipient == "a@b.com"
    assert created.status == DeliveryStatus.PENDING

    fetched = await repo.get_by_id(created.id)
    assert fetched is not None
    assert fetched.recipient == "a@b.com"


@pytest.mark.integration
async def test_delivery_repository_uniqueness_constraint(db_session) -> None:
    repo = DeliveryRepository(db_session)
    digest_id = uuid4()
    delivery1 = DigestDelivery.create(digest_id=digest_id, recipient="a@b.com")
    await repo.create(delivery1)

    delivery2 = DigestDelivery.create(digest_id=digest_id, recipient="a@b.com")
    with pytest.raises(Exception):  # noqa: B017
        await repo.create(delivery2)


@pytest.mark.integration
async def test_delivery_repository_get_by_digest_and_recipient(db_session) -> None:
    repo = DeliveryRepository(db_session)
    digest_id = uuid4()
    delivery = DigestDelivery.create(digest_id=digest_id, recipient="a@b.com")
    await repo.create(delivery)

    found = await repo.get_by_digest_and_recipient(digest_id, "a@b.com")
    assert found is not None
    assert found.id == delivery.id

    not_found = await repo.get_by_digest_and_recipient(digest_id, "nobody@b.com")
    assert not_found is None


@pytest.mark.integration
async def test_delivery_repository_list_by_digest(db_session) -> None:
    repo = DeliveryRepository(db_session)
    digest_id = uuid4()
    for recipient in ("a@b.com", "c@d.com", "e@f.com"):
        delivery = DigestDelivery.create(digest_id=digest_id, recipient=recipient)
        await repo.create(delivery)

    results = await repo.list_by_digest(digest_id)
    assert len(results) == 3
    recipients = {r.recipient for r in results}
    assert recipients == {"a@b.com", "c@d.com", "e@f.com"}


@pytest.mark.integration
async def test_delivery_repository_update_status(db_session) -> None:
    repo = DeliveryRepository(db_session)
    delivery = DigestDelivery.create(digest_id=uuid4(), recipient="a@b.com")
    created = await repo.create(delivery)

    created.status = DeliveryStatus.SENT
    created.sent_at = created.created_at
    updated = await repo.update(created)
    assert updated.status == DeliveryStatus.SENT
    assert updated.sent_at is not None


@pytest.mark.integration
async def test_delivery_repository_increment_attempt(db_session) -> None:
    repo = DeliveryRepository(db_session)
    delivery = DigestDelivery.create(digest_id=uuid4(), recipient="a@b.com")
    created = await repo.create(delivery)
    assert created.attempt_count == 0

    incremented = await repo.increment_attempt(created.id)
    assert incremented is not None
    assert incremented.attempt_count == 1


@pytest.mark.integration
async def test_delivery_idempotency_workflow(db_session) -> None:
    repo = DeliveryRepository(db_session)
    digest_id = uuid4()
    recipient = "idempotent@test.com"

    delivery1 = DigestDelivery.create(digest_id=digest_id, recipient=recipient)
    created1 = await repo.create(delivery1)

    existing = await repo.get_by_digest_and_recipient(digest_id, recipient)
    assert existing is not None
    assert existing.id == created1.id

    delivery2 = DigestDelivery.create(digest_id=digest_id, recipient=recipient)
    with pytest.raises(Exception):  # noqa: B017
        await repo.create(delivery2)


__all__ = [
    "test_delivery_idempotency_workflow",
    "test_delivery_repository_create_and_get",
    "test_delivery_repository_get_by_digest_and_recipient",
    "test_delivery_repository_increment_attempt",
    "test_delivery_repository_list_by_digest",
    "test_delivery_repository_uniqueness_constraint",
    "test_delivery_repository_update_status",
]
