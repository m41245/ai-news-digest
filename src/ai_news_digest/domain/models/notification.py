from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from ai_news_digest.domain.enums.notification import (
    DeliveryChannel,
    DeliveryStatus,
    NotificationSeverity,
    NotificationType,
)

_VALID_TRANSITIONS: dict[DeliveryStatus, set[DeliveryStatus]] = {
    DeliveryStatus.PENDING: {
        DeliveryStatus.SCHEDULED,
        DeliveryStatus.PROCESSING,
        DeliveryStatus.SENT,
        DeliveryStatus.CANCELLED,
        DeliveryStatus.SUPPRESSED,
        DeliveryStatus.DEFERRED,
    },
    DeliveryStatus.SCHEDULED: {
        DeliveryStatus.PROCESSING,
        DeliveryStatus.CANCELLED,
        DeliveryStatus.EXPIRED,
    },
    DeliveryStatus.PROCESSING: {
        DeliveryStatus.SENT,
        DeliveryStatus.FAILED,
        DeliveryStatus.DEFERRED,
        DeliveryStatus.RETRYABLE_FAILURE,
        DeliveryStatus.PERMANENT_FAILURE,
    },
    DeliveryStatus.DEFERRED: {
        DeliveryStatus.SCHEDULED,
        DeliveryStatus.PROCESSING,
        DeliveryStatus.CANCELLED,
        DeliveryStatus.EXPIRED,
    },
    DeliveryStatus.RETRYABLE_FAILURE: {
        DeliveryStatus.SCHEDULED,
        DeliveryStatus.PROCESSING,
        DeliveryStatus.CANCELLED,
        DeliveryStatus.EXPIRED,
        DeliveryStatus.PERMANENT_FAILURE,
    },
    DeliveryStatus.SENT: {DeliveryStatus.DELIVERED, DeliveryStatus.BOUNCED},
    DeliveryStatus.DELIVERED: set(),
    DeliveryStatus.FAILED: {
        DeliveryStatus.SCHEDULED,
        DeliveryStatus.RETRYABLE_FAILURE,
    },
    DeliveryStatus.BOUNCED: set(),
    DeliveryStatus.SUPPRESSED: set(),
    DeliveryStatus.PERMANENT_FAILURE: set(),
    DeliveryStatus.EXPIRED: set(),
    DeliveryStatus.CANCELLED: set(),
}


@dataclass(slots=True)
class Notification:
    """Represents a single user-facing notification."""

    id: UUID
    user_id: UUID
    notification_type: NotificationType
    title: str
    body: str
    severity: NotificationSeverity
    story_id: UUID | None = None
    article_id: UUID | None = None
    company_id: UUID | None = None
    topic_id: UUID | None = None
    digest_id: UUID | None = None
    metadata: dict[str, Any] | None = None
    deduplication_key: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    read_at: datetime | None = None
    dismissed_at: datetime | None = None
    expires_at: datetime | None = None
    scheduled_for: datetime | None = None

    def mark_read(self) -> None:
        self.read_at = datetime.now(UTC)

    def mark_dismissed(self) -> None:
        self.dismissed_at = datetime.now(UTC)

    def is_read(self) -> bool:
        return self.read_at is not None

    def is_dismissed(self) -> bool:
        return self.dismissed_at is not None

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now(UTC) >= self.expires_at

    @classmethod
    def create(
        cls,
        *,
        user_id: UUID,
        notification_type: NotificationType,
        title: str,
        body: str,
        severity: NotificationSeverity,
        story_id: UUID | None = None,
        article_id: UUID | None = None,
        company_id: UUID | None = None,
        topic_id: UUID | None = None,
        digest_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
        deduplication_key: str = "",
        expires_at: datetime | None = None,
        scheduled_for: datetime | None = None,
    ) -> Notification:
        return cls(
            id=uuid4(),
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            body=body,
            severity=severity,
            story_id=story_id,
            article_id=article_id,
            company_id=company_id,
            topic_id=topic_id,
            digest_id=digest_id,
            metadata=metadata,
            deduplication_key=deduplication_key,
            expires_at=expires_at,
            scheduled_for=scheduled_for,
        )


