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
        company_id: UUID | None = None,
        topic_id: UUID | None = None,
        min_importance: float | None = None,
        published_from: datetime | None = None,
        published_to: datetime | None = None,
        search: str | None = None,
        order_by: str = "published_at",
    ) -> list[Article]:
        """
        Return publicly visible articles with optional filtering.

        Only articles beyond the NEW/FAILED processing stages are returned so
        the public surface never exposes raw, unprocessed items.

        `order_by` accepts ``"published_at"`` (default) or ``"importance"``.
        """
        raise NotImplementedError

    @abstractmethod
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

    @abstractmethod
    async def replace_companies(
        self,
        article_id: UUID,
        company_ids: list[UUID],
    ) -> None:
        """Replace the company links for an article with the given company ids."""
        raise NotImplementedError

    @abstractmethod
    async def replace_topics(
        self,
        article_id: UUID,
        topic_ids: list[UUID],
    ) -> None:
        """Replace the topic links for an article with the given topic ids."""
        raise NotImplementedError

    @abstractmethod
    async def replace_categories(
        self,
        article_id: UUID,
        category_ids: list[UUID],
    ) -> None:
        """Replace the category links for an article with the given category ids."""
        raise NotImplementedError

    @abstractmethod
    async def list_by_cluster_id(
        self,
        cluster_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Article]:
        """
        Return articles belonging to the given cluster, ordered by published_at desc.
        """
        raise NotImplementedError

    @abstractmethod
    async def set_cluster(
        self,
        article_id: UUID,
        cluster_id: UUID | None,
    ) -> None:
        """Set or clear the cluster for an article."""
        raise NotImplementedError

    @abstractmethod
    async def list_public_articles_for_feed(
        self,
        limit: int = 100,
        offset: int = 0,
        min_importance: float | None = None,
        min_confidence: float | None = None,
        published_from: datetime | None = None,
        published_to: datetime | None = None,
    ) -> list[Article]:
        """
        Return publicly visible articles with all relationships loaded for
        personalized feed ranking.
        """
        raise NotImplementedError

    @abstractmethod
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
        """
        Return story-level candidates for the personalized feed.

        Prefers the latest article per story cluster when clusters exist,
        falling back to standalone articles. Database-level filtering is
        applied where practical.
        """
        raise NotImplementedError

    @abstractmethod
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
        """
        Return candidate articles for the personalized feed with database-level
        filtering applied where practical.

        The implementation should push as much filtering as possible into the
        database to avoid loading unbounded result sets into application memory.
        """
        raise NotImplementedError

    @abstractmethod
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
        """Count personalized feed candidates matching the given filters."""
        raise NotImplementedError
