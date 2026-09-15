from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ai_news_digest.domain.models.story_activity import StoryActivity
from ai_news_digest.domain.ports.story_activity_repository import (
    StoryActivityRepository as StoryActivityRepositoryPort,
)
from ai_news_digest.infrastructure.database.mappers.story_activity_mapper import (
    StoryActivityMapper,
)
from ai_news_digest.infrastructure.database.models.story_activity_model import (
    StoryActivityModel,
)
from ai_news_digest.infrastructure.database.repositories.base_repository import (
    BaseRepository,
)


class StoryActivityRepository(
    BaseRepository[StoryActivityModel],
    StoryActivityRepositoryPort,
):
    """
    SQLAlchemy implementation of the StoryActivityRepository port.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def create(self, activity: StoryActivity) -> StoryActivity:
        model = StoryActivityMapper.to_model(activity)
        model = await self._add_and_refresh(model)
        return StoryActivityMapper.to_domain(model)

    async def get_by_story_cluster_id(
        self,
        story_cluster_id: UUID,
    ) -> StoryActivity | None:
        statement = select(StoryActivityModel).where(
            StoryActivityModel.story_cluster_id == str(story_cluster_id)
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return StoryActivityMapper.to_domain(model)

    async def list_recent(
        self,
        *,
        evaluated_since: datetime | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[StoryActivity]:
        statement = select(StoryActivityModel).order_by(
            StoryActivityModel.evaluated_at.desc()
        )
        if evaluated_since is not None:
            statement = statement.where(StoryActivityModel.evaluated_at >= evaluated_since)
        if status is not None:
            statement = statement.where(StoryActivityModel.status == status)
        statement = statement.limit(limit).offset(offset)
        result = await self._session.execute(statement)
        return [StoryActivityMapper.to_domain(model) for model in result.scalars().all()]

    async def upsert(self, activity: StoryActivity) -> StoryActivity:
        existing = await self.get_by_story_cluster_id(activity.story_cluster_id)
        if existing is None:
            return await self.create(activity)
        statement = (
            update(StoryActivityModel)
            .where(StoryActivityModel.story_cluster_id == str(activity.story_cluster_id))
            .values(
                status=activity.status.value,
                activity_score=activity.activity_score,
                confidence=activity.confidence,
                explanation=activity.explanation,
                evaluated_at=activity.evaluated_at,
                detection_version=activity.detection_version,
                article_count_recent=activity.article_count_recent,
                unique_source_count_recent=activity.unique_source_count_recent,
                recent_article_velocity=activity.recent_article_velocity,
                latest_article_at=activity.latest_article_at,
                first_article_at=activity.first_article_at,
                recent_claim_count=activity.recent_claim_count,
                recent_conflict_count=activity.recent_conflict_count,
                state_change_count=activity.state_change_count,
                updated_at=activity.updated_at,
            )
        )
        await self._session.execute(statement)
        await self._commit()
        updated = await self.get_by_story_cluster_id(activity.story_cluster_id)
        if updated is None:
            raise RuntimeError(
                f"Failed to upsert story activity for cluster {activity.story_cluster_id}"
            )
        return updated

    async def count(self) -> int:
        statement = select(func.count()).select_from(StoryActivityModel)
        result = await self._session.execute(statement)
        return int(result.scalar_one())

    async def get_by_cluster_ids(
        self,
        cluster_ids: list[UUID],
    ) -> list[StoryActivity]:
        if not cluster_ids:
            return []
        statement = select(StoryActivityModel).where(
            StoryActivityModel.story_cluster_id.in_([str(cid) for cid in cluster_ids])
        )
        result = await self._session.execute(statement)
        return [StoryActivityMapper.to_domain(model) for model in result.scalars().all()]


__all__ = ["StoryActivityRepository"]