@dataclass(slots=True)
class NotificationDelivery:
    """Represents a single notification delivery attempt."""

    id: UUID
    notification_id: UUID
    channel: DeliveryChannel
    status: DeliveryStatus
    provider_message_id: str | None = None
    attempt_count: int = 0
    last_attempt_at: datetime | None = None
    delivered_at: datetime | None = None
    failure_reason: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    scheduled_for: datetime | None = None
    claimed_at: datetime | None = None
    processing_started_at: datetime | None = None
    next_attempt_at: datetime | None = None
    provider_idempotency_key: str | None = None
    delivery_window: str | None = None
    suppression_reason: str | None = None

    def _validate_transition(self, new_status: DeliveryStatus) -> None:
        if self.status == new_status:
            return
        allowed = _VALID_TRANSITIONS.get(self.status, set())
        if new_status not in allowed:
            raise ValueError(
                f"Invalid delivery status transition: {self.status.value} -> {new_status.value}"
            )

    def schedule(self, scheduled_for: datetime, delivery_window: str | None = None) -> None:
        self._validate_transition(DeliveryStatus.SCHEDULED)
        self.status = DeliveryStatus.SCHEDULED
        self.scheduled_for = scheduled_for
        self.delivery_window = delivery_window
        self.updated_at = datetime.now(UTC)

    def claim(self) -> None:
        if self.status != DeliveryStatus.SCHEDULED:
            raise ValueError(
                f"Cannot claim delivery in status {self.status.value}; expected scheduled."
            )
        self.claimed_at = datetime.now(UTC)
        self.updated_at = datetime.now(UTC)

    def start_processing(self) -> None:
        self._validate_transition(DeliveryStatus.PROCESSING)
        self.status = DeliveryStatus.PROCESSING
        self.processing_started_at = datetime.now(UTC)
        self.last_attempt_at = datetime.now(UTC)
        self.attempt_count += 1
        self.updated_at = datetime.now(UTC)

    def mark_sent(self, provider_message_id: str | None = None) -> None:
        self._validate_transition(DeliveryStatus.SENT)
        self.status = DeliveryStatus.SENT
        self.provider_message_id = provider_message_id
        self.last_attempt_at = datetime.now(UTC)
        self.attempt_count += 1
        self.updated_at = datetime.now(UTC)

    def mark_delivered(self) -> None:
        self._validate_transition(DeliveryStatus.DELIVERED)
        self.status = DeliveryStatus.DELIVERED
        self.delivered_at = datetime.now(UTC)
        self.last_attempt_at = datetime.now(UTC)
        self.updated_at = datetime.now(UTC)

    def mark_retryable_failure(self, reason: str, next_attempt_at: datetime) -> None:
        self._validate_transition(DeliveryStatus.RETRYABLE_FAILURE)
        self.status = DeliveryStatus.RETRYABLE_FAILURE
        self.failure_reason = reason
        self.next_attempt_at = next_attempt_at
        self.last_attempt_at = datetime.now(UTC)
        self.attempt_count += 1
        self.updated_at = datetime.now(UTC)

    def mark_permanent_failure(self, reason: str) -> None:
        self._validate_transition(DeliveryStatus.PERMANENT_FAILURE)
        self.status = DeliveryStatus.PERMANENT_FAILURE
        self.failure_reason = reason
        self.last_attempt_at = datetime.now(UTC)
        self.attempt_count += 1
        self.updated_at = datetime.now(UTC)

    def mark_deferred(self, reason: str, next_attempt_at: datetime) -> None:
        self._validate_transition(DeliveryStatus.DEFERRED)
        self.status = DeliveryStatus.DEFERRED
        self.failure_reason = reason
        self.next_attempt_at = next_attempt_at
        self.last_attempt_at = datetime.now(UTC)
        self.updated_at = datetime.now(UTC)

    def mark_suppressed(self, reason: str) -> None:
        self._validate_transition(DeliveryStatus.SUPPRESSED)
        self.status = DeliveryStatus.SUPPRESSED
        self.suppression_reason = reason
        self.updated_at = datetime.now(UTC)

    def mark_expired(self) -> None:
        self._validate_transition(DeliveryStatus.EXPIRED)
        self.status = DeliveryStatus.EXPIRED
        self.updated_at = datetime.now(UTC)

    def cancel(self) -> None:
        self._validate_transition(DeliveryStatus.CANCELLED)
        self.status = DeliveryStatus.CANCELLED
        self.updated_at = datetime.now(UTC)

    @classmethod
    def create(
        cls,
        *,
        notification_id: UUID,
        channel: DeliveryChannel,
        provider_idempotency_key: str | None = None,
        delivery_window: str | None = None,
        scheduled_for: datetime | None = None,
    ) -> NotificationDelivery:
        if scheduled_for is not None:
            initial_status = DeliveryStatus.SCHEDULED
        else:
            initial_status = DeliveryStatus.PENDING
        return cls(
            id=uuid4(),
            notification_id=notification_id,
            channel=channel,
            status=initial_status,
            provider_idempotency_key=provider_idempotency_key,
            delivery_window=delivery_window,
            scheduled_for=scheduled_for,
        )


__all__ = ["Notification", "NotificationDelivery"]
