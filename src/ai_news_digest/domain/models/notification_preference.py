from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID


@dataclass(slots=True)
class NotificationPreference:
    """Represents a user's notification preferences."""

    user_id: UUID
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
    unsubscribe_token: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def touch(self) -> None:
        self.updated_at = datetime.now(UTC)

    @classmethod
    def create_default(cls, user_id: UUID) -> NotificationPreference:
        return cls(user_id=user_id)


__all__ = ["NotificationPreference"]
