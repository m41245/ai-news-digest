from __future__ import annotations

from enum import StrEnum


class NotificationType(StrEnum):
    """Stable notification type taxonomy."""

    IMPORTANT_STORY = "important_story"
    FOLLOWED_COMPANY_UPDATE = "followed_company_update"
    FOLLOWED_TOPIC_UPDATE = "followed_topic_update"
    STORY_EVOLUTION = "story_evolution"
    CONTRADICTION_DETECTED = "contradiction_detected"
    CORRECTION_PUBLISHED = "correction_published"
    DIGEST_READY = "digest_ready"
    SYSTEM = "system"


class NotificationSeverity(StrEnum):
    """Notification severity levels."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DeliveryChannel(StrEnum):
    """Supported notification delivery channels."""

    IN_APP = "in_app"
    EMAIL = "email"


class DeliveryStatus(StrEnum):
    """Notification delivery status."""

    PENDING = "pending"
    SCHEDULED = "scheduled"
    PROCESSING = "processing"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    BOUNCED = "bounced"
    SUPPRESSED = "suppressed"
    DEFERRED = "deferred"
    RETRYABLE_FAILURE = "retryable_failure"
    PERMANENT_FAILURE = "permanent_failure"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


__all__ = [
    "DeliveryChannel",
    "DeliveryStatus",
    "NotificationSeverity",
    "NotificationType",
]
