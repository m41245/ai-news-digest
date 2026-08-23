from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from ai_news_digest.domain.models.digest_delivery import DigestDelivery


class DeliveryRepository(ABC):
    """
    Repository interface for digest delivery persistence.
    """

    @abstractmethod
    async def create(
        self,
        delivery: DigestDelivery,
    ) -> DigestDelivery:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(
        self,
        delivery_id: UUID,
    ) -> DigestDelivery | None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_digest_and_recipient(
        self,
        digest_id: UUID,
        recipient: str,
    ) -> DigestDelivery | None:
        """Return the delivery record for a specific digest and recipient."""
        raise NotImplementedError

    @abstractmethod
    async def list_by_digest(
        self,
        digest_id: UUID,
    ) -> list[DigestDelivery]:
        """Return all delivery records for a digest."""
        raise NotImplementedError

    @abstractmethod
    async def update(
        self,
        delivery: DigestDelivery,
    ) -> DigestDelivery:
        raise NotImplementedError

    @abstractmethod
    async def increment_attempt(
        self,
        delivery_id: UUID,
    ) -> DigestDelivery | None:
        """Atomically increment the attempt counter for a delivery."""
        raise NotImplementedError


__all__ = ["DeliveryRepository"]
