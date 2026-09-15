from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from ai_news_digest.domain.models.story_activity import StoryActivity


class StoryActivityRepository(ABC):
    """
    Port for persisting and retrieving story activity records.
    """

    @abstractmethod
    async def create(self, activity: StoryActivity) -> StoryActivity:
        raise NotImplementedError

    @abstractmethod
    async def get_by_story_cluster_id(
        self,
        story_cluster_id: UUID,
    ) -> StoryActivity | None:
        raise NotImplementedError

    @abstractmethod
    async def list_recent(
        self,
        *,
        evaluated_since: datetime | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[StoryActivity]:
        raise NotImplementedError

    @abstractmethod
    async def upsert(
        self,
        activity: StoryActivity,
    ) -> StoryActivity:
        raise NotImplementedError

    @abstractmethod
    async def count(self) -> int:
        raise NotImplementedError

    @abstractmethod
    async def get_by_cluster_ids(
        self,
        cluster_ids: list[UUID],
    ) -> list[StoryActivity]:
        """Return story activities for the given cluster IDs."""
        raise NotImplementedError


__all__ = ["StoryActivityRepository"]
