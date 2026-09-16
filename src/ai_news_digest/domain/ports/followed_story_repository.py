from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from ai_news_digest.domain.models.followed_story import FollowedStory


class FollowedStoryRepository(ABC):
    """Port for persisting and retrieving followed stories."""

    @abstractmethod
    async def create(self, followed_story: FollowedStory) -> FollowedStory:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, followed_story_id: UUID) -> FollowedStory | None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_user_and_story(
        self,
        user_id: UUID,
        story_cluster_id: UUID,
    ) -> FollowedStory | None:
        raise NotImplementedError

    @abstractmethod
    async def list_by_user(
        self,
        user_id: UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[FollowedStory], int]:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, user_id: UUID, story_cluster_id: UUID) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def count_by_user(self, user_id: UUID) -> int:
        raise NotImplementedError
