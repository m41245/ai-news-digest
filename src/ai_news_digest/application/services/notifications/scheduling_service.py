from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from uuid import UUID

from ai_news_digest.core.config import get_settings
from ai_news_digest.core.logging import get_logger
from ai_news_digest.domain.enums.notification import (
    DeliveryChannel,
    NotificationType,
)
from ai_news_digest.domain.models.notification import Notification, NotificationDelivery
from ai_news_digest.domain.models.notification_preference import NotificationPreference
from ai_news_digest.domain.ports.notification_repository import (
    NotificationDeliveryRepository,
    NotificationPreferenceRepository,
    NotificationRepository,
)
from ai_news_digest.infrastructure.email.development_sender import ConsoleEmailSender
from ai_news_digest.infrastructure.email.provider_factory import create_email_sender

logger = get_logger(__name__)
settings = get_settings()

_BATCH_SIZE = 50


class NotificationSchedulingService:
    """Creates delivery records and schedules digest-ready notifications."""

    def __init__(
        self,
        notification_repo: NotificationRepository,
        delivery_repo: NotificationDeliveryRepository,
        preference_repo: NotificationPreferenceRepository,
    ) -> None:
        self._notification_repo = notification_repo
        self._delivery_repo = delivery_repo
        self._preference_repo = preference_repo

    def _generate_idempotency_key(
        self,
        notification_id: UUID,
        channel: str,
        window: str | None = None,
    ) -> str:
        raw = f"{notification_id}:{channel}:{window or 'immediate'}"
        return hashlib.sha256(raw.encode()).hexdigest()[:64]

    async def schedule_notification(
        self,
        notification: Notification,
        preference: NotificationPreference | None = None,
    ) -> list[NotificationDelivery]:
        deliveries: list[NotificationDelivery] = []

        in_app_delivery = NotificationDelivery.create(
            notification_id=notification.id,
            channel=DeliveryChannel.IN_APP,
        )
        deliveries.append(await self._delivery_repo.create(in_app_delivery))

        if preference is None:
            preference = await self._preference_repo.get_by_user_id(notification.user_id)
        if preference is None:
            preference = NotificationPreference.create_default(notification.user_id)

        if not preference.email_enabled:
            return deliveries

        email_sender = create_email_sender()
        if isinstance(email_sender, ConsoleEmailSender) and not settings.email_enabled:
            return deliveries

        notification_type = notification.notification_type

        if notification_type == NotificationType.DIGEST_READY:
            window = self._resolve_digest_window(preference)
            if window is None:
                logger.debug(
                    "No digest window configured for user; suppressing email delivery",
                    user_id=str(notification.user_id),
                )
                suppressed = NotificationDelivery.create(
                    notification_id=notification.id,
                    channel=DeliveryChannel.EMAIL,
                )
                suppressed.mark_suppressed("no_digest_window_configured")
                deliveries.append(await self._delivery_repo.create(suppressed))
                return deliveries

            scheduled_for = self._compute_scheduled_time(window, preference)
            if self._is_in_quiet_hours(scheduled_for, preference):
                scheduled_for = self._next_after_quiet_hours(scheduled_for, preference)

            idempotency_key = self._generate_idempotency_key(
                notification.id, "email", window
            )
            email_delivery = NotificationDelivery.create(
                notification_id=notification.id,
                channel=DeliveryChannel.EMAIL,
                provider_idempotency_key=idempotency_key,
                delivery_window=window,
                scheduled_for=scheduled_for,
            )
            deliveries.append(await self._delivery_repo.create(email_delivery))
        else:
            immediate_allowed = preference.immediate_enabled
            if not immediate_allowed:
                logger.debug(
                    "Immediate email disabled for user; skipping",
                    user_id=str(notification.user_id),
                )
                return deliveries

            if self._is_in_quiet_hours(datetime.now(UTC), preference):
                defer_until = self._next_after_quiet_hours(datetime.now(UTC), preference)
                idempotency_key = self._generate_idempotency_key(notification.id, "email")
                deferred = NotificationDelivery.create(
                    notification_id=notification.id,
                    channel=DeliveryChannel.EMAIL,
                    provider_idempotency_key=idempotency_key,
                )
                deferred.mark_deferred("quiet_hours", defer_until)
                deliveries.append(await self._delivery_repo.create(deferred))
                return deliveries

            pending_count = await self._delivery_repo.count_pending_since(
                notification.user_id,
                datetime.now(UTC) - timedelta(hours=24),
            )
            if pending_count >= preference.max_per_day:
                logger.info(
                    "Daily cap reached for user; suppressing email delivery",
                    user_id=str(notification.user_id),
                    pending=pending_count,
                    max=preference.max_per_day,
                )
                suppressed = NotificationDelivery.create(
                    notification_id=notification.id,
                    channel=DeliveryChannel.EMAIL,
                )
                suppressed.mark_suppressed("daily_cap_reached")
                deliveries.append(await self._delivery_repo.create(suppressed))
                return deliveries

            idempotency_key = self._generate_idempotency_key(notification.id, "email")
            email_delivery = NotificationDelivery.create(
                notification_id=notification.id,
                channel=DeliveryChannel.EMAIL,
                provider_idempotency_key=idempotency_key,
            )
            deliveries.append(await self._delivery_repo.create(email_delivery))

        return deliveries

    async def batch_schedule_pending(self, limit: int = _BATCH_SIZE) -> dict[str, int]:
        scheduled = 0
        offset = 0
        while scheduled < limit:
            notifications_page, _ = await self._notification_repo.list_for_user(
                user_id=UUID(int=0),
                limit=min(_BATCH_SIZE, limit - scheduled),
                offset=offset,
            )
            if not notifications_page:
                break
            for notification in notifications_page:
                existing_deliveries = (
                    await self._delivery_repo.list_pending(limit=10)
                )
                has_delivery = any(
                    d.notification_id == notification.id for d in existing_deliveries
                )
                if not has_delivery:
                    await self.schedule_notification(notification)
                    scheduled += 1
                    if scheduled >= limit:
                        break
            offset += len(notifications_page)
            if len(notifications_page) < _BATCH_SIZE:
                break
        return {"scheduled": scheduled}

    def _resolve_digest_window(self, preference: NotificationPreference) -> str | None:
        if preference.daily_digest_enabled:
            return "daily"
        if preference.weekly_digest_enabled:
            return "weekly"
        return None

    def _compute_scheduled_time(
        self,
        window: str,
        preference: NotificationPreference,
    ) -> datetime:
        from contextlib import suppress
        from datetime import tzinfo
        from zoneinfo import ZoneInfo

        tz_name = preference.timezone or "UTC"
        tz: tzinfo = UTC
        with suppress(Exception):
            tz = ZoneInfo(tz_name)

        now = datetime.now(tz)
        if window == "daily":
            scheduled = now.replace(
                hour=settings.digest_schedule_hour,
                minute=settings.digest_schedule_minute,
                second=0,
                microsecond=0,
            )
            if scheduled <= now:
                scheduled += timedelta(days=1)
        elif window == "weekly":
            days_until_monday = (7 - now.weekday()) % 7
            if days_until_monday == 0:
                days_until_monday = 7
            scheduled = now + timedelta(days=days_until_monday)
            scheduled = scheduled.replace(
                hour=settings.digest_schedule_hour,
                minute=settings.digest_schedule_minute,
                second=0,
                microsecond=0,
            )
        else:
            scheduled = now + timedelta(hours=1)

        return scheduled.astimezone(UTC)

    def _is_in_quiet_hours(
        self,
        dt: datetime,
        preference: NotificationPreference,
    ) -> bool:
        if not preference.quiet_hours_start or not preference.quiet_hours_end:
            return False
        try:
            tz_name = preference.timezone or "UTC"
            from zoneinfo import ZoneInfo
            local_dt = dt.astimezone(ZoneInfo(tz_name))
            current_minutes = local_dt.hour * 60 + local_dt.minute
            start_parts = preference.quiet_hours_start.split(":")
            end_parts = preference.quiet_hours_end.split(":")
            start_minutes = int(start_parts[0]) * 60 + int(start_parts[1])
            end_minutes = int(end_parts[0]) * 60 + int(end_parts[1])
            if start_minutes <= end_minutes:
                return start_minutes <= current_minutes < end_minutes
            return current_minutes >= start_minutes or current_minutes < end_minutes
        except Exception:
            return False

    def _next_after_quiet_hours(
        self,
        dt: datetime,
        preference: NotificationPreference,
    ) -> datetime:
        try:
            tz_name = preference.timezone or "UTC"
            from zoneinfo import ZoneInfo
            tz = ZoneInfo(tz_name)
            local_dt = dt.astimezone(tz)
            end = preference.quiet_hours_end
            if end is None:
                return dt + timedelta(hours=1)
            end_parts = end.split(":")
            end_minutes = int(end_parts[0]) * 60 + int(end_parts[1])
            candidate = local_dt.replace(
                hour=end_minutes // 60,
                minute=end_minutes % 60,
                second=0,
                microsecond=0,
            )
            if candidate <= local_dt:
                candidate += timedelta(days=1)
            return candidate.astimezone(UTC)
        except Exception:
            return dt + timedelta(hours=1)


__all__ = ["NotificationSchedulingService"]
