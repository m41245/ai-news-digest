from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from ai_news_digest.domain.models.source import Source


class SourceRepository(ABC):
    """
    Port for persisting and retrieving news sources.
    """

    @abstractmethod
    async def create(
        self,
        source: Source,
    ) -> Source:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(
        self,
        source_id: UUID,
    ) -> Source | None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_feed_url(
        self,
        feed_url: str,
    ) -> Source | None:
        raise NotImplementedError

    @abstractmethod
    async def list_all(
        self,
    ) -> list[Source]:
        raise NotImplementedError

    @abstractmethod
    async def list_enabled(
        self,
    ) -> list[Source]:
        """
        Return enabled RSS sources.
        """
        raise NotImplementedError

    @abstractmethod
    async def list_active(
        self,
    ) -> list[Source]:
        """
        Alias used by the ingestion service.

        Implementations can simply return list_enabled().
        """
        raise NotImplementedError

    @abstractmethod
    async def update(
        self,
        source: Source,
    ) -> Source:
        raise NotImplementedError

    @abstractmethod
    async def delete(
        self,
        source_id: UUID,
    ) -> None:
        raise NotImplementedError
