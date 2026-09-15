from __future__ import annotations

from typing import Any, cast
from uuid import UUID

from sqlalchemy import CursorResult, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_news_digest.domain.models.story_event import StoryEvent
from ai_news_digest.domain.ports.story_event_repository import (
    StoryEventRepository as StoryEventRepositoryPort,
)
from ai_news_digest.infrastructure.database.mappers.story_event_mapper import (
    StoryEventMapper,
)
from ai_news_digest.infrastructure.database.models.story_event_model import (
    StoryEventModel,
)
from ai_news_digest.infrastructure.database.repositories.base_repository import (
    BaseRepository,
)


class StoryEventRepository(
    BaseRepository[StoryEventModel],
    StoryEventRepositoryPort,
):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def create(self, event: StoryEvent) -> StoryEvent:
        model = StoryEventMapper.to_model(event)
        model = await self._add_and_refresh(model)
        return StoryEventMapper.to_domain(model)

    async def get_by_id(self, event_id: UUID) -> StoryEvent | None:
        statement = select(StoryEventModel).where(
            StoryEventModel.id == str(event_id)
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return StoryEventMapper.to_domain(model)

    async def list_by_cluster_id(
        self,
        cluster_id: UUID,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[StoryEvent]:
        statement = (
            select(StoryEventModel)
            .where(StoryEventModel.story_cluster_id == str(cluster_id))
            .order_by(
                StoryEventModel.sequence.asc(),
                StoryEventModel.event_time.asc(),
                StoryEventModel.created_at.asc(),
            )
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(statement)
        return [StoryEventMapper.to_domain(model) for model in result.scalars().all()]

    async def replace_for_cluster(
        self,
        cluster_id: UUID,
        events: list[StoryEvent],
    ) -> list[StoryEvent]:
        await self.delete_for_cluster(cluster_id)
        created: list[StoryEvent] = []
        for event in events:
            model = StoryEventMapper.to_model(event)
            self._session.add(model)
            created.append(event)
        await self._commit()
        return created

    async def delete_for_cluster(self, cluster_id: UUID) -> int:
        statement = delete(StoryEventModel).where(
            StoryEventModel.story_cluster_id == str(cluster_id)
        )
        result = cast(CursorResult[Any], await self._session.execute(statement))
        await self._commit()
        return int(result.rowcount or 0)

    async def count_by_cluster_id(self, cluster_id: UUID) -> int:
        statement = (
            select(func.count())
            .select_from(StoryEventModel)
            .where(StoryEventModel.story_cluster_id == str(cluster_id))
        )
        result = await self._session.execute(statement)
        return int(result.scalar_one())


__all__ = ["StoryEventRepository"]
