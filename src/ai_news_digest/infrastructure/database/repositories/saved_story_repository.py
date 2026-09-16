from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_news_digest.domain.models.saved_story import SavedStory
from ai_news_digest.domain.ports.saved_story_repository import (
    SavedStoryRepository as SavedStoryRepositoryPort,
)
from ai_news_digest.infrastructure.database.models.saved_story_model import (
    SavedStoryModel,
)
from ai_news_digest.infrastructure.database.repositories.base_repository import (
    BaseRepository,
)


class SqlAlchemySavedStoryRepository(BaseRepository[SavedStoryModel], SavedStoryRepositoryPort):
    """SQLAlchemy implementation of the SavedStoryRepository port."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def create(self, saved_story: SavedStory) -> SavedStory:
        model = SavedStoryModel(
            id=str(saved_story.id),
            user_id=str(saved_story.user_id),
            story_cluster_id=str(saved_story.story_cluster_id),
            collection_id=str(saved_story.collection_id) if saved_story.collection_id else None,
            note=saved_story.note,
            created_at=saved_story.created_at,
        )
        model = await self._add_and_refresh(model)
        return self._to_domain(model)

    async def get_by_id(self, saved_story_id: UUID) -> SavedStory | None:
        statement = select(SavedStoryModel).where(SavedStoryModel.id == str(saved_story_id))
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_domain(model)

    async def get_by_user_and_story(
        self,
        user_id: UUID,
        story_cluster_id: UUID,
    ) -> SavedStory | None:
        statement = select(SavedStoryModel).where(
            SavedStoryModel.user_id == str(user_id),
            SavedStoryModel.story_cluster_id == str(story_cluster_id),
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_domain(model)

    async def list_by_user(
        self,
        user_id: UUID,
        collection_id: UUID | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[SavedStory], int]:
        statement = (
            select(SavedStoryModel)
            .where(SavedStoryModel.user_id == str(user_id))
            .order_by(SavedStoryModel.created_at.desc())
        )
        if collection_id is not None:
            statement = statement.where(SavedStoryModel.collection_id == str(collection_id))

        count_statement = select(func.count()).select_from(statement.subquery())
        total_result = await self._session.execute(count_statement)
        total = total_result.scalar_one()

        statement = statement.limit(limit).offset(offset)
        result = await self._session.execute(statement)
        items = [self._to_domain(model) for model in result.scalars().all()]
        return items, total

    async def delete(self, user_id: UUID, story_cluster_id: UUID) -> bool:
        statement = select(SavedStoryModel).where(
            SavedStoryModel.user_id == str(user_id),
            SavedStoryModel.story_cluster_id == str(story_cluster_id),
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return False
        await self._session.delete(model)
        await self._commit()
        return True

    async def count_by_user(self, user_id: UUID) -> int:
        statement = select(func.count()).select_from(SavedStoryModel).where(
            SavedStoryModel.user_id == str(user_id),
        )
        result = await self._session.execute(statement)
        return result.scalar_one()

    @staticmethod
    def _to_domain(model: SavedStoryModel) -> SavedStory:
        return SavedStory(
            id=UUID(model.id),
            user_id=UUID(model.user_id),
            story_cluster_id=UUID(model.story_cluster_id),
            collection_id=UUID(model.collection_id) if model.collection_id else None,
            note=model.note,
            created_at=model.created_at,
        )
