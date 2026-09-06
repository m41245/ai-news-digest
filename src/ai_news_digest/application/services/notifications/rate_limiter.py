from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from ai_news_digest.core.config import get_settings
from ai_news_digest.core.logging import get_logger
from ai_news_digest.domain.ports.notification_repository import NotificationDeliveryRepository

logger = get_logger(__name__)
settings = get_settings()


class NotificationRateLimiter:
    """Enforces per-user and global rate limits for notifications."""

    def __init__(self, delivery_repo: NotificationDeliveryRepository) -> None:
        self._delivery_repo = delivery_repo

    async def check_and_record(
        self,
        user_id: UUID,
        channel: str,
    ) -> tuple[bool, str | None]:
        now = datetime.now(UTC)
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        count = await self._delivery_repo.count_pending_since(user_id, day_start)

        max_per_day = getattr(settings, "notification_max_per_day", 100)
        global_limit = getattr(settings, "email_rate_limit", 100)

        if channel == "email" and count >= max_per_day:
            return False, "user_daily_email_cap_reached"

        if count >= global_limit:
            return False, "global_rate_limit_exceeded"

        return True, None

    async def get_user_daily_email_count(self, user_id: UUID) -> int:
        day_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        return await self._delivery_repo.count_pending_since(user_id, day_start)

    async def get_user_daily_notification_count(self, user_id: UUID) -> int:
        return await self.get_user_daily_email_count(user_id)

    async def get_user_daily_digest_count(self, user_id: UUID) -> int:
        day_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        count = await self._delivery_repo.count_pending_since(user_id, day_start)
        return count


__all__ = ["NotificationRateLimiter"]
