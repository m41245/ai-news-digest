from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from ai_news_digest.application.services.notifications.eligibility_engine import (  # type: ignore[import-untyped]
    NotificationEligibilityEngine,
)
from ai_news_digest.core.logging import get_logger
from ai_news_digest.domain.enums.notification import (
    NotificationSeverity,
    NotificationType,
)
from ai_news_digest.domain.models.notification import Notification, NotificationDelivery
from ai_news_digest.domain.models.notification_preference import NotificationPreference
from ai_news_digest.domain.models.story_cluster import StoryCluster
from ai_news_digest.domain.models.user import User
from ai_news_digest.domain.ports.notification_repository import (
    NotificationDeliveryRepository,
    NotificationPreferenceRepository,
    NotificationRepository,
)

logger = get_logger(__name__)


class NotificationService:
    """
    Service for creating and managing notifications with deduplication.
    """

    def __init__(
        self,
        notification_repository: NotificationRepository,
        delivery_repository: NotificationDeliveryRepository,
        preference_repository: NotificationPreferenceRepository,
        eligibility_engine: NotificationEligibilityEngine,
        email_composer: Any = None,
    ) -> None:
        self._notification_repo = notification_repository
        self._delivery_repo = delivery_repository
        self._preference_repo = preference_repository
        self._eligibility_engine = eligibility_engine
        self._email_composer = email_composer

    async def create_notification(
        self,
        user: User,
        notification_type: NotificationType,
        title: str,
        body: str,
        severity: NotificationSeverity,
        story: StoryCluster | None = None,
        article_id: UUID | None = None,
        company_id: UUID | None = None,
        topic_id: UUID | None = None,
        digest_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
        ttl_days: int = 30,
    ) -> Notification | None:
        """
        Create a notification idempotently. Returns None if suppressed.
        """
        dedup_key = self._eligibility_engine.build_deduplication_key(
            user_id=user.id,
            notification_type=notification_type,
            story_id=story.id if story else None,
            article_id=article_id,
            company_id=company_id,
            topic_id=topic_id,
            digest_id=digest_id,
        )

        existing = await self._notification_repo.get_by_deduplication_key(user.id, dedup_key)
        if existing is not None:
            logger.debug(
                "Notification deduplicated",
                user_id=str(user.id),
                dedup_key=dedup_key,
            )
            return existing

        eligible, reason, eval_metadata = await self._eligibility_engine.evaluate_story(
            user=user,
            story=story,
            notification_type=notification_type,
            article_id=article_id,
            company_id=company_id,
            topic_id=topic_id,
        )
        if not eligible:
            logger.debug(
                "Notification suppressed",
                user_id=str(user.id),
                reason=reason,
                notification_type=notification_type.value,
            )
            return None

        combined_metadata = {**(eval_metadata or {}), **(metadata or {})}
        expires_at = datetime.now(UTC) + timedelta(days=ttl_days)

        notification = Notification.create(
            user_id=user.id,
            notification_type=notification_type,
            title=title,
            body=body,
            severity=severity,
            story_id=story.id if story else None,
            article_id=article_id,
            company_id=company_id,
            topic_id=topic_id,
            digest_id=digest_id,
            metadata=combined_metadata,
            deduplication_key=dedup_key,
            expires_at=expires_at,
        )

        created = await self._notification_repo.create(notification)
        logger.info(
            "Notification created",
            notification_id=str(created.id),
            user_id=str(user.id),
            type=notification_type.value,
            severity=severity.value,
        )

        await self._create_delivery(created, "in_app")

        pref = await self._preference_repo.get_by_user_id(user.id)
        if pref is None:
            pref = NotificationPreference.create_default(user.id)
        if pref.email_enabled and pref.immediate_enabled:
            await self._create_delivery(created, "email")

        return created

    async def _create_delivery(
        self,
        notification: Notification,
        channel: str,
    ) -> NotificationDelivery:
        from ai_news_digest.domain.enums.notification import DeliveryChannel

        delivery = NotificationDelivery.create(
            notification_id=notification.id,
            channel=DeliveryChannel(channel),
        )
        return await self._delivery_repo.create(delivery)

    async def ensure_default_preferences(self, user_id: UUID) -> NotificationPreference:
        pref = await self._preference_repo.get_by_user_id(user_id)
        if pref is None:
            pref = NotificationPreference.create_default(user_id)
            pref.unsubscribe_token = secrets.token_urlsafe(32)
            await self._preference_repo.create(pref)
        return pref

    async def get_notification(
        self,
        notification_id: UUID,
        user_id: UUID,
    ) -> Notification | None:
        notification = await self._notification_repo.get_by_id(notification_id)
        if notification is None or notification.user_id != user_id:
            return None
        return notification

    async def mark_read(
        self,
        notification_id: UUID,
        user_id: UUID,
    ) -> Notification | None:
        return await self._notification_repo.mark_read(notification_id, user_id)

    async def mark_all_read(self, user_id: UUID) -> int:
        return await self._notification_repo.mark_all_read(user_id)

    async def dismiss(
        self,
        notification_id: UUID,
        user_id: UUID,
    ) -> Notification | None:
        return await self._notification_repo.dismiss(notification_id, user_id)

    async def get_unread_count(self, user_id: UUID) -> int:
        return await self._notification_repo.count_unread(user_id)

    async def list_notifications(
        self,
        user_id: UUID,
        limit: int = 20,
        offset: int = 0,
        unread_only: bool = False,
        notification_type: str | None = None,
    ) -> tuple[list[Notification], int]:
        return await self._notification_repo.list_for_user(
            user_id,
            limit=limit,
            offset=offset,
            unread_only=unread_only,
            notification_type=notification_type,
        )

    async def update_preferences(
        self,
        user_id: UUID,
        updates: dict[str, Any],
    ) -> NotificationPreference:
        pref = await self._preference_repo.get_by_user_id(user_id)
        if pref is None:
            pref = NotificationPreference.create_default(user_id)
            pref.unsubscribe_token = secrets.token_urlsafe(32)

        for key, value in updates.items():
            if hasattr(pref, key):
                setattr(pref, key, value)
        pref.touch()

        if pref.unsubscribe_token is None:
            pref.unsubscribe_token = secrets.token_urlsafe(32)

        saved = await self._preference_repo.update(pref)
        return saved

    async def reset_preferences(self, user_id: UUID) -> NotificationPreference:
        await self._preference_repo.delete_by_user_id(user_id)
        pref = NotificationPreference.create_default(user_id)
        pref.unsubscribe_token = secrets.token_urlsafe(32)
        return await self._preference_repo.create(pref)

    async def unsubscribe_email(self, token: str) -> bool:
        pref = await self._preference_repo.get_by_unsubscribe_token(token)
        if pref is None:
            return False
        pref.email_enabled = False
        pref.touch()
        await self._preference_repo.update(pref)
        return True


__all__ = ["NotificationService"]
