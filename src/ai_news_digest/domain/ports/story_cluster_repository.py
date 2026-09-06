from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from ai_news_digest.domain.models.story_cluster import StoryCluster


class StoryClusterRepository(ABC):
    """
    Port for persisting and retrieving story clusters.
    """

    @abstractmethod
    async def create(self, cluster: StoryCluster) -> StoryCluster:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, cluster_id: UUID) -> StoryCluster | None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_slug(self, slug: str) -> StoryCluster | None:
        raise NotImplementedError

    @abstractmethod
    async def list_all(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[StoryCluster]:
        raise NotImplementedError

    @abstractmethod
    async def count(self) -> int:
        raise NotImplementedError

    @abstractmethod
    async def update(self, cluster: StoryCluster) -> StoryCluster:
        raise NotImplementedError

    @abstractmethod
    async def attach_article(
        self,
        cluster_id: UUID,
        article_id: UUID,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def detach_article(self, article_id: UUID) -> None:
        raise NotImplementedError


__all__ = ["StoryClusterRepository"]
