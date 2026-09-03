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
from ai_news_digest.infrastructure.database.models.article_model import (
    ArticleModel,
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
        statement = select(ArticleModel).where(
            ArticleModel.id == str(article_id),
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
            )
            .where(
                ArticleModel.status.in_(
                    [
                        ArticleStatus.SUMMARIZED,
                        ArticleStatus.CATEGORIZED,
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

    async def list_public_articles(
        self,
        limit: int = 100,
        offset: int = 0,
        category_id: UUID | None = None,
        source_id: UUID | None = None,
        search: str | None = None,
    ) -> list[Article]:
        statement = (
            select(ArticleModel)
            .options(
                selectinload(ArticleModel.source),
                selectinload(ArticleModel.category),
            )
            .where(
                ArticleModel.status.not_in(
                    [ArticleStatus.NEW, ArticleStatus.FAILED],
                ),
            )
            .order_by(ArticleModel.published_at.desc())
            .limit(limit)
            .offset(offset)
        )

        if category_id is not None:
            statement = statement.where(ArticleModel.category_id == str(category_id))

        if source_id is not None:
            statement = statement.where(ArticleModel.source_id == str(source_id))

        if search:
            pattern = f"%{search}%"
            statement = statement.where(
                or_(
                    ArticleModel.title.ilike(pattern),
                    ArticleModel.summary.ilike(pattern),
                ),
            )

        result = await self._session.execute(statement)

        return [ArticleMapper.to_domain(model) for model in result.scalars().all()]

    async def count_public_articles(
        self,
        category_id: UUID | None = None,
        source_id: UUID | None = None,
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

        if category_id is not None:
            statement = statement.where(ArticleModel.category_id == str(category_id))

        if source_id is not None:
            statement = statement.where(ArticleModel.source_id == str(source_id))

        if search:
            pattern = f"%{search}%"
            statement = statement.where(
                or_(
                    ArticleModel.title.ilike(pattern),
                    ArticleModel.summary.ilike(pattern),
                ),
            )

        result = await self._session.execute(statement)

        return int(result.scalar_one())

    async def get_public_article(
        self,
        article_id: UUID,
    ) -> Article | None:
        statement = (
            select(ArticleModel)
            .options(
                selectinload(ArticleModel.source),
                selectinload(ArticleModel.category),
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
