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

    async def find_recent_active_clusters(
        self,
        *,
        cutoff: datetime,
        category_id: UUID | None = None,
        company_ids: list[UUID] | None = None,
        topic_ids: list[UUID] | None = None,
        title_tokens: list[str] | None = None,
        limit: int = 50,
    ) -> list[StoryCluster]:
        from sqlalchemy import and_, exists, or_

        from ai_news_digest.infrastructure.database.models.article_company_model import (
            ArticleCompanyModel,
        )
        from ai_news_digest.infrastructure.database.models.article_model import (
            ArticleModel,
        )
        from ai_news_digest.infrastructure.database.models.article_topic_model import (
            ArticleTopicModel,
        )

        statement = (
            select(StoryClusterModel)
            .where(StoryClusterModel.first_published_at >= cutoff)
            .where(StoryClusterModel.status == "active")
            .order_by(StoryClusterModel.first_published_at.desc())
            .limit(limit)
        )

        if category_id is not None:
            statement = statement.where(
                exists(
                    select(1)
                    .where(
                        and_(
                            ArticleModel.cluster_id == StoryClusterModel.id,
                            ArticleModel.category_id == str(category_id),
                        )
                    )
                )
            )

        if company_ids:
            company_strs = [str(cid) for cid in company_ids]
            statement = statement.where(
                exists(
                    select(1)
                    .where(
                        and_(
                            ArticleModel.cluster_id == StoryClusterModel.id,
                            ArticleCompanyModel.article_id == ArticleModel.id,
                            ArticleCompanyModel.company_id.in_(company_strs),
                        )
                    )
                )
            )

        if topic_ids:
            topic_strs = [str(tid) for tid in topic_ids]
            statement = statement.where(
                exists(
                    select(1)
                    .where(
                        and_(
                            ArticleModel.cluster_id == StoryClusterModel.id,
                            ArticleTopicModel.article_id == ArticleModel.id,
                            ArticleTopicModel.topic_id.in_(topic_strs),
                        )
                    )
                )
            )

        if title_tokens:
            conditions = []
            for token in title_tokens[:10]:
                conditions.append(StoryClusterModel.title.ilike(f"%{token}%"))
            if conditions:
                statement = statement.where(or_(*conditions))

        result = await self._session.execute(statement)
        return [StoryClusterMapper.to_domain(model) for model in result.scalars().all()]

    async def count(self) -> int:
        statement = select(func.count()).select_from(StoryClusterModel)
        result = await self._session.execute(statement)
        return int(result.scalar_one())

    async def search_public(
        self,
        *,
        search: str | None = None,
        category_id: UUID | None = None,
        company_id: UUID | None = None,
        topic_id: UUID | None = None,
        published_from: datetime | None = None,
        published_to: datetime | None = None,
        min_importance: float | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[StoryCluster]:
        from sqlalchemy import and_, exists, or_

        from ai_news_digest.infrastructure.database.models.article_company_model import (
            ArticleCompanyModel,
        )
        from ai_news_digest.infrastructure.database.models.article_model import (
            ArticleModel,
        )
        from ai_news_digest.infrastructure.database.models.article_topic_model import (
            ArticleTopicModel,
        )

        statement = (
            select(
                StoryClusterModel,
                func.count(ArticleModel.id).label("article_count"),
                func.count(func.distinct(ArticleModel.source_id)).label("source_count"),
            )
            .outerjoin(ArticleModel, ArticleModel.cluster_id == StoryClusterModel.id)
            .where(StoryClusterModel.status == "active")
            .group_by(StoryClusterModel.id)
        )

        if search and search.strip():
            pattern = f"%{search.strip()}%"
            statement = statement.where(
                or_(
                    StoryClusterModel.title.ilike(pattern),
                    StoryClusterModel.summary.ilike(pattern),
                )
            )

        if category_id is not None:
            statement = statement.where(
                exists(
                    select(1)
                    .where(
                        and_(
                            ArticleModel.cluster_id == StoryClusterModel.id,
                            ArticleModel.category_id == str(category_id),
                        )
                    )
                )
            )

        if company_id is not None:
            statement = statement.where(
                exists(
                    select(1)
                    .where(
                        and_(
                            ArticleModel.cluster_id == StoryClusterModel.id,
                            ArticleCompanyModel.article_id == ArticleModel.id,
                            ArticleCompanyModel.company_id == str(company_id),
                        )
                    )
                )
            )

        if topic_id is not None:
            statement = statement.where(
                exists(
                    select(1)
                    .where(
                        and_(
                            ArticleModel.cluster_id == StoryClusterModel.id,
                            ArticleTopicModel.article_id == ArticleModel.id,
                            ArticleTopicModel.topic_id == str(topic_id),
                        )
                    )
                )
            )

        if published_from is not None:
            statement = statement.where(StoryClusterModel.first_published_at >= published_from)

        if published_to is not None:
            statement = statement.where(StoryClusterModel.first_published_at <= published_to)

        if min_importance is not None:
            statement = statement.where(StoryClusterModel.importance_score >= min_importance)

        statement = (
            statement.order_by(StoryClusterModel.first_published_at.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await self._session.execute(statement)
        rows = result.all()
        clusters: list[StoryCluster] = []
        for row in rows:
            cluster = row[0]
            article_count = row[1] or 0
            source_count = row[2] or 0
            cluster.article_count = article_count
            cluster.source_count = source_count
            clusters.append(StoryClusterMapper.to_domain(cluster))
        return clusters

    async def count_public(
        self,
        *,
        search: str | None = None,
        category_id: UUID | None = None,
        company_id: UUID | None = None,
        topic_id: UUID | None = None,
        published_from: datetime | None = None,
        published_to: datetime | None = None,
        min_importance: float | None = None,
    ) -> int:
        from sqlalchemy import and_, exists, or_

        from ai_news_digest.infrastructure.database.models.article_company_model import (
            ArticleCompanyModel,
        )
        from ai_news_digest.infrastructure.database.models.article_model import (
            ArticleModel,
        )
        from ai_news_digest.infrastructure.database.models.article_topic_model import (
            ArticleTopicModel,
        )

        statement = (
            select(func.count(func.distinct(StoryClusterModel.id)))
            .select_from(StoryClusterModel)
            .outerjoin(ArticleModel, ArticleModel.cluster_id == StoryClusterModel.id)
            .where(StoryClusterModel.status == "active")
        )

        if search and search.strip():
            pattern = f"%{search.strip()}%"
            statement = statement.where(
                or_(
                    StoryClusterModel.title.ilike(pattern),
                    StoryClusterModel.summary.ilike(pattern),
                )
            )

        if category_id is not None:
            statement = statement.where(
                exists(
                    select(1)
                    .where(
                        and_(
                            ArticleModel.cluster_id == StoryClusterModel.id,
                            ArticleModel.category_id == str(category_id),
                        )
                    )
                )
            )

        if company_id is not None:
            statement = statement.where(
                exists(
                    select(1)
                    .where(
                        and_(
                            ArticleModel.cluster_id == StoryClusterModel.id,
                            ArticleCompanyModel.article_id == ArticleModel.id,
                            ArticleCompanyModel.company_id == str(company_id),
                        )
                    )
                )
            )

        if topic_id is not None:
            statement = statement.where(
                exists(
                    select(1)
                    .where(
                        and_(
                            ArticleModel.cluster_id == StoryClusterModel.id,
                            ArticleTopicModel.article_id == ArticleModel.id,
                            ArticleTopicModel.topic_id == str(topic_id),
                        )
                    )
                )
            )

        if published_from is not None:
            statement = statement.where(StoryClusterModel.first_published_at >= published_from)

        if published_to is not None:
            statement = statement.where(StoryClusterModel.first_published_at <= published_to)

        if min_importance is not None:
            statement = statement.where(StoryClusterModel.importance_score >= min_importance)

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

    async def bulk_update_ranking(
        self,
        updates: list[tuple[UUID, float, str]],
    ) -> None:
        from sqlalchemy import update as sa_update

        if not updates:
            return

        for cluster_id, score, explanation in updates:
            statement = (
                sa_update(StoryClusterModel)
                .where(StoryClusterModel.id == str(cluster_id))
                .values(
                    ranking_score=score,
                    ranking_explanation=explanation,
                )
            )
            await self._session.execute(statement)

        await self._commit()

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

    async def get_by_ids(
        self,
        cluster_ids: list[UUID],
    ) -> list[StoryCluster]:
        if not cluster_ids:
            return []
        statement = select(StoryClusterModel).where(
            StoryClusterModel.id.in_([str(cid) for cid in cluster_ids])
        )
        result = await self._session.execute(statement)
        return [StoryClusterMapper.to_domain(model) for model in result.scalars().all()]


__all__ = ["StoryClusterRepository"]
