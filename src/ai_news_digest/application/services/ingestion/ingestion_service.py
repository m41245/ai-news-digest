from __future__ import annotations

import time

from ai_news_digest.application.services.ingestion.models import IngestionResult
from ai_news_digest.application.services.rss.feed_service import FeedService
from ai_news_digest.application.services.rss.models import FeedResult
from ai_news_digest.domain.ports.article_repository import ArticleRepository
from ai_news_digest.domain.ports.source_repository import SourceRepository


class IngestionService:
    """
    Coordinates the complete RSS ingestion workflow.
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
        feeds_processed = 0
        failed_feeds = 0
        articles_fetched = 0
        articles_inserted = 0
        articles_skipped = 0

        sources = await self._source_repository.list_active()

        print(f"Sources: {len(sources)}")

        for source in sources:
            print(f"\n=== {source.name} ===")

            try:
                t0 = time.perf_counter()

                result: FeedResult = await self._feed_service.fetch(
                    source.feed_url,
                )

                print(f"Fetch: {time.perf_counter() - t0:.3f}s")

                feeds_processed += 1
                articles_fetched += len(result.articles)

                for article in result.articles:
                    t1 = time.perf_counter()

                    existing = await self._article_repository.get_by_url(
                        article.url,
                    )

                    lookup_time = time.perf_counter() - t1

                    if lookup_time > 1:
                        print(
                            f"Lookup took {lookup_time:.2f}s\n"
                            f"{article.url}"
                        )

                    if existing:
                        articles_skipped += 1
                        continue

                    t2 = time.perf_counter()

                    await self._article_repository.create_from_parsed(
                        source_id=source.id,
                        article=article,
                    )

                    insert_time = time.perf_counter() - t2

                    if insert_time > 1:
                        print(
                            f"Insert took {insert_time:.2f}s\n"
                            f"{article.url}"
                        )

                    articles_inserted += 1

            except Exception as exc:
                failed_feeds += 1
                print(exc)

        return IngestionResult(
            feeds_processed=feeds_processed,
            articles_fetched=articles_fetched,
            articles_inserted=articles_inserted,
            articles_skipped=articles_skipped,
            failed_feeds=failed_feeds,
        )