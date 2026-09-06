from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import and_, delete, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_news_digest.core.exceptions import ResourceNotFoundError
from ai_news_digest.domain.models.notification import Notification, NotificationDelivery
from ai_news_digest.domain.models.notification_preference import NotificationPreference
from ai_news_digest.domain.ports.notification_repository import (
    NotificationDeliveryRepository as NotificationDeliveryRepositoryPort,
)
from ai_news_digest.domain.ports.notification_repository import (
    NotificationPreferenceRepository as NotificationPreferenceRepositoryPort,
)
from ai_news_digest.domain.ports.notification_repository import (
    NotificationRepository as NotificationRepositoryPort,
)
from ai_news_digest.infrastructure.database.mappers.notification_mapper import (
    NotificationDeliveryMapper,
    NotificationMapper,
    NotificationPreferenceMapper,
)
from ai_news_digest.infrastructure.database.models.notification_model import (
    NotificationDeliveryModel,
    NotificationModel,
    NotificationPreferenceModel,
)
from ai_news_digest.infrastructure.database.repositories.base_repository import (
    BaseRepository,
)

if TYPE_CHECKING:
    pass


class NotificationRepository(
    BaseRepository[NotificationModel],
    NotificationRepositoryPort,
):
    """SQLAlchemy implementation of the NotificationRepository port."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def create(self, notification: Notification) -> Notification:
        model = NotificationMapper.to_model(notification)
        model = await self._add_and_refresh(model)
        return NotificationMapper.to_domain(model)

    async def get_by_id(self, notification_id: UUID) -> Notification | None:
        statement = select(NotificationModel).where(
            NotificationModel.id == str(notification_id)
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return NotificationMapper.to_domain(model)

    async def get_by_deduplication_key(
        self,
        user_id: UUID,
        deduplication_key: str,
    ) -> Notification | None:
        statement = select(NotificationModel).where(
            and_(
                NotificationModel.user_id == str(user_id),
                NotificationModel.deduplication_key == deduplication_key,
            )
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return NotificationMapper.to_domain(model)

    async def list_for_user(
        self,
        user_id: UUID,
        limit: int = 20,
        offset: int = 0,
        unread_only: bool = False,
        notification_type: str | None = None,
    ) -> tuple[list[Notification], int]:
        statement = select(NotificationModel).where(
            NotificationModel.user_id == str(user_id)
        )

        if unread_only:
            statement = statement.where(NotificationModel.read_at.is_(None))

        if notification_type is not None:
            statement = statement.where(NotificationModel.notification_type == notification_type)

        count_statement = select(func.count()).select_from(statement.subquery())
        total_result = await self._session.execute(count_statement)
        total = int(total_result.scalar_one())

        statement = (
            statement.order_by(desc(NotificationModel.created_at))
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(statement)
        models = result.scalars().all()
        return [NotificationMapper.to_domain(model) for model in models], total

    async def mark_read(self, notification_id: UUID, user_id: UUID) -> Notification | None:
        statement = select(NotificationModel).where(
            and_(
                NotificationModel.id == str(notification_id),
                NotificationModel.user_id == str(user_id),
            )
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        model.read_at = datetime.now(UTC)
        await self._commit()
        await self._refresh(model)
        return NotificationMapper.to_domain(model)

    async def mark_all_read(self, user_id: UUID, before: datetime | None = None) -> int:
        statement = select(NotificationModel).where(
            and_(
                NotificationModel.user_id == str(user_id),
                NotificationModel.read_at.is_(None),
            )
        )
        if before is not None:
            statement = statement.where(NotificationModel.created_at < before)

        result = await self._session.execute(statement)
        models = result.scalars().all()
        now = datetime.now(UTC)
        for model in models:
            model.read_at = now
        await self._commit()
        return len(models)

    async def dismiss(self, notification_id: UUID, user_id: UUID) -> Notification | None:
        statement = select(NotificationModel).where(
            and_(
                NotificationModel.id == str(notification_id),
                NotificationModel.user_id == str(user_id),
            )
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        model.dismissed_at = datetime.now(UTC)
        model.read_at = datetime.now(UTC)
        await self._commit()
        await self._refresh(model)
        return NotificationMapper.to_domain(model)

    async def count_unread(self, user_id: UUID) -> int:
        statement = select(func.count()).select_from(NotificationModel).where(
            and_(
                NotificationModel.user_id == str(user_id),
                NotificationModel.read_at.is_(None),
            )
        )
        result = await self._session.execute(statement)
        return int(result.scalar_one())

    async def count_unread_since(self, user_id: UUID, since: datetime) -> int:
        statement = select(func.count()).select_from(NotificationModel).where(
            and_(
                NotificationModel.user_id == str(user_id),
                NotificationModel.read_at.is_(None),
                NotificationModel.created_at >= since,
            )
        )
        result = await self._session.execute(statement)
        return int(result.scalar_one())

    async def expire_old(self, before: datetime) -> int:
        statement = select(NotificationModel).where(
            and_(
                NotificationModel.expires_at.is_not(None),
                NotificationModel.expires_at < before,
            )
        )
        result = await self._session.execute(statement)
        models = result.scalars().all()
        for model in models:
            await self._session.delete(model)
        await self._commit()
        return len(models)

    async def list_old(self, before: datetime, limit: int = 100) -> list[Notification]:
        statement = (
            select(NotificationModel)
            .where(NotificationModel.created_at < before)
            .limit(limit)
        )
        result = await self._session.execute(statement)
        models = result.scalars().all()
        return [NotificationMapper.to_domain(model) for model in models]


class NotificationDeliveryRepository(
    BaseRepository[NotificationDeliveryModel],
    NotificationDeliveryRepositoryPort,
):
    """SQLAlchemy implementation of the NotificationDeliveryRepository port."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def create(self, delivery: NotificationDelivery) -> NotificationDelivery:
        model = NotificationDeliveryMapper.to_model(delivery)
        model = await self._add_and_refresh(model)
        return NotificationDeliveryMapper.to_domain(model)

    async def get_by_id(self, delivery_id: UUID) -> NotificationDelivery | None:
        statement = select(NotificationDeliveryModel).where(
            NotificationDeliveryModel.id == str(delivery_id)
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return NotificationDeliveryMapper.to_domain(model)

    async def list_pending(
        self,
        channel: str | None = None,
        limit: int = 100,
    ) -> list[NotificationDelivery]:
        statement = select(NotificationDeliveryModel).where(
            NotificationDeliveryModel.status.in_(["pending", "failed"])
        )
        if channel is not None:
            statement = statement.where(NotificationDeliveryModel.channel == channel)
        statement = statement.limit(limit)
        result = await self._session.execute(statement)
        models = result.scalars().all()
        return [NotificationDeliveryMapper.to_domain(model) for model in models]

    async def list_scheduled(
        self,
        limit: int = 100,
        before: datetime | None = None,
    ) -> list[NotificationDelivery]:
        statement = select(NotificationDeliveryModel).where(
            NotificationDeliveryModel.status == "scheduled"
        )
        if before is not None:
            statement = statement.where(
                NotificationDeliveryModel.scheduled_for <= before
            )
        statement = statement.order_by(NotificationDeliveryModel.scheduled_for.asc()).limit(limit)
        result = await self._session.execute(statement)
        models = result.scalars().all()
        return [NotificationDeliveryMapper.to_domain(model) for model in models]

    async def list_retryable(self, limit: int = 100) -> list[NotificationDelivery]:
        statement = (
            select(NotificationDeliveryModel)
            .where(NotificationDeliveryModel.status == "retryable_failure")
            .order_by(NotificationDeliveryModel.next_attempt_at.asc())
            .limit(limit)
        )
        result = await self._session.execute(statement)
        models = result.scalars().all()
        return [NotificationDeliveryMapper.to_domain(model) for model in models]

    async def list_stuck_processing(
        self,
        timeout_minutes: int = 30,
        limit: int = 100,
    ) -> list[NotificationDelivery]:
        cutoff = datetime.now(UTC) - timedelta(minutes=timeout_minutes)
        statement = (
            select(NotificationDeliveryModel)
            .where(
                NotificationDeliveryModel.status == "processing",
                NotificationDeliveryModel.processing_started_at <= cutoff,
            )
            .limit(limit)
        )
        result = await self._session.execute(statement)
        models = result.scalars().all()
        return [NotificationDeliveryMapper.to_domain(model) for model in models]

    async def get_by_provider_idempotency_key(
        self,
        key: str,
    ) -> NotificationDelivery | None:
        statement = select(NotificationDeliveryModel).where(
            NotificationDeliveryModel.provider_idempotency_key == key
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return NotificationDeliveryMapper.to_domain(model)

    async def count_pending_since(
        self,
        user_id: UUID,
        since: datetime,
    ) -> int:
        subquery = (
            select(NotificationDeliveryModel.id)
            .join(
                NotificationModel,
                NotificationModel.id == NotificationDeliveryModel.notification_id,
            )
            .where(
                NotificationModel.user_id == str(user_id),
                NotificationDeliveryModel.status.in_(["pending", "processing"]),
                NotificationDeliveryModel.created_at >= since,
            )
        )
        count_statement = select(func.count()).select_from(subquery.subquery())
        result = await self._session.execute(count_statement)
        return int(result.scalar_one())

    async def update(self, delivery: NotificationDelivery) -> NotificationDelivery:
        statement = select(NotificationDeliveryModel).where(
            NotificationDeliveryModel.id == str(delivery.id)
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            raise ResourceNotFoundError(
                f"NotificationDelivery with id '{delivery.id}' was not found."
            )
        NotificationDeliveryMapper.update_model(model, delivery)
        await self._commit()
        await self._refresh(model)
        return NotificationDeliveryMapper.to_domain(model)


class NotificationPreferenceRepository(
    BaseRepository[NotificationPreferenceModel],
    NotificationPreferenceRepositoryPort,
):
    """SQLAlchemy implementation of the NotificationPreferenceRepository port."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_user_id(self, user_id: UUID) -> NotificationPreference | None:
        statement = select(NotificationPreferenceModel).where(
            NotificationPreferenceModel.user_id == str(user_id)
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return NotificationPreferenceMapper.to_domain(model)

    async def create(self, preference: NotificationPreference) -> NotificationPreference:
        model = NotificationPreferenceMapper.to_model(preference)
        model = await self._add_and_refresh(model)
        return NotificationPreferenceMapper.to_domain(model)

    async def update(self, preference: NotificationPreference) -> NotificationPreference:
        statement = select(NotificationPreferenceModel).where(
            NotificationPreferenceModel.user_id == str(preference.user_id),
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            raise ResourceNotFoundError(
                f"NotificationPreference for user '{preference.user_id}' was not found."
            )
        NotificationPreferenceMapper.update_model(model, preference)
        await self._commit()
        await self._refresh(model)
        return NotificationPreferenceMapper.to_domain(model)

    async def get_by_unsubscribe_token(self, token: str) -> NotificationPreference | None:
        statement = select(NotificationPreferenceModel).where(
            NotificationPreferenceModel.unsubscribe_token == token
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return NotificationPreferenceMapper.to_domain(model)

    async def delete_by_user_id(self, user_id: UUID) -> None:
        await self._session.execute(
            delete(NotificationPreferenceModel).where(
                NotificationPreferenceModel.user_id == str(user_id)
            )
        )
        await self._commit()


__all__ = [
    "NotificationDeliveryRepository",
    "NotificationPreferenceRepository",
    "NotificationRepository",
]
