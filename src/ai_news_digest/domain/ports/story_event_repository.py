from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from ai_news_digest.domain.models.story_event import StoryEvent


class StoryEventRepository(ABC):
    @abstractmethod
    async def create(self, event: StoryEvent) -> StoryEvent:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, event_id: UUID) -> StoryEvent | None:
        raise NotImplementedError

    @abstractmethod
    async def list_by_cluster_id(
        self,
        cluster_id: UUID,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[StoryEvent]:
        raise NotImplementedError

    @abstractmethod
    async def replace_for_cluster(
        self,
        cluster_id: UUID,
        events: list[StoryEvent],
    ) -> list[StoryEvent]:
        raise NotImplementedError

    @abstractmethod
    async def delete_for_cluster(self, cluster_id: UUID) -> int:
        raise NotImplementedError

    @abstractmethod
    async def count_by_cluster_id(self, cluster_id: UUID) -> int:
        raise NotImplementedError

    @abstractmethod
    async def list_by_cluster_ids(
        self,
        cluster_ids: list[UUID],
        *,
        limit: int = 10,
    ) -> dict[UUID, list[StoryEvent]]:
        """Return events grouped by cluster ID for the given clusters."""
        raise NotImplementedError


__all__ = ["StoryEventRepository"]
