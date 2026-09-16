from __future__ import annotations

from uuid import UUID

from ai_news_digest.core.exceptions import DuplicateResourceError, ResourceNotFoundError
from ai_news_digest.domain.models.saved_story import SavedStory
from ai_news_digest.domain.ports.saved_story_repository import SavedStoryRepository


class SaveStoryUseCase:
    """Use case for saving a story cluster for a user."""

    def __init__(self, saved_story_repository: SavedStoryRepository) -> None:
        self._saved_story_repository = saved_story_repository

    async def execute(
        self,
        user_id: UUID,
        story_cluster_id: UUID,
        collection_id: UUID | None = None,
        note: str | None = None,
    ) -> SavedStory:
        existing = await self._saved_story_repository.get_by_user_and_story(
            user_id, story_cluster_id,
        )
        if existing is not None:
            raise DuplicateResourceError("Story is already saved.")

        saved_story = SavedStory.create(
            user_id=user_id,
            story_cluster_id=story_cluster_id,
            collection_id=collection_id,
            note=note,
        )
        return await self._saved_story_repository.create(saved_story)


class UnsaveStoryUseCase:
    """Use case for removing a saved story for a user."""

    def __init__(self, saved_story_repository: SavedStoryRepository) -> None:
        self._saved_story_repository = saved_story_repository

    async def execute(
        self,
        user_id: UUID,
        story_cluster_id: UUID,
    ) -> None:
        deleted = await self._saved_story_repository.delete(user_id, story_cluster_id)
        if not deleted:
            raise ResourceNotFoundError("Saved story not found.")


class ListSavedStoriesUseCase:
    """Use case for listing a user's saved stories."""

    def __init__(self, saved_story_repository: SavedStoryRepository) -> None:
        self._saved_story_repository = saved_story_repository

    async def execute(
        self,
        user_id: UUID,
        collection_id: UUID | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[SavedStory], int]:
        return await self._saved_story_repository.list_by_user(
            user_id=user_id,
            collection_id=collection_id,
            limit=limit,
            offset=offset,
        )
