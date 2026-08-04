from __future__ import annotations

import asyncio
import traceback

from ai_news_digest.application.services.ingestion.ingestion_service import (
    IngestionService,
)
from ai_news_digest.application.services.rss.feed_service import FeedService
from ai_news_digest.application.services.rss.parser.rss_parser import RSSParser
from ai_news_digest.application.services.rss.rss_client import RSSClient
from ai_news_digest.infrastructure.database.repositories.article_repository import (
    ArticleRepository,
)
from ai_news_digest.infrastructure.database.repositories.source_repository import (
    SourceRepository,
)
from ai_news_digest.infrastructure.database.session import SessionLocal


async def main() -> None:
    print("=" * 60)
    print("AI News Digest")
    print("=" * 60)
    print()

    try:
        print("[1/6] Opening database session...")

        async with SessionLocal() as session:
            print("[2/6] Creating repositories...")

            source_repository = SourceRepository(session)
            article_repository = ArticleRepository(session)

            print("[3/6] Creating RSS services...")

            rss_client = RSSClient()
            rss_parser = RSSParser()

            feed_service = FeedService(
                client=rss_client,
                parser=rss_parser,
            )

            print("[4/6] Creating ingestion service...")

            ingestion_service = IngestionService(
                source_repository=source_repository,
                article_repository=article_repository,
                feed_service=feed_service,
            )

            print("[5/6] Starting ingestion...")
            print("      (If it stops here, the issue is inside the ingestion pipeline.)")
            print()

            result = await ingestion_service.ingest()

            print()
            print("[6/6] Ingestion completed successfully.")
            print()

        print("=" * 60)
        print("RESULT")
        print("=" * 60)
        print(f"Feeds processed : {result.feeds_processed}")
        print(f"Articles fetched: {result.articles_fetched}")
        print(f"Inserted        : {result.articles_inserted}")
        print(f"Skipped         : {result.articles_skipped}")
        print(f"Failed feeds    : {result.failed_feeds}")
        print("=" * 60)

    except KeyboardInterrupt:
        print()
        print("Execution cancelled by user (Ctrl+C).")

    except Exception:
        print()
        print("=" * 60)
        print("UNHANDLED EXCEPTION")
        print("=" * 60)
        traceback.print_exc()
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())