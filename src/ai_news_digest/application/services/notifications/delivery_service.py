from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from ai_news_digest.core.config import get_settings
from ai_news_digest.core.logging import get_logger
from ai_news_digest.domain.enums.notification import (
    DeliveryChannel,
    DeliveryStatus,
    NotificationType,
)
from ai_news_digest.domain.models.notification import NotificationDelivery
from ai_news_digest.domain.ports.notification_repository import NotificationDeliveryRepository
from ai_news_digest.infrastructure.email.errors import (
    EmailConnectionError,
    EmailInvalidRecipientError,
    EmailPermanentFailureError,
    EmailTimeoutError,
)
from ai_news_digest.infrastructure.email.provider_factory import create_email_sender

logger = get_logger(__name__)
settings = get_settings()

_MAX_RETRIES = 3
_BACKOFF_BASE = 60


class NotificationDeliveryService:
    """Processes pending, scheduled, and retryable notification deliveries."""

    def __init__(
        self,
        delivery_repo: NotificationDeliveryRepository,
        notification_repo: Any | None = None,
        user_repo: Any | None = None,
    ) -> None:
        self._delivery_repo = delivery_repo
        self._notification_repo = notification_repo
        self._user_repo = user_repo
        self._sender = create_email_sender()

    async def process_scheduled_deliveries(self, limit: int = 50) -> dict[str, int]:
        now = datetime.now(UTC)
        scheduled = await self._delivery_repo.list_scheduled(limit=limit, before=now)
        processed = 0
        failed = 0
        for delivery in scheduled:
            try:
                await self._process_single_delivery(delivery)
                processed += 1
            except Exception as exc:
                logger.error(
                    "Scheduled delivery processing failed",
                    delivery_id=str(delivery.id),
                    error=str(exc),
                )
                failed += 1
        return {"processed": processed, "failed": failed}

    async def process_immediate_deliveries(self, limit: int = 50) -> dict[str, int]:
        pending = await self._delivery_repo.list_pending(channel="email", limit=limit)
        processed = 0
        failed = 0
        for delivery in pending:
            if delivery.scheduled_for is not None:
                continue
            try:
                await self._process_single_delivery(delivery)
                processed += 1
            except Exception as exc:
                logger.error(
                    "Immediate delivery processing failed",
                    delivery_id=str(delivery.id),
                    error=str(exc),
                )
                failed += 1
        return {"processed": processed, "failed": failed}

    async def retry_failed_deliveries(self, limit: int = 50) -> dict[str, int]:
        retryable = await self._delivery_repo.list_retryable(limit=limit)
        now = datetime.now(UTC)
        ready = [d for d in retryable if d.next_attempt_at is None or d.next_attempt_at <= now]
        retried = 0
        failed = 0
        for delivery in ready:
            try:
                delivery.start_processing()
                await self._delivery_repo.update(delivery)
                await self._send_delivery(delivery)
                delivery.mark_sent()
                await self._delivery_repo.update(delivery)
                retried += 1
            except EmailTimeoutError as exc:
                backoff = _BACKOFF_BASE * (2 ** min(delivery.attempt_count, 5))
                next_attempt = now + timedelta(seconds=backoff)
                delivery.mark_retryable_failure(str(exc), next_attempt)
                await self._delivery_repo.update(delivery)
                retried += 1
            except EmailConnectionError as exc:
                backoff = _BACKOFF_BASE * (2 ** min(delivery.attempt_count, 5))
                next_attempt = now + timedelta(seconds=backoff)
                delivery.mark_retryable_failure(str(exc), next_attempt)
                await self._delivery_repo.update(delivery)
                retried += 1
            except EmailPermanentFailureError as exc:
                delivery.mark_permanent_failure(str(exc))
                await self._delivery_repo.update(delivery)
                failed += 1
            except EmailInvalidRecipientError as exc:
                delivery.mark_permanent_failure(str(exc))
                await self._delivery_repo.update(delivery)
                failed += 1
            except Exception as exc:
                logger.error(
                    "Retry delivery failed",
                    delivery_id=str(delivery.id),
                    error=str(exc),
                )
                backoff = _BACKOFF_BASE * (2 ** min(delivery.attempt_count, 5))
                if delivery.attempt_count >= _MAX_RETRIES:
                    delivery.mark_permanent_failure(str(exc))
                    await self._delivery_repo.update(delivery)
                    failed += 1
                else:
                    next_attempt = now + timedelta(seconds=backoff)
                    delivery.mark_retryable_failure(str(exc), next_attempt)
                    await self._delivery_repo.update(delivery)
                    retried += 1
        return {"retried": retried, "failed": failed}

    async def recover_stuck_deliveries(
        self,
        timeout_minutes: int = 30,
        limit: int = 50,
    ) -> dict[str, int]:
        stuck = await self._delivery_repo.list_stuck_processing(
            timeout_minutes=timeout_minutes,
            limit=limit,
        )
        recovered = 0
        for delivery in stuck:
            next_attempt = datetime.now(UTC) + timedelta(seconds=_BACKOFF_BASE)
            delivery.mark_retryable_failure("stuck_processing_recovered", next_attempt)
            await self._delivery_repo.update(delivery)
            recovered += 1
        return {"recovered": recovered}

    async def _process_single_delivery(self, delivery: NotificationDelivery) -> None:
        if delivery.status == DeliveryStatus.SCHEDULED:
            delivery.claim()
            await self._delivery_repo.update(delivery)

        delivery.start_processing()
        await self._delivery_repo.update(delivery)

        await self._send_delivery(delivery)

        delivery.mark_sent()
        await self._delivery_repo.update(delivery)

    async def _send_delivery(self, delivery: NotificationDelivery) -> None:
        if self._notification_repo is None:
            raise ValueError("Notification repository is required for delivery")
        notification = await self._notification_repo.get_by_id(delivery.notification_id)
        if notification is None:
            raise ValueError(f"Notification {delivery.notification_id} not found")

        from ai_news_digest.infrastructure.email.notification_templates import (
            render_contradiction_detected_email,
            render_correction_published_email,
            render_digest_ready_email,
            render_followed_company_update_email,
            render_followed_topic_update_email,
            render_important_story_email,
            render_story_evolution_email,
            render_system_email,
        )

        base_url = getattr(settings, "email_base_url", "http://localhost:8000")
        app_name = getattr(settings, "app_name", "AI News Digest")

        if delivery.channel == DeliveryChannel.EMAIL:
            user_email = self._get_user_email(notification.user_id)
            if not user_email:
                raise ValueError(f"No email address for user {notification.user_id}")

            template_map = {
                NotificationType.IMPORTANT_STORY: render_important_story_email,
                NotificationType.FOLLOWED_COMPANY_UPDATE: render_followed_company_update_email,
                NotificationType.FOLLOWED_TOPIC_UPDATE: render_followed_topic_update_email,
                NotificationType.STORY_EVOLUTION: render_story_evolution_email,
                NotificationType.CONTRADICTION_DETECTED: render_contradiction_detected_email,
                NotificationType.CORRECTION_PUBLISHED: render_correction_published_email,
                NotificationType.DIGEST_READY: render_digest_ready_email,
                NotificationType.SYSTEM: render_system_email,
            }
            render_fn = template_map.get(
                notification.notification_type,
                render_system_email,
            )
            subject, html_body, text_body = render_fn(
                notification=notification,
                app_name=app_name,
                base_url=base_url,
                unsubscribe_url="",
            )

            await self._sender.send(
                recipient=user_email,
                subject=subject,
                html=html_body,
                text=text_body,
            )
        else:
            logger.info(
                "In-app delivery processed",
                delivery_id=str(delivery.id),
                notification_id=str(delivery.notification_id),
            )

    def _get_user_email(self, user_id: UUID) -> str | None:
        if self._user_repo is None:
            return None
        import asyncio

        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                return None
        except RuntimeError:
            pass
        return None


__all__ = ["NotificationDeliveryService"]
