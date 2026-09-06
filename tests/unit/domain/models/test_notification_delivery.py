"""
Unit tests for ``NotificationDelivery`` domain model state machine.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from ai_news_digest.domain.enums.notification import DeliveryChannel, DeliveryStatus
from ai_news_digest.domain.models.notification import NotificationDelivery


def _make_delivery(status: DeliveryStatus = DeliveryStatus.PENDING) -> NotificationDelivery:
    return NotificationDelivery(
        id=uuid4(),
        notification_id=uuid4(),
        channel=DeliveryChannel.EMAIL,
        status=status,
    )


def test_schedule_sets_scheduled_for_and_delivery_window() -> None:
    delivery = _make_delivery()
    scheduled_for = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    delivery.schedule(scheduled_for, delivery_window="daily")
    assert delivery.status == DeliveryStatus.SCHEDULED
    assert delivery.scheduled_for == scheduled_for
    assert delivery.delivery_window == "daily"
    assert delivery.updated_at is not None


def test_claim_sets_claimed_at_and_transitions_from_scheduled() -> None:
    delivery = _make_delivery(DeliveryStatus.SCHEDULED)
    before = datetime.now(UTC)
    delivery.claim()
    assert delivery.claimed_at >= before
    assert delivery.status == DeliveryStatus.SCHEDULED


def test_claim_raises_for_non_scheduled_status() -> None:
    delivery = _make_delivery(DeliveryStatus.PENDING)
    with pytest.raises(ValueError, match="expected scheduled"):
        delivery.claim()


def test_start_processing_sets_processing_started_at_and_transitions() -> None:
    delivery = _make_delivery(DeliveryStatus.SCHEDULED)
    before = datetime.now(UTC)
    delivery.start_processing()
    assert delivery.status == DeliveryStatus.PROCESSING
    assert delivery.processing_started_at >= before
    assert delivery.attempt_count == 1
    assert delivery.last_attempt_at is not None


def test_mark_sent_sets_provider_message_id() -> None:
    delivery = _make_delivery(DeliveryStatus.PROCESSING)
    delivery.mark_sent(provider_message_id="msg-123")
    assert delivery.status == DeliveryStatus.SENT
    assert delivery.provider_message_id == "msg-123"
    assert delivery.attempt_count == 1


def test_mark_sent_without_provider_message_id() -> None:
    delivery = _make_delivery(DeliveryStatus.PROCESSING)
    delivery.mark_sent()
    assert delivery.status == DeliveryStatus.SENT
    assert delivery.provider_message_id is None


def test_mark_delivered_sets_delivered_at() -> None:
    delivery = _make_delivery(DeliveryStatus.SENT)
    before = datetime.now(UTC)
    delivery.mark_delivered()
    assert delivery.status == DeliveryStatus.DELIVERED
    assert delivery.delivered_at >= before


def test_mark_retryable_failure_sets_next_attempt_at() -> None:
    delivery = _make_delivery(DeliveryStatus.PROCESSING)
    next_attempt = datetime(2026, 1, 2, tzinfo=UTC)
    delivery.mark_retryable_failure("timeout", next_attempt)
    assert delivery.status == DeliveryStatus.RETRYABLE_FAILURE
    assert delivery.failure_reason == "timeout"
    assert delivery.next_attempt_at == next_attempt
    assert delivery.attempt_count == 1


def test_mark_permanent_failure_sets_failure_reason() -> None:
    delivery = _make_delivery(DeliveryStatus.RETRYABLE_FAILURE)
    delivery.mark_permanent_failure("invalid_recipient")
    assert delivery.status == DeliveryStatus.PERMANENT_FAILURE
    assert delivery.failure_reason == "invalid_recipient"
    assert delivery.attempt_count == 1


def test_mark_deferred_sets_next_attempt_at() -> None:
    delivery = _make_delivery(DeliveryStatus.PROCESSING)
    next_attempt = datetime(2026, 1, 2, tzinfo=UTC)
    delivery.mark_deferred("quiet_hours", next_attempt)
    assert delivery.status == DeliveryStatus.DEFERRED
    assert delivery.failure_reason == "quiet_hours"
    assert delivery.next_attempt_at == next_attempt


def test_mark_suppressed_sets_suppression_reason() -> None:
    delivery = _make_delivery(DeliveryStatus.PENDING)
    delivery.mark_suppressed("daily_cap_reached")
    assert delivery.status == DeliveryStatus.SUPPRESSED
    assert delivery.suppression_reason == "daily_cap_reached"


def test_mark_expired_sets_status() -> None:
    delivery = _make_delivery(DeliveryStatus.SCHEDULED)
    delivery.mark_expired()
    assert delivery.status == DeliveryStatus.EXPIRED


def test_cancel_sets_status() -> None:
    delivery = _make_delivery(DeliveryStatus.SCHEDULED)
    delivery.cancel()
    assert delivery.status == DeliveryStatus.CANCELLED


@pytest.mark.parametrize(
    "from_status,to_status",
    [
        (DeliveryStatus.DELIVERED, DeliveryStatus.PENDING),
        (DeliveryStatus.PERMANENT_FAILURE, DeliveryStatus.SENT),
        (DeliveryStatus.BOUNCED, DeliveryStatus.PROCESSING),
        (DeliveryStatus.SUPPRESSED, DeliveryStatus.SCHEDULED),
        (DeliveryStatus.EXPIRED, DeliveryStatus.RETRYABLE_FAILURE),
        (DeliveryStatus.CANCELLED, DeliveryStatus.SENT),
    ],
)
def test_invalid_state_transitions_raise_value_error(from_status: DeliveryStatus, to_status: DeliveryStatus) -> None:
    delivery = _make_delivery(from_status)
    with pytest.raises(ValueError, match="Invalid delivery status transition"):
        delivery._validate_transition(to_status)


def test_state_transition_idempotent_when_already_in_target_status() -> None:
    delivery = _make_delivery(DeliveryStatus.SENT)
    delivery.mark_sent(provider_message_id="msg-1")
    first_message_id = delivery.provider_message_id
    delivery.mark_sent(provider_message_id="msg-2")
    assert delivery.provider_message_id == "msg-2"
    assert delivery.attempt_count == 2


def test_schedule_from_pending_transitions() -> None:
    delivery = _make_delivery(DeliveryStatus.PENDING)
    delivery.schedule(datetime.now(UTC))
    assert delivery.status == DeliveryStatus.SCHEDULED


def test_create_with_scheduled_for_sets_initial_status() -> None:
    scheduled_for = datetime(2026, 1, 1, tzinfo=UTC)
    delivery = NotificationDelivery.create(
        notification_id=uuid4(),
        channel=DeliveryChannel.EMAIL,
        scheduled_for=scheduled_for,
    )
    assert delivery.status == DeliveryStatus.SCHEDULED
    assert delivery.scheduled_for == scheduled_for


def test_create_without_scheduled_for_sets_pending() -> None:
    delivery = NotificationDelivery.create(
        notification_id=uuid4(),
        channel=DeliveryChannel.EMAIL,
    )
    assert delivery.status == DeliveryStatus.PENDING
    assert delivery.scheduled_for is None


__all__ = [
    "test_cancel_sets_status",
    "test_claim_raises_for_non_scheduled_status",
    "test_claim_sets_claimed_at_and_transitions_from_scheduled",
    "test_create_with_scheduled_for_sets_initial_status",
    "test_create_without_scheduled_for_sets_pending",
    "test_invalid_state_transitions_raise_value_error",
    "test_mark_delivered_sets_delivered_at",
    "test_mark_deferred_sets_next_attempt_at",
    "test_mark_expired_sets_status",
    "test_mark_permanent_failure_sets_failure_reason",
    "test_mark_retryable_failure_sets_next_attempt_at",
    "test_mark_sent_sets_provider_message_id",
    "test_mark_sent_without_provider_message_id",
    "test_mark_suppressed_sets_suppression_reason",
    "test_schedule_from_pending_transitions",
    "test_schedule_sets_scheduled_for_and_delivery_window",
    "test_start_processing_sets_processing_started_at_and_transitions",
    "test_state_transition_idempotent_when_already_in_target_status",
]
