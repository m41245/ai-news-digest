from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_news_digest.domain.ports.topic_repository import TopicRepository
from ai_news_digest.infrastructure.database.models.article_topic_model import (
    ArticleTopicModel,
)
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

    async def list_all(self) -> list[Any]:
        result = await self._session.execute(select(TopicModel))
        return list(result.scalars().all())

    async def list_all_with_counts(self) -> list[Any]:
        statement = (
            select(
                TopicModel,
                func.count(ArticleTopicModel.article_id).label("article_count"),
            )
            .outerjoin(ArticleTopicModel, TopicModel.id == ArticleTopicModel.topic_id)
            .group_by(TopicModel.id)
            .order_by(TopicModel.name)
        )
        result = await self._session.execute(statement)
        rows = result.all()
        output: list[Any] = []
        for topic_model, article_count in rows:
            topic_model.article_count = article_count or 0
            output.append(topic_model)
        return output

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
