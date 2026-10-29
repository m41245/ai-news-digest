from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_news_digest.core.exceptions import ResourceNotFoundError
from ai_news_digest.domain.models.topic import Topic
from ai_news_digest.domain.ports.topic_repository import TopicRepository
from ai_news_digest.infrastructure.database.mappers.topic_mapper import (
    TopicMapper,
    _slugify,
)
from ai_news_digest.infrastructure.database.models.topic_model import TopicModel
from ai_news_digest.infrastructure.database.repositories.base_repository import (
    BaseRepository,
)


class SqlAlchemyTopicRepository(BaseRepository[TopicModel], TopicRepository):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self._session = session

    async def get_by_id(self, topic_id: str) -> Any | None:
        result = await self._session.execute(select(TopicModel).where(TopicModel.id == topic_id))
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return TopicMapper.to_domain(model)

    async def get_by_slug(self, slug: str) -> Any | None:
        result = await self._session.execute(
            select(TopicModel).where(TopicModel.slug == _slugify(slug))
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return TopicMapper.to_domain(model)

    async def list_by_ids(self, topic_ids: list[str]) -> list[Any]:
        result = await self._session.execute(select(TopicModel).where(TopicModel.id.in_(topic_ids)))
        return [TopicMapper.to_domain(m) for m in result.scalars().all()]

    async def list_all(self) -> list[Any]:
        result = await self._session.execute(select(TopicModel))
        return [TopicMapper.to_domain(m) for m in result.scalars().all()]

    async def list_all_with_counts(self) -> list[Any]:
        from ai_news_digest.infrastructure.database.models.article_topic_model import (
            ArticleTopicModel,
        )

        statement = (
            select(
                TopicModel,
                func.count(ArticleTopicModel.article_id).label("article_count"),
            )
            .outerjoin(
                ArticleTopicModel,
                TopicModel.id == ArticleTopicModel.topic_id,
            )
            .group_by(TopicModel.id)
            .order_by(TopicModel.name)
        )
        result = await self._session.execute(statement)
        rows = result.all()
        output: list[Any] = []
        for topic_model, article_count in rows:
            topic = TopicMapper.to_domain(topic_model)
            topic.article_count = article_count or 0
            output.append(topic)
        return output

    async def create(self, topic: Any) -> Any:
        if isinstance(topic, TopicModel):
            model = topic
            if not getattr(model, "slug", None):
                model.slug = _slugify(model.name)
        elif isinstance(topic, Topic):
            model = TopicMapper.to_model(topic)
        else:
            model = TopicModel(
                id=str(getattr(topic, "id", None) or __import__("uuid").uuid4()),
                name=topic.name,
                slug=_slugify(topic.name),
            )
        self._session.add(model)
        await self._flush()
        return TopicMapper.to_domain(model)

    async def update(self, topic: Any) -> Any:
        if not isinstance(topic, Topic):
            raise TypeError("TopicRepository.update expects a Topic domain model")
        result = await self._session.execute(
            select(TopicModel).where(TopicModel.id == str(topic.id))
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise ResourceNotFoundError(f"Topic with id '{topic.id}' was not found.")
        TopicMapper.update_model(model, topic)
        await self._flush()
        return TopicMapper.to_domain(model)

    async def delete(self, topic_id: str) -> None:
        result = await self._session.execute(select(TopicModel).where(TopicModel.id == topic_id))
        model = result.scalar_one_or_none()
        if model is not None:
            await self._session.delete(model)
            await self._flush()


__all__ = ["SqlAlchemyTopicRepository"]
