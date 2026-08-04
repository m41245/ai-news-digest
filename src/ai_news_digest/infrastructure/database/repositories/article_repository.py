from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_news_digest.application.services.rss.parser.models import ParsedArticle
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
    ) -> list[Article]:
        statement = (
            select(ArticleModel)
            .order_by(ArticleModel.published_at.desc())
            .limit(limit)
        )

        result = await self._session.execute(statement)

        return [
            ArticleMapper.to_domain(model)
            for model in result.scalars().all()
        ]

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
            raise ValueError(
                f"Article with id '{article.id}' was not found."
            )

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
