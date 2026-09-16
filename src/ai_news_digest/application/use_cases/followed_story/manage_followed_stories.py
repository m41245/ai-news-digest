from __future__ import annotations

from uuid import UUID

from ai_news_digest.core.exceptions import DuplicateResourceError
from ai_news_digest.domain.models.followed_story import FollowedStory
from ai_news_digest.domain.ports.followed_story_repository import FollowedStoryRepository


class FollowStoryUseCase:
    """Use case for following a story cluster."""

    def __init__(self, followed_story_repository: FollowedStoryRepository) -> None:
        self._followed_story_repository = followed_story_repository

    async def execute(
        self,
        user_id: UUID,
        story_cluster_id: UUID,
    ) -> FollowedStory:
        existing = await self._followed_story_repository.get_by_user_and_story(
            user_id, story_cluster_id,
        )
        if existing is not None:
            raise DuplicateResourceError("Story is already being followed.")

        followed_story = FollowedStory.create(
            user_id=user_id,
            story_cluster_id=story_cluster_id,
        )
        return await self._followed_story_repository.create(followed_story)


class UnfollowStoryUseCase:
    """Use case for unfollowing a story cluster."""

    def __init__(self, followed_story_repository: FollowedStoryRepository) -> None:
        self._followed_story_repository = followed_story_repository

    async def execute(
        self,
        user_id: UUID,
        story_cluster_id: UUID,
    ) -> None:
        deleted = await self._followed_story_repository.delete(user_id, story_cluster_id)
        if not deleted:
            from ai_news_digest.core.exceptions import ResourceNotFoundError
            raise ResourceNotFoundError("Followed story not found.")


class ListFollowedStoriesUseCase:
    """Use case for listing a user's followed stories."""

    def __init__(self, followed_story_repository: FollowedStoryRepository) -> None:
        self._followed_story_repository = followed_story_repository

    async def execute(
        self,
        user_id: UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[FollowedStory], int]:
        return await self._followed_story_repository.list_by_user(
            user_id=user_id,
            limit=limit,
            offset=offset,
        )
