from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_news_digest.domain.models.followed_story import FollowedStory
from ai_news_digest.domain.ports.followed_story_repository import (
    FollowedStoryRepository as FollowedStoryRepositoryPort,
)
from ai_news_digest.infrastructure.database.models.followed_story_model import (
    FollowedStoryModel,
)
from ai_news_digest.infrastructure.database.repositories.base_repository import (
    BaseRepository,
)


class SqlAlchemyFollowedStoryRepository(
    BaseRepository[FollowedStoryModel],
    FollowedStoryRepositoryPort,
):
    """SQLAlchemy implementation of the FollowedStoryRepository port."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def create(self, followed_story: FollowedStory) -> FollowedStory:
        model = FollowedStoryModel(
            id=str(followed_story.id),
            user_id=str(followed_story.user_id),
            story_cluster_id=str(followed_story.story_cluster_id),
            created_at=followed_story.created_at,
        )
        model = await self._add_and_refresh(model)
        return self._to_domain(model)

    async def get_by_id(
        self, followed_story_id: UUID
    ) -> FollowedStory | None:
        statement = select(FollowedStoryModel).where(
            FollowedStoryModel.id == str(followed_story_id)
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_domain(model)

    async def get_by_user_and_story(
        self,
        user_id: UUID,
        story_cluster_id: UUID,
    ) -> FollowedStory | None:
        statement = select(FollowedStoryModel).where(
            FollowedStoryModel.user_id == str(user_id),
            FollowedStoryModel.story_cluster_id == str(story_cluster_id),
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_domain(model)

    async def list_by_user(
        self,
        user_id: UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[FollowedStory], int]:
        base_statement = select(FollowedStoryModel).where(
            FollowedStoryModel.user_id == str(user_id),
        ).order_by(FollowedStoryModel.created_at.desc())

        count_statement = select(func.count()).select_from(base_statement.subquery())
        total_result = await self._session.execute(count_statement)
        total = total_result.scalar_one()

        statement = base_statement.limit(limit).offset(offset)
        result = await self._session.execute(statement)
        items = [self._to_domain(model) for model in result.scalars().all()]
        return items, total

    async def delete(self, user_id: UUID, story_cluster_id: UUID) -> bool:
        statement = select(FollowedStoryModel).where(
            FollowedStoryModel.user_id == str(user_id),
            FollowedStoryModel.story_cluster_id == str(story_cluster_id),
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return False
        await self._session.delete(model)
        await self._commit()
        return True

    async def count_by_user(self, user_id: UUID) -> int:
        statement = select(func.count()).select_from(FollowedStoryModel).where(
            FollowedStoryModel.user_id == str(user_id),
        )
        result = await self._session.execute(statement)
        return result.scalar_one()

    @staticmethod
    def _to_domain(model: FollowedStoryModel) -> FollowedStory:
        return FollowedStory(
            id=UUID(model.id),
            user_id=UUID(model.user_id),
            story_cluster_id=UUID(model.story_cluster_id),
            created_at=model.created_at,
        )
