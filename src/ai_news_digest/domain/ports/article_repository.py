from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from ai_news_digest.application.services.rss.parser.models import ParsedArticle
    from ai_news_digest.domain.models.article import Article


class ArticleRepository(ABC):
    """
    Port for persisting and retrieving articles.
    """

    @abstractmethod
    async def create(
        self,
        article: Article,
    ) -> Article:
        raise NotImplementedError

    @abstractmethod
    async def create_from_parsed(
        self,
        *,
        source_id: UUID,
        article: ParsedArticle,
    ) -> Article:
        """
        Persist a ParsedArticle directly from the RSS pipeline.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(
        self,
        article_id: UUID,
    ) -> Article | None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_url(
        self,
        url: str,
    ) -> Article | None:
        raise NotImplementedError

    @abstractmethod
    async def list_recent(
        self,
        limit: int = 100,
    ) -> list[Article]:
        """
        Return the most recently published articles.
        """
        raise NotImplementedError

    @abstractmethod
    async def update(
        self,
        article: Article,
    ) -> Article:
        raise NotImplementedError

    @abstractmethod
    async def delete(
        self,
        article_id: UUID,
    ) -> None:
        raise NotImplementedError
