"""Unit tests for DigestDelivery domain model."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from ai_news_digest.domain.enums.delivery_status import DeliveryStatus
from ai_news_digest.domain.models.digest_delivery import DigestDelivery


def test_digest_delivery_create() -> None:
    digest_id = uuid4()
    recipient = "user@example.com"
    delivery = DigestDelivery.create(digest_id=digest_id, recipient=recipient)

    assert delivery.digest_id == digest_id
    assert delivery.recipient == recipient
    assert delivery.status == DeliveryStatus.PENDING
    assert delivery.attempt_count == 0
    assert delivery.sent_at is None
    assert delivery.failed_at is None
    assert delivery.failure_reason is None
    assert delivery.provider_message_id is None
    assert delivery.id is not None
    assert isinstance(delivery.created_at, datetime)
    assert isinstance(delivery.updated_at, datetime)


def test_digest_delivery_create_sets_timestamps() -> None:
    delivery = DigestDelivery.create(digest_id=uuid4(), recipient="a@b.com")
    assert (datetime.now(UTC) - delivery.created_at).total_seconds() < 1
    assert (datetime.now(UTC) - delivery.updated_at).total_seconds() < 1


def test_digest_delivery_slots() -> None:
    delivery = DigestDelivery.create(digest_id=uuid4(), recipient="a@b.com")
    with pytest.raises(AttributeError):
        delivery.new_attr = "value"  # type: ignore[misc]


__all__ = [
    "test_digest_delivery_create",
    "test_digest_delivery_create_sets_timestamps",
    "test_digest_delivery_slots",
]
