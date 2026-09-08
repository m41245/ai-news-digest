from __future__ import annotations

from datetime import datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import func, or_, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ai_news_digest.application.services.rss.parser.models import ParsedArticle
from ai_news_digest.core.exceptions import ResourceNotFoundError
from ai_news_digest.domain.enums.article_status import ArticleStatus
from ai_news_digest.domain.models.article import Article
from ai_news_digest.domain.ports.article_repository import (
    ArticleRepository as ArticleRepositoryPort,
)
from ai_news_digest.infrastructure.database.mappers.article_mapper import (
    ArticleMapper,
)
from ai_news_digest.infrastructure.database.models.article_category_model import (
    ArticleCategoryModel,
)
from ai_news_digest.infrastructure.database.models.article_company_model import (
    ArticleCompanyModel,
)
from ai_news_digest.infrastructure.database.models.article_model import (
    ArticleModel,
)
from ai_news_digest.infrastructure.database.models.article_topic_model import (
    ArticleTopicModel,
)
from ai_news_digest.infrastructure.database.repositories.base_repository import (
    BaseRepository,
)


class ArticleRepository(
    BaseRepository[ArticleModel],
    ArticleRepositoryPort,
):
    """
    SQLAlchemy implementation of the ArticleRepository port.
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        super().__init__(session)

    async def create(
        self,
        article: Article,
    ) -> Article:
        model = ArticleMapper.to_model(article)
        model = await self._add_and_refresh(model)
        return ArticleMapper.to_domain(model)

    async def create_from_parsed(
        self,
        *,
        source_id: UUID,
        article: ParsedArticle,
    ) -> Article:
        """
        Persist a parsed RSS article.
        """
        domain_article = Article.create(
            title=article.title,
            url=article.url,
            summary=article.summary,
            content=None,
            source_id=source_id,
            published_at=article.published_at,
        )

        return await self.create(domain_article)

    async def get_by_id(
        self,
        article_id: UUID,
    ) -> Article | None:
        statement = (
            select(ArticleModel)
            .options(
                selectinload(ArticleModel.source),
                selectinload(ArticleModel.category),
                selectinload(ArticleModel.company_links),
                selectinload(ArticleModel.topic_links),
                selectinload(ArticleModel.category_links),
            )
            .where(ArticleModel.id == str(article_id))
        )

        result = await self._session.execute(statement)

        model = result.scalar_one_or_none()

        if model is None:
            return None

        return ArticleMapper.to_domain(model)

    async def get_by_url(
        self,
        url: str,
    ) -> Article | None:
        statement = select(ArticleModel).where(
            ArticleModel.url == url,
        )

        result = await self._session.execute(statement)

        model = result.scalar_one_or_none()

        if model is None:
            return None

        return ArticleMapper.to_domain(model)

    async def list_recent(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Article]:
        statement = (
            select(ArticleModel)
            .options(
                selectinload(ArticleModel.source),
                selectinload(ArticleModel.category),
                selectinload(ArticleModel.company_links),
                selectinload(ArticleModel.topic_links),
                selectinload(ArticleModel.category_links),
            )
            .order_by(ArticleModel.published_at.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await self._session.execute(statement)

        return [ArticleMapper.to_domain(model) for model in result.scalars().all()]

    async def list_by_status(
        self,
        status: ArticleStatus,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Article]:
        statement = (
            select(ArticleModel)
            .options(
                selectinload(ArticleModel.source),
                selectinload(ArticleModel.category),
                selectinload(ArticleModel.company_links),
                selectinload(ArticleModel.topic_links),
                selectinload(ArticleModel.category_links),
            )
            .where(ArticleModel.status == status.value)
            .order_by(ArticleModel.published_at.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await self._session.execute(statement)

        return [ArticleMapper.to_domain(model) for model in result.scalars().all()]

    async def list_digest_eligible(
        self,
        limit: int | None = None,
    ) -> list[Article]:
        statement = (
            select(ArticleModel)
            .options(
                selectinload(ArticleModel.source),
                selectinload(ArticleModel.category),
                selectinload(ArticleModel.company_links),
                selectinload(ArticleModel.topic_links),
                selectinload(ArticleModel.category_links),
            )
            .where(
                ArticleModel.status.in_(
                    [
                        ArticleStatus.SUMMARIZED,
                        ArticleStatus.CATEGORIZED,
                        ArticleStatus.ANALYZED,
                    ]
                )
            )
            .order_by(
                ArticleModel.published_at.desc(),
                ArticleModel.id.asc(),
            )
        )

        if limit is not None:
            statement = statement.limit(limit)

        result = await self._session.execute(statement)

        return [ArticleMapper.to_domain(model) for model in result.scalars().all()]

    async def mark_status_bulk(
        self,
        article_ids: list[UUID],
        status: ArticleStatus,
    ) -> int:
        """Bulk-update the status of multiple articles in a single transaction."""
        if not article_ids:
            return 0

        statement = (
            update(ArticleModel)
            .where(
                ArticleModel.id.in_([str(a) for a in article_ids]),
                ArticleModel.status.not_in(
                    [ArticleStatus.READY.value, ArticleStatus.FAILED.value],
                ),
            )
            .values(status=status.value)
        )
        result = cast(CursorResult[Any], await self._session.execute(statement))
        return result.rowcount

    async def update(
        self,
        article: Article,
    ) -> Article:
        statement = select(ArticleModel).where(
            ArticleModel.id == str(article.id),
        )

        result = await self._session.execute(statement)

        model = result.scalar_one_or_none()

        if model is None:
            raise ResourceNotFoundError(f"Article with id '{article.id}' was not found.")

        ArticleMapper.update_model(
            model,
            article,
        )

        await self._commit()

        model = await self._refresh(model)

        return ArticleMapper.to_domain(model)

    async def delete(
        self,
        article_id: UUID,
    ) -> None:
        statement = select(ArticleModel).where(
            ArticleModel.id == str(article_id),
        )

        result = await self._session.execute(statement)

        model = result.scalar_one_or_none()

        if model is None:
            return

        await self._delete(model)

    async def count(self) -> int:
        statement = select(func.count()).select_from(ArticleModel)
        result = await self._session.execute(statement)
        return int(result.scalar_one())

    async def list_by_cluster_id(
        self,
        cluster_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Article]:
        statement = (
            select(ArticleModel)
            .options(
                selectinload(ArticleModel.source),
                selectinload(ArticleModel.category),
                selectinload(ArticleModel.company_links),
                selectinload(ArticleModel.topic_links),
                selectinload(ArticleModel.category_links),
            )
            .where(ArticleModel.cluster_id == str(cluster_id))
            .order_by(ArticleModel.published_at.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await self._session.execute(statement)

        return [ArticleMapper.to_domain(model) for model in result.scalars().all()]

    async def list_public_articles(
        self,
        limit: int = 100,
        offset: int = 0,
        category_id: UUID | None = None,
        source_id: UUID | None = None,
        company_id: UUID | None = None,
        topic_id: UUID | None = None,
        min_importance: float | None = None,
        published_from: datetime | None = None,
        published_to: datetime | None = None,
        search: str | None = None,
        order_by: str = "published_at",
    ) -> list[Article]:
        statement = (
            select(ArticleModel)
            .options(
                selectinload(ArticleModel.source),
                selectinload(ArticleModel.category),
                selectinload(ArticleModel.company_links),
                selectinload(ArticleModel.topic_links),
                selectinload(ArticleModel.category_links),
            )
            .where(
                ArticleModel.status.not_in(
                    [ArticleStatus.NEW, ArticleStatus.FAILED],
                ),
            )
        )

        statement = self._apply_public_filters(
            statement,
            category_id=category_id,
            source_id=source_id,
            company_id=company_id,
            topic_id=topic_id,
            min_importance=min_importance,
            published_from=published_from,
            published_to=published_to,
            search=search,
        )

        if order_by == "importance":
            statement = statement.order_by(
                ArticleModel.importance_score.desc().nulls_last(),
                ArticleModel.published_at.desc(),
            )
        else:
            statement = statement.order_by(ArticleModel.published_at.desc())

        statement = statement.limit(limit).offset(offset)

        result = await self._session.execute(statement)

        return [ArticleMapper.to_domain(model) for model in result.scalars().all()]

    async def count_public_articles(
        self,
        category_id: UUID | None = None,
        source_id: UUID | None = None,
        company_id: UUID | None = None,
        topic_id: UUID | None = None,
        min_importance: float | None = None,
        published_from: datetime | None = None,
        published_to: datetime | None = None,
        search: str | None = None,
    ) -> int:
        statement = (
            select(func.count())
            .select_from(ArticleModel)
            .where(
                ArticleModel.status.not_in(
                    [ArticleStatus.NEW, ArticleStatus.FAILED],
                ),
            )
        )

        statement = self._apply_public_filters(
            statement,
            category_id=category_id,
            source_id=source_id,
            company_id=company_id,
            topic_id=topic_id,
            min_importance=min_importance,
            published_from=published_from,
            published_to=published_to,
            search=search,
        )

        result = await self._session.execute(statement)

        return int(result.scalar_one())

    def _apply_public_filters(
        self,
        statement: Any,
        *,
        category_id: UUID | None,
        source_id: UUID | None,
        company_id: UUID | None,
        topic_id: UUID | None,
        min_importance: float | None,
        published_from: datetime | None,
        published_to: datetime | None,
        search: str | None,
    ) -> Any:
        from ai_news_digest.infrastructure.database.models.article_company_model import (
            ArticleCompanyModel,
        )
        from ai_news_digest.infrastructure.database.models.article_topic_model import (
            ArticleTopicModel,
        )

        if category_id is not None:
            statement = statement.where(ArticleModel.category_id == str(category_id))

        if source_id is not None:
            statement = statement.where(ArticleModel.source_id == str(source_id))

        if company_id is not None:
            statement = statement.where(
                ArticleModel.id.in_(
                    select(ArticleCompanyModel.article_id).where(
                        ArticleCompanyModel.company_id == str(company_id),
                    ),
                ),
            )

        if topic_id is not None:
            statement = statement.where(
                ArticleModel.id.in_(
                    select(ArticleTopicModel.article_id).where(
                        ArticleTopicModel.topic_id == str(topic_id),
                    ),
                ),
            )

        if min_importance is not None:
            statement = statement.where(ArticleModel.importance_score >= min_importance)

        if published_from is not None:
            statement = statement.where(ArticleModel.published_at >= published_from)

        if published_to is not None:
            statement = statement.where(ArticleModel.published_at <= published_to)

        if search:
            pattern = f"%{search}%"
            statement = statement.where(
                or_(
                    ArticleModel.title.ilike(pattern),
                    ArticleModel.summary.ilike(pattern),
                ),
            )

        return statement

    async def get_public_article(
        self,
        article_id: UUID,
    ) -> Article | None:
        statement = (
            select(ArticleModel)
            .options(
                selectinload(ArticleModel.source),
                selectinload(ArticleModel.category),
                selectinload(ArticleModel.company_links),
                selectinload(ArticleModel.topic_links),
                selectinload(ArticleModel.category_links),
            )
            .where(
                ArticleModel.id == str(article_id),
                ArticleModel.status.not_in(
                    [ArticleStatus.NEW, ArticleStatus.FAILED],
                ),
            )
        )

        result = await self._session.execute(statement)

        model = result.scalar_one_or_none()

        if model is None:
            return None

        return ArticleMapper.to_domain(model)

    async def list_public_articles_for_feed(
        self,
        limit: int = 100,
        offset: int = 0,
        min_importance: float | None = None,
        min_confidence: float | None = None,
        published_from: datetime | None = None,
        published_to: datetime | None = None,
    ) -> list[Article]:
        statement = (
            select(ArticleModel)
            .options(
                selectinload(ArticleModel.source),
                selectinload(ArticleModel.category),
                selectinload(ArticleModel.company_links),
                selectinload(ArticleModel.topic_links),
                selectinload(ArticleModel.category_links),
                selectinload(ArticleModel.cluster),
            )
            .where(
                ArticleModel.status.not_in(
                    [ArticleStatus.NEW, ArticleStatus.FAILED],
                ),
            )
        )

        if min_importance is not None:
            statement = statement.where(ArticleModel.importance_score >= min_importance)

        if min_confidence is not None:
            statement = statement.where(ArticleModel.confidence >= min_confidence)

        if published_from is not None:
            statement = statement.where(ArticleModel.published_at >= published_from)

        if published_to is not None:
            statement = statement.where(ArticleModel.published_at <= published_to)

        statement = statement.order_by(ArticleModel.published_at.desc()).limit(limit).offset(offset)

        result = await self._session.execute(statement)

        return [ArticleMapper.to_domain(model) for model in result.scalars().all()]

    async def list_personalized_feed_story_candidates(
        self,
        limit: int = 100,
        offset: int = 0,
        min_importance: float | None = None,
        min_confidence: float | None = None,
        published_from: datetime | None = None,
        published_to: datetime | None = None,
        muted_company_ids: list[UUID] | None = None,
        muted_topic_ids: list[UUID] | None = None,
        muted_category_ids: list[UUID] | None = None,
        followed_company_ids: list[UUID] | None = None,
        followed_topic_ids: list[UUID] | None = None,
        followed_category_ids: list[UUID] | None = None,
        preferred_source_type_ids: list[UUID] | None = None,
    ) -> list[Article]:
        from ai_news_digest.infrastructure.database.models.article_category_model import (
            ArticleCategoryModel,
        )
        from ai_news_digest.infrastructure.database.models.article_company_model import (
            ArticleCompanyModel,
        )
        from ai_news_digest.infrastructure.database.models.article_topic_model import (
            ArticleTopicModel,
        )

        cluster_latest = (
            select(
                ArticleModel.cluster_id,
                func.max(ArticleModel.published_at).label("max_published_at"),
            )
            .where(
                ArticleModel.status.not_in(
                    [ArticleStatus.NEW, ArticleStatus.FAILED],
                ),
                ArticleModel.cluster_id.is_not(None),
            )
            .group_by(ArticleModel.cluster_id)
            .subquery()
        )

        cluster_article_ids = (
            select(ArticleModel.id)
            .join(
                cluster_latest,
                ArticleModel.cluster_id == cluster_latest.c.cluster_id,
            )
            .where(ArticleModel.published_at == cluster_latest.c.max_published_at)
            .subquery()
        )

        standalone_ids = (
            select(ArticleModel.id)
            .where(
                ArticleModel.status.not_in(
                    [ArticleStatus.NEW, ArticleStatus.FAILED],
                ),
                ArticleModel.cluster_id.is_(None),
            )
            .subquery()
        )

        combined_ids = (
            select(cluster_article_ids.c.id).union_all(select(standalone_ids.c.id)).subquery()
        )

        statement = (
            select(ArticleModel)
            .options(
                selectinload(ArticleModel.source),
                selectinload(ArticleModel.category),
                selectinload(ArticleModel.company_links),
                selectinload(ArticleModel.topic_links),
                selectinload(ArticleModel.category_links),
                selectinload(ArticleModel.cluster),
            )
            .join(combined_ids, ArticleModel.id == combined_ids.c.id)
            .where(
                ArticleModel.status.not_in(
                    [ArticleStatus.NEW, ArticleStatus.FAILED],
                ),
            )
        )

        if min_importance is not None:
            statement = statement.where(ArticleModel.importance_score >= min_importance)

        if min_confidence is not None:
            statement = statement.where(ArticleModel.confidence >= min_confidence)

        if published_from is not None:
            statement = statement.where(ArticleModel.published_at >= published_from)

        if published_to is not None:
            statement = statement.where(ArticleModel.published_at <= published_to)

        if muted_company_ids:
            muted_strs = [str(cid) for cid in muted_company_ids]
            statement = statement.where(
                ArticleModel.id.not_in(
                    select(ArticleCompanyModel.article_id).where(
                        ArticleCompanyModel.company_id.in_(muted_strs),
                    ),
                ),
            )

        if muted_topic_ids:
            muted_strs = [str(tid) for tid in muted_topic_ids]
            statement = statement.where(
                ArticleModel.id.not_in(
                    select(ArticleTopicModel.article_id).where(
                        ArticleTopicModel.topic_id.in_(muted_strs),
                    ),
                ),
            )

        if muted_category_ids:
            muted_strs = [str(cid) for cid in muted_category_ids]
            statement = statement.where(
                ArticleModel.id.not_in(
                    select(ArticleCategoryModel.article_id).where(
                        ArticleCategoryModel.category_id.in_(muted_strs),
                    ),
                ),
            )

        statement = statement.order_by(ArticleModel.published_at.desc()).limit(limit).offset(offset)

        result = await self._session.execute(statement)

        return [ArticleMapper.to_domain(model) for model in result.scalars().all()]

    async def list_personalized_feed_candidates(
        self,
        limit: int = 100,
        offset: int = 0,
        min_importance: float | None = None,
        min_confidence: float | None = None,
        published_from: datetime | None = None,
        published_to: datetime | None = None,
        muted_company_ids: list[UUID] | None = None,
        muted_topic_ids: list[UUID] | None = None,
        muted_category_ids: list[UUID] | None = None,
        followed_company_ids: list[UUID] | None = None,
        followed_topic_ids: list[UUID] | None = None,
        followed_category_ids: list[UUID] | None = None,
        preferred_source_type_ids: list[UUID] | None = None,
    ) -> list[Article]:
        statement = (
            select(ArticleModel)
            .options(
                selectinload(ArticleModel.source),
                selectinload(ArticleModel.category),
                selectinload(ArticleModel.company_links),
                selectinload(ArticleModel.topic_links),
                selectinload(ArticleModel.category_links),
                selectinload(ArticleModel.cluster),
            )
            .where(
                ArticleModel.status.not_in(
                    [ArticleStatus.NEW, ArticleStatus.FAILED],
                ),
            )
        )

        if min_importance is not None:
            statement = statement.where(ArticleModel.importance_score >= min_importance)

        if min_confidence is not None:
            statement = statement.where(ArticleModel.confidence >= min_confidence)

        if published_from is not None:
            statement = statement.where(ArticleModel.published_at >= published_from)

        if published_to is not None:
            statement = statement.where(ArticleModel.published_at <= published_to)

        if muted_company_ids:
            muted_strs = [str(cid) for cid in muted_company_ids]
            statement = statement.where(
                ArticleModel.id.not_in(
                    select(ArticleCompanyModel.article_id).where(
                        ArticleCompanyModel.company_id.in_(muted_strs),
                    ),
                ),
            )

        if muted_topic_ids:
            muted_strs = [str(tid) for tid in muted_topic_ids]
            statement = statement.where(
                ArticleModel.id.not_in(
                    select(ArticleTopicModel.article_id).where(
                        ArticleTopicModel.topic_id.in_(muted_strs),
                    ),
                ),
            )

        if muted_category_ids:
            muted_strs = [str(cid) for cid in muted_category_ids]
            statement = statement.where(
                ArticleModel.id.not_in(
                    select(ArticleCategoryModel.article_id).where(
                        ArticleCategoryModel.category_id.in_(muted_strs),
                    ),
                ),
            )

        statement = statement.order_by(ArticleModel.published_at.desc()).limit(limit).offset(offset)

        result = await self._session.execute(statement)

        return [ArticleMapper.to_domain(model) for model in result.scalars().all()]

    async def count_personalized_feed_candidates(
        self,
        min_importance: float | None = None,
        min_confidence: float | None = None,
        published_from: datetime | None = None,
        published_to: datetime | None = None,
        muted_company_ids: list[UUID] | None = None,
        muted_topic_ids: list[UUID] | None = None,
        muted_category_ids: list[UUID] | None = None,
        followed_company_ids: list[UUID] | None = None,
        followed_topic_ids: list[UUID] | None = None,
        followed_category_ids: list[UUID] | None = None,
        preferred_source_type_ids: list[UUID] | None = None,
    ) -> int:
        statement = (
            select(func.count())
            .select_from(ArticleModel)
            .where(
                ArticleModel.status.not_in(
                    [ArticleStatus.NEW, ArticleStatus.FAILED],
                ),
            )
        )

        if min_importance is not None:
            statement = statement.where(ArticleModel.importance_score >= min_importance)

        if min_confidence is not None:
            statement = statement.where(ArticleModel.confidence >= min_confidence)

        if published_from is not None:
            statement = statement.where(ArticleModel.published_at >= published_from)

        if published_to is not None:
            statement = statement.where(ArticleModel.published_at <= published_to)

        if muted_company_ids:
            muted_strs = [str(cid) for cid in muted_company_ids]
            statement = statement.where(
                ArticleModel.id.not_in(
                    select(ArticleCompanyModel.article_id).where(
                        ArticleCompanyModel.company_id.in_(muted_strs),
                    ),
                ),
            )

        if muted_topic_ids:
            muted_strs = [str(tid) for tid in muted_topic_ids]
            statement = statement.where(
                ArticleModel.id.not_in(
                    select(ArticleTopicModel.article_id).where(
                        ArticleTopicModel.topic_id.in_(muted_strs),
                    ),
                ),
            )

        if muted_category_ids:
            muted_strs = [str(cid) for cid in muted_category_ids]
            statement = statement.where(
                ArticleModel.id.not_in(
                    select(ArticleCategoryModel.article_id).where(
                        ArticleCategoryModel.category_id.in_(muted_strs),
                    ),
                ),
            )

        result = await self._session.execute(statement)

        return int(result.scalar_one())

    async def delete_older_than(
        self,
        cutoff_date: datetime,
        limit: int = 1000,
    ) -> int:
        statement = select(ArticleModel).where(ArticleModel.published_at < cutoff_date).limit(limit)

        result = await self._session.execute(statement)
        models = result.scalars().all()

        for model in models:
            await self._session.delete(model)

        await self._commit()

        return len(models)

    async def replace_companies(
        self,
        article_id: UUID,
        company_ids: list[UUID],
    ) -> None:
        await self._replace_links(
            ArticleCompanyModel,
            ArticleCompanyModel.article_id,
            ArticleCompanyModel.company_id,
            article_id,
            company_ids,
        )

    async def replace_topics(
        self,
        article_id: UUID,
        topic_ids: list[UUID],
    ) -> None:
        await self._replace_links(
            ArticleTopicModel,
            ArticleTopicModel.article_id,
            ArticleTopicModel.topic_id,
            article_id,
            topic_ids,
        )

    async def replace_categories(
        self,
        article_id: UUID,
        category_ids: list[UUID],
    ) -> None:
        await self._replace_links(
            ArticleCategoryModel,
            ArticleCategoryModel.article_id,
            ArticleCategoryModel.category_id,
            article_id,
            category_ids,
        )

    async def set_cluster(
        self,
        article_id: UUID,
        cluster_id: UUID | None,
    ) -> None:
        statement = (
            update(ArticleModel)
            .where(ArticleModel.id == str(article_id))
            .values(cluster_id=(str(cluster_id) if cluster_id is not None else None))
        )
        await self._session.execute(statement)
        await self._commit()

    async def _replace_links(
        self,
        model_cls: type,
        article_id_col: Any,
        target_id_col: Any,
        article_id: UUID,
        target_ids: list[UUID],
    ) -> None:
        from sqlalchemy import delete

        await self._session.execute(delete(model_cls).where(article_id_col == str(article_id)))

        for target_id in target_ids:
            link = model_cls(
                article_id=str(article_id),
                **{target_id_col.name: str(target_id)},
            )
            self._session.add(link)

        await self._commit()
