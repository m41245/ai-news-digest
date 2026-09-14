from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from ai_news_digest.domain.models.conflict import Conflict


class ConflictRepository(ABC):
    """Port for persisting and retrieving conflict records."""

    @abstractmethod
    async def create(self, conflict: Conflict) -> Conflict:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, conflict_id: UUID) -> Conflict | None:
        raise NotImplementedError

    @abstractmethod
    async def find_existing(
        self,
        *,
        claim_a_id: UUID,
        claim_b_id: UUID,
        detection_version: str,
    ) -> Conflict | None:
        raise NotImplementedError

    @abstractmethod
    async def list_recent(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        status: str | None = None,
    ) -> list[Conflict]:
        raise NotImplementedError

    @abstractmethod
    async def list_by_story_cluster_id(
        self,
        story_cluster_id: UUID,
        *,
        limit: int = 50,
    ) -> list[Conflict]:
        raise NotImplementedError

    @abstractmethod
    async def update(self, conflict: Conflict) -> Conflict:
        raise NotImplementedError

    @abstractmethod
    async def count(self) -> int:
        raise NotImplementedError


__all__ = ["ConflictRepository"]
