from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from ai_news_digest.domain.models.saved_story import SavedStory


class SavedStoryRepository(ABC):
    """Port for persisting and retrieving saved stories."""

    @abstractmethod
    async def create(self, saved_story: SavedStory) -> SavedStory:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, saved_story_id: UUID) -> SavedStory | None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_user_and_story(
        self,
        user_id: UUID,
        story_cluster_id: UUID,
    ) -> SavedStory | None:
        raise NotImplementedError

    @abstractmethod
    async def list_by_user(
        self,
        user_id: UUID,
        collection_id: UUID | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[SavedStory], int]:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, user_id: UUID, story_cluster_id: UUID) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def count_by_user(self, user_id: UUID) -> int:
        raise NotImplementedError
