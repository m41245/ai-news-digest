from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class NotificationResponse(BaseModel):
    id: str
    user_id: str
    notification_type: str
    title: str
    body: str
    severity: str
    story_id: str | None = None
    article_id: str | None = None
    company_id: str | None = None
    topic_id: str | None = None
    digest_id: str | None = None
    metadata: dict[str, Any] | None = None
    created_at: str | None = None
    read_at: str | None = None
    dismissed_at: str | None = None
    expires_at: str | None = None


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    total: int
    limit: int
    offset: int


class UnreadCountResponse(BaseModel):
    unread_count: int


class NotificationPreferenceResponse(BaseModel):
    user_id: str
    in_app_enabled: bool = True
    email_enabled: bool = False
    immediate_enabled: bool = True
    daily_digest_enabled: bool = True
    weekly_digest_enabled: bool = False
    min_importance: float = 0.0
    min_confidence: float = 0.0
    notify_followed_companies: bool = True
    notify_followed_topics: bool = True
    notify_corrections: bool = True
    notify_story_evolution: bool = True
    quiet_hours_start: str | None = None
    quiet_hours_end: str | None = None
    timezone: str = "UTC"
    max_per_day: int = 10


class NotificationPreferenceUpdateRequest(BaseModel):
    in_app_enabled: bool | None = None
    email_enabled: bool | None = None
    immediate_enabled: bool | None = None
    daily_digest_enabled: bool | None = None
    weekly_digest_enabled: bool | None = None
    min_importance: float | None = Field(default=None, ge=0.0, le=1.0)
    min_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    notify_followed_companies: bool | None = None
    notify_followed_topics: bool | None = None
    notify_corrections: bool | None = None
    notify_story_evolution: bool | None = None
    quiet_hours_start: str | None = None
    quiet_hours_end: str | None = None
    timezone: str | None = None
    max_per_day: int | None = Field(default=None, ge=1, le=100)


class UnsubscribeResponse(BaseModel):
    success: bool
    message: str


class NotificationDeliveryResponse(BaseModel):
    id: str
    notification_id: str
    channel: str
    status: str
    provider_message_id: str | None = None
    attempt_count: int = 0
    last_attempt_at: str | None = None
    delivered_at: str | None = None
    failure_reason: str | None = None
    created_at: str | None = None
    scheduled_for: str | None = None
    next_attempt_at: str | None = None
    delivery_window: str | None = None
    suppression_reason: str | None = None


class NotificationDeliveryHistoryResponse(BaseModel):
    items: list[NotificationDeliveryResponse]
    total: int
    limit: int
    offset: int


class NotificationStatsResponse(BaseModel):
    total: int
    unread: int
    by_type: dict[str, int]
    by_severity: dict[str, int]
    deliveries_pending: int
    deliveries_sent: int
    deliveries_failed: int


class SchedulePreviewResponse(BaseModel):
    scheduled: list[NotificationDeliveryResponse]
    count: int


class TestNotificationRequest(BaseModel):
    notification_type: str = Field(
        default="system",
        description="Type of notification to send.",
    )
    title: str = Field(
        min_length=1,
        max_length=500,
        description="Notification title.",
    )
    body: str = Field(
        min_length=1,
        max_length=2000,
        description="Notification body.",
    )
    severity: str = Field(
        default="info",
        description="Notification severity level.",
    )


__all__ = [
    "NotificationDeliveryHistoryResponse",
    "NotificationDeliveryResponse",
    "NotificationListResponse",
    "NotificationPreferenceResponse",
    "NotificationPreferenceUpdateRequest",
    "NotificationResponse",
    "NotificationStatsResponse",
    "SchedulePreviewResponse",
    "TestNotificationRequest",
    "UnreadCountResponse",
    "UnsubscribeResponse",
]
