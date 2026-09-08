from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_news_digest.domain.ports.topic_repository import TopicRepository
from ai_news_digest.infrastructure.database.models.topic_model import TopicModel


class SqlAlchemyTopicRepository(TopicRepository):
    """
    SQLAlchemy implementation of TopicRepository.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, topic_id: str) -> Any | None:
        result = await self._session.execute(select(TopicModel).where(TopicModel.id == topic_id))
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Any | None:
        result = await self._session.execute(select(TopicModel).where(TopicModel.name == slug))
        return result.scalar_one_or_none()

    async def list_by_ids(self, topic_ids: list[str]) -> list[Any]:
        result = await self._session.execute(select(TopicModel).where(TopicModel.id.in_(topic_ids)))
        return list(result.scalars().all())

    async def create(self, topic: Any) -> Any:
        self._session.add(topic)
        await self._session.flush()
        return topic

    async def update(self, topic: Any) -> Any:
        await self._session.flush()
        return topic

    async def delete(self, topic_id: str) -> None:
        result = await self._session.execute(select(TopicModel).where(TopicModel.id == topic_id))
        model = result.scalar_one_or_none()
        if model is not None:
            await self._session.delete(model)
