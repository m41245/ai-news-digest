from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ai_news_digest.core.exceptions import ResourceNotFoundError
from ai_news_digest.domain.models.digest_delivery import DigestDelivery
from ai_news_digest.domain.ports.delivery_repository import (
    DeliveryRepository as DeliveryRepositoryPort,
)
from ai_news_digest.infrastructure.database.mappers.digest_delivery_mapper import (
    DigestDeliveryMapper,
)
from ai_news_digest.infrastructure.database.models.digest_delivery_model import (
    DigestDeliveryModel,
)
from ai_news_digest.infrastructure.database.repositories.base_repository import (
    BaseRepository,
)


class DeliveryRepository(
    BaseRepository[DigestDeliveryModel],
    DeliveryRepositoryPort,
):
    """
    SQLAlchemy implementation of the DeliveryRepository port.
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        super().__init__(session)

    async def create(
        self,
        delivery: DigestDelivery,
    ) -> DigestDelivery:
        """
        Persist a new delivery record.
        """
        model = DigestDeliveryMapper.to_model(delivery)
        model = await self._add_and_refresh(model)
        return DigestDeliveryMapper.to_domain(model)

    async def get_by_id(
        self,
        delivery_id: UUID,
    ) -> DigestDelivery | None:
        """
        Retrieve a delivery by its identifier.
        """
        statement = select(DigestDeliveryModel).where(
            DigestDeliveryModel.id == str(delivery_id),
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return DigestDeliveryMapper.to_domain(model)

    async def get_by_digest_and_recipient(
        self,
        digest_id: UUID,
        recipient: str,
    ) -> DigestDelivery | None:
        """
        Return the delivery record for a specific digest and recipient.
        """
        statement = select(DigestDeliveryModel).where(
            DigestDeliveryModel.digest_id == str(digest_id),
            DigestDeliveryModel.recipient == recipient,
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return DigestDeliveryMapper.to_domain(model)

    async def list_by_digest(
        self,
        digest_id: UUID,
    ) -> list[DigestDelivery]:
        """
        Return all delivery records for a digest.
        """
        statement = (
            select(DigestDeliveryModel)
            .where(DigestDeliveryModel.digest_id == str(digest_id))
            .order_by(DigestDeliveryModel.created_at.asc())
        )
        result = await self._session.execute(statement)
        models = result.scalars().all()
        return [DigestDeliveryMapper.to_domain(model) for model in models]

    async def update(
        self,
        delivery: DigestDelivery,
    ) -> DigestDelivery:
        """
        Update an existing delivery record.
        """
        statement = select(DigestDeliveryModel).where(
            DigestDeliveryModel.id == str(delivery.id),
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            raise ResourceNotFoundError(f"Delivery with id '{delivery.id}' was not found.")
        DigestDeliveryMapper.update_model(model, delivery)
        model = await self._add_and_refresh(model)
        return DigestDeliveryMapper.to_domain(model)

    async def increment_attempt(
        self,
        delivery_id: UUID,
    ) -> DigestDelivery | None:
        """
        Atomically increment the attempt counter for a delivery.
        """
        statement = (
            update(DigestDeliveryModel)
            .where(DigestDeliveryModel.id == str(delivery_id))
            .values(attempt_count=DigestDeliveryModel.attempt_count + 1)
            .returning(DigestDeliveryModel)
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        await self._commit()
        await self._session.refresh(model)
        return DigestDeliveryMapper.to_domain(model)


__all__ = ["DeliveryRepository"]
