from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from ai_news_digest.application.services.rss.parser.models import ParsedArticle
    from ai_news_digest.domain.enums.article_status import ArticleStatus
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
        offset: int = 0,
    ) -> list[Article]:
        """
        Return the most recently published articles.
        """
        raise NotImplementedError

    @abstractmethod
    async def list_by_status(
        self,
        status: ArticleStatus,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Article]:
        """
        Return articles with the given status, ordered by published_at desc.
        """
        raise NotImplementedError

    @abstractmethod
    async def list_digest_eligible(
        self,
        limit: int | None = None,
    ) -> list[Article]:
        """
        Return articles ready to be included in a digest.

        The repository should apply eligibility filtering at the database layer
        whenever possible so the application does not need to load unrelated
        data for selection.
        """
        raise NotImplementedError

    @abstractmethod
    async def mark_status_bulk(
        self,
        article_ids: list[UUID],
        status: ArticleStatus,
    ) -> int:
        """Bulk-update the status of multiple articles in a single transaction.

        Used by digest generation to mark included articles as READY
        atomically, avoiding partial-commit data loss.
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

    @abstractmethod
    async def count(self) -> int:
        """Return the total number of articles."""
        raise NotImplementedError

    @abstractmethod
    async def list_public_articles(
        self,
        limit: int = 100,
        offset: int = 0,
        category_id: UUID | None = None,
        source_id: UUID | None = None,
        search: str | None = None,
    ) -> list[Article]:
        """
        Return publicly visible articles with optional filtering.

        Only articles beyond the NEW/FAILED processing stages are returned so
        the public surface never exposes raw, unprocessed items.
        """
        raise NotImplementedError

    @abstractmethod
    async def count_public_articles(
        self,
        category_id: UUID | None = None,
        source_id: UUID | None = None,
        search: str | None = None,
    ) -> int:
        """Count publicly visible articles matching the given filters."""
        raise NotImplementedError

    @abstractmethod
    async def get_public_article(
        self,
        article_id: UUID,
    ) -> Article | None:
        """
        Return a single publicly visible article by ID.

        Only articles beyond the NEW/FAILED processing stages are returned so
        the public surface never exposes raw, unprocessed items.
        """
        raise NotImplementedError

    @abstractmethod
    async def delete_older_than(
        self,
        cutoff_date: datetime,
        limit: int = 1000,
    ) -> int:
        """Delete articles older than the cutoff date, returning the count deleted."""
        raise NotImplementedError
