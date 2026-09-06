from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from ai_news_digest.domain.models.notification import Notification, NotificationDelivery
from ai_news_digest.domain.models.notification_preference import NotificationPreference

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID


class NotificationRepository(ABC):
    """Port for persisting and retrieving notifications."""

    @abstractmethod
    async def create(self, notification: Notification) -> Notification:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, notification_id: UUID) -> Notification | None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_deduplication_key(
        self,
        user_id: UUID,
        deduplication_key: str,
    ) -> Notification | None:
        raise NotImplementedError

    @abstractmethod
    async def list_for_user(
        self,
        user_id: UUID,
        limit: int = 20,
        offset: int = 0,
        unread_only: bool = False,
        notification_type: str | None = None,
    ) -> tuple[list[Notification], int]:
        raise NotImplementedError

    @abstractmethod
    async def mark_read(self, notification_id: UUID, user_id: UUID) -> Notification | None:
        raise NotImplementedError

    @abstractmethod
    async def mark_all_read(self, user_id: UUID, before: datetime | None = None) -> int:
        raise NotImplementedError

    @abstractmethod
    async def dismiss(self, notification_id: UUID, user_id: UUID) -> Notification | None:
        raise NotImplementedError

    @abstractmethod
    async def count_unread(self, user_id: UUID) -> int:
        raise NotImplementedError

    @abstractmethod
    async def count_unread_since(self, user_id: UUID, since: datetime) -> int:
        raise NotImplementedError

    @abstractmethod
    async def expire_old(self, before: datetime) -> int:
        raise NotImplementedError

    @abstractmethod
    async def list_old(self, before: datetime, limit: int = 100) -> list[Notification]:
        raise NotImplementedError


class NotificationDeliveryRepository(ABC):
    """Port for persisting and retrieving notification deliveries."""

    @abstractmethod
    async def create(self, delivery: NotificationDelivery) -> NotificationDelivery:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, delivery_id: UUID) -> NotificationDelivery | None:
        raise NotImplementedError

    @abstractmethod
    async def list_pending(
        self,
        channel: str | None = None,
        limit: int = 100,
    ) -> list[NotificationDelivery]:
        raise NotImplementedError

    @abstractmethod
    async def update(self, delivery: NotificationDelivery) -> NotificationDelivery:
        raise NotImplementedError

    @abstractmethod
    async def list_scheduled(
        self,
        limit: int = 100,
        before: datetime | None = None,
    ) -> list[NotificationDelivery]:
        raise NotImplementedError

    @abstractmethod
    async def list_retryable(self, limit: int = 100) -> list[NotificationDelivery]:
        raise NotImplementedError

    @abstractmethod
    async def list_stuck_processing(
        self,
        timeout_minutes: int = 30,
        limit: int = 100,
    ) -> list[NotificationDelivery]:
        raise NotImplementedError

    @abstractmethod
    async def get_by_provider_idempotency_key(
        self,
        key: str,
    ) -> NotificationDelivery | None:
        raise NotImplementedError

    @abstractmethod
    async def count_pending_since(
        self,
        user_id: UUID,
        since: datetime,
    ) -> int:
        raise NotImplementedError


class NotificationPreferenceRepository(ABC):
    """Port for persisting and retrieving notification preferences."""

    @abstractmethod
    async def get_by_user_id(self, user_id: UUID) -> NotificationPreference | None:
        raise NotImplementedError

    @abstractmethod
    async def create(self, preference: NotificationPreference) -> NotificationPreference:
        raise NotImplementedError

    @abstractmethod
    async def update(self, preference: NotificationPreference) -> NotificationPreference:
        raise NotImplementedError

    @abstractmethod
    async def get_by_unsubscribe_token(self, token: str) -> NotificationPreference | None:
        raise NotImplementedError

    @abstractmethod
    async def delete_by_user_id(self, user_id: UUID) -> None:
        raise NotImplementedError


__all__ = [
    "NotificationDeliveryRepository",
    "NotificationPreferenceRepository",
    "NotificationRepository",
]
