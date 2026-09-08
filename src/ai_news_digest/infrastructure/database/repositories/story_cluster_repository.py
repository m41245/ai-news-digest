from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_news_digest.core.exceptions import ResourceNotFoundError
from ai_news_digest.domain.models.story_cluster import StoryCluster
from ai_news_digest.domain.ports.story_cluster_repository import (
    StoryClusterRepository as StoryClusterRepositoryPort,
)
from ai_news_digest.infrastructure.database.mappers.story_cluster_mapper import (
    StoryClusterMapper,
)
from ai_news_digest.infrastructure.database.models.story_cluster_model import (
    StoryClusterModel,
)
from ai_news_digest.infrastructure.database.repositories.base_repository import (
    BaseRepository,
)


class StoryClusterRepository(
    BaseRepository[StoryClusterModel],
    StoryClusterRepositoryPort,
):
    """
    SQLAlchemy implementation of the StoryClusterRepository port.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def create(self, cluster: StoryCluster) -> StoryCluster:
        model = StoryClusterMapper.to_model(cluster)
        model = await self._add_and_refresh(model)
        return StoryClusterMapper.to_domain(model)

    async def get_by_id(self, cluster_id: UUID) -> StoryCluster | None:
        statement = select(StoryClusterModel).where(StoryClusterModel.id == str(cluster_id))
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return StoryClusterMapper.to_domain(model)

    async def get_by_slug(self, slug: str) -> StoryCluster | None:
        statement = select(StoryClusterModel).where(StoryClusterModel.slug == slug)
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return StoryClusterMapper.to_domain(model)

    async def list_all(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[StoryCluster]:
        statement = (
            select(StoryClusterModel)
            .order_by(StoryClusterModel.first_published_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(statement)
        return [StoryClusterMapper.to_domain(model) for model in result.scalars().all()]

    async def count(self) -> int:
        statement = select(func.count()).select_from(StoryClusterModel)
        result = await self._session.execute(statement)
        return int(result.scalar_one())

    async def update(self, cluster: StoryCluster) -> StoryCluster:
        statement = select(StoryClusterModel).where(StoryClusterModel.id == str(cluster.id))
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            raise ResourceNotFoundError(f"StoryCluster with id '{cluster.id}' was not found.")
        StoryClusterMapper.update_model(model, cluster)
        await self._commit()
        model = await self._refresh(model)
        return StoryClusterMapper.to_domain(model)

    async def attach_article(
        self,
        cluster_id: UUID,
        article_id: UUID,
    ) -> None:
        from sqlalchemy import update as sa_update

        statement = (
            sa_update(StoryClusterModel)
            .where(StoryClusterModel.id == str(cluster_id))
            .values(
                last_updated_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        )
        await self._session.execute(statement)
        await self._commit()

    async def detach_article(self, article_id: UUID) -> None:
        from sqlalchemy import update as sa_update

        statement = (
            sa_update(StoryClusterModel)
            .where(StoryClusterModel.representative_article_id == str(article_id))
            .values(representative_article_id=None)
        )
        await self._session.execute(statement)
        await self._commit()


__all__ = ["StoryClusterRepository"]
