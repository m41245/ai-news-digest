from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from ai_news_digest.core.logging import get_logger
from ai_news_digest.domain.enums.notification import DeliveryStatus, NotificationType
from ai_news_digest.domain.models.notification import Notification, NotificationDelivery
from ai_news_digest.domain.ports.notification_repository import (
    NotificationDeliveryRepository,
    NotificationPreferenceRepository,
    NotificationRepository,
)

logger = get_logger(__name__)

_MAX_DIGEST_ITEMS = 50
_DEDUP_WINDOW_HOURS = 24
_SEVERITY_SORT_ORDER: dict[str, int] = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
    "info": 4,
}


class DigestBatchingService:
    """Groups eligible notifications by user and delivery window for digest generation."""

    def __init__(
        self,
        notification_repo: NotificationRepository,
        delivery_repo: NotificationDeliveryRepository,
        preference_repo: NotificationPreferenceRepository,
    ) -> None:
        self._notification_repo = notification_repo
        self._delivery_repo = delivery_repo
        self._preference_repo = preference_repo

    async def group_for_digest(
        self,
        window: str,
        limit: int = _MAX_DIGEST_ITEMS,
    ) -> dict[UUID, list[NotificationDelivery]]:
        now = datetime.now(UTC)

        scheduled_deliveries = await self._delivery_repo.list_scheduled(
            limit=limit * 10,
            before=now,
        )

        user_batches: dict[UUID, list[NotificationDelivery]] = {}
        for delivery in scheduled_deliveries:
            if delivery.delivery_window != window:
                continue
            if delivery.status != DeliveryStatus.SCHEDULED:
                continue
            if delivery.scheduled_for is None or delivery.scheduled_for > now:
                continue
            if delivery.suppression_reason is not None:
                continue
            notification = await self._notification_repo.get_by_id(delivery.notification_id)
            if notification is None:
                continue
            user_batches.setdefault(notification.user_id, []).append(delivery)

        grouped: dict[UUID, list[NotificationDelivery]] = {}
        for deliveries in user_batches.values():
            notification = await self._notification_repo.get_by_id(deliveries[0].notification_id)
            if notification is None:
                continue
            if notification.notification_type != NotificationType.DIGEST_READY:
                continue
            user_id = notification.user_id
            grouped.setdefault(user_id, []).extend(deliveries)

        result: dict[UUID, list[NotificationDelivery]] = {}
        for user_id, deliveries in grouped.items():
            seen_keys: set[str] = set()
            deduped: list[tuple[NotificationDelivery, Notification]] = []
            for delivery in deliveries:
                dedup_key = f"{delivery.notification_id}:{delivery.channel.value}"
                if dedup_key in seen_keys:
                    continue
                seen_keys.add(dedup_key)
                notification = await self._notification_repo.get_by_id(delivery.notification_id)
                if notification is None:
                    continue
                deduped.append((delivery, notification))
                if len(deduped) >= limit:
                    break

            if deduped:
                deduped.sort(key=lambda pair: _SEVERITY_SORT_ORDER.get(pair[1].severity.value, 99))
                result[user_id] = [pair[0] for pair in deduped]

        return result

    async def get_digest_items_for_user(
        self,
        user_id: UUID,
        window: str,
        limit: int = _MAX_DIGEST_ITEMS,
    ) -> list[dict[str, Any]]:
        notifications, _ = await self._notification_repo.list_for_user(
            user_id=user_id,
            limit=limit * 2,
        )
        items: list[dict[str, Any]] = []
        for notification in notifications:
            if notification.notification_type != NotificationType.DIGEST_READY:
                continue
            item: dict[str, Any] = {
                "notification_id": str(notification.id),
                "title": notification.title,
                "body": notification.body,
                "severity": notification.severity.value,
                "category": self._infer_category(notification),
                "importance_score": self._severity_to_score(notification.severity),
                "created_at": (
                    notification.created_at.isoformat()
                    if notification.created_at
                    else None
                ),
            }
            if notification.story_id:
                item["story_id"] = str(notification.story_id)
            if notification.metadata:
                meta_keys = {"source_name", "url", "summary"}
                item.update(
                    {k: v for k, v in notification.metadata.items() if k in meta_keys}
                )
            items.append(item)

        items.sort(key=lambda x: x.get("importance_score", 0), reverse=True)
        return items[:limit]

    def _infer_category(self, notification: Notification) -> str:
        metadata = notification.metadata or {}
        category = metadata.get("category")
        if category:
            return str(category)
        type_map = {
            NotificationType.FOLLOWED_COMPANY_UPDATE: "Companies",
            NotificationType.FOLLOWED_TOPIC_UPDATE: "Topics",
            NotificationType.STORY_EVOLUTION: "Evolving Stories",
            NotificationType.CONTRADICTION_DETECTED: "Contradictions",
            NotificationType.CORRECTION_PUBLISHED: "Corrections",
            NotificationType.IMPORTANT_STORY: "Important Stories",
            NotificationType.SYSTEM: "System",
        }
        return type_map.get(notification.notification_type, "Other")

    def _severity_to_score(self, severity: Any) -> float:
        scores = {
            "critical": 1.0,
            "high": 0.8,
            "medium": 0.6,
            "low": 0.4,
            "info": 0.2,
        }
        raw_severity = (
            severity.value.lower()
            if hasattr(severity, "value")
            else str(severity).lower()
        )
        return scores.get(raw_severity, 0.0)


__all__ = ["DigestBatchingService"]
