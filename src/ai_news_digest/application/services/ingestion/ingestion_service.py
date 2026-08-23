from __future__ import annotations

import logging

from ai_news_digest.application.services.ingestion.models import IngestionResult
from ai_news_digest.application.services.rss.exceptions import RSSException
from ai_news_digest.application.services.rss.feed_service import FeedService
from ai_news_digest.application.services.rss.models import FeedResult
from ai_news_digest.domain.ports.article_repository import ArticleRepository
from ai_news_digest.domain.ports.source_repository import SourceRepository

logger = logging.getLogger(__name__)


class IngestionService:
    """
    Coordinates the complete RSS ingestion workflow.

    Responsibilities:
        - Retrieve active sources.
        - Download and parse RSS feeds.
        - Skip duplicate articles.
        - Persist new articles.
        - Return ingestion statistics.

    This service intentionally contains no HTTP, XML, or database logic.
    """

    def __init__(
        self,
        source_repository: SourceRepository,
        article_repository: ArticleRepository,
        feed_service: FeedService,
    ) -> None:
        self._source_repository = source_repository
        self._article_repository = article_repository
        self._feed_service = feed_service

    async def ingest(self) -> IngestionResult:
        """
        Execute a full ingestion cycle for all active sources.
        """

        processed_sources = 0
        failed_sources = 0
        fetched_articles = 0
        new_articles = 0
        existing_articles = 0

        sources = await self._source_repository.list_active()

        logger.info(
            "Starting ingestion for %d active sources.",
            len(sources),
        )

        for source in sources:
            try:
                logger.info(
                    "Fetching feed: %s",
                    source.name,
                )

                result: FeedResult = await self._feed_service.fetch(
                    source.feed_url,
                )

                processed_sources += 1
                fetched_articles += len(result.articles)

                for article in result.articles:
                    existing = await self._article_repository.get_by_url(
                        article.url,
                    )

                    if existing is not None:
                        existing_articles += 1
                        continue

                    await self._article_repository.create_from_parsed(
                        source_id=source.id,
                        article=article,
                    )

                    new_articles += 1

            except RSSException:
                failed_sources += 1

                logger.exception(
                    "Failed to ingest feed '%s'.",
                    source.name,
                )

        logger.info(
            ("Ingestion complete. Processed=%d Failed=%d Fetched=%d New=%d Existing=%d"),
            processed_sources,
            failed_sources,
            fetched_articles,
            new_articles,
            existing_articles,
        )

        return IngestionResult(
            feeds_processed=processed_sources,
            failed_feeds=failed_sources,
            articles_fetched=fetched_articles,
            articles_inserted=new_articles,
            articles_skipped=existing_articles,
        )
