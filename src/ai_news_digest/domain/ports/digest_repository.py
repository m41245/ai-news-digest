from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from ai_news_digest.domain.models.digest import Digest


class DigestRepository(ABC):
    """
    Repository interface for generated digest persistence.
    """

    @abstractmethod
    async def create(
        self,
        digest: Digest,
    ) -> Digest:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(
        self,
        digest_id: UUID,
    ) -> Digest | None:
        raise NotImplementedError

    @abstractmethod
    async def list_recent(
        self,
        limit: int = 30,
        offset: int = 0,
    ) -> list[Digest]:
        raise NotImplementedError

    @abstractmethod
    async def get_by_title(
        self,
        title: str,
    ) -> Digest | None:
        """Return the most recent digest matching the given title."""
        raise NotImplementedError

    @abstractmethod
    async def update(
        self,
        digest: Digest,
    ) -> Digest:
        raise NotImplementedError

    @abstractmethod
    async def delete(
        self,
        digest_id: UUID,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def count(self) -> int:
        """Return the total number of digests."""
        raise NotImplementedError
