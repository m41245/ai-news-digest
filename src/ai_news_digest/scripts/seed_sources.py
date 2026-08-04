from __future__ import annotations

import asyncio

from ai_news_digest.bootstrap.container import Container
from ai_news_digest.domain.models.source import Source
from ai_news_digest.infrastructure.database.session import get_db_session

DEFAULT_SOURCES = [
    {
        "name": "OpenAI",
        "feed_url": "https://openai.com/news/rss.xml",
        "website_url": "https://openai.com",
        "description": "Official OpenAI News",
    },
    {
        "name": "Anthropic",
        "feed_url": "https://www.anthropic.com/news/rss.xml",
        "website_url": "https://www.anthropic.com",
        "description": "Official Anthropic News",
    },
    {
        "name": "Hugging Face",
        "feed_url": "https://huggingface.co/blog/feed.xml",
        "website_url": "https://huggingface.co",
        "description": "Hugging Face Blog",
    },
    {
        "name": "TechCrunch AI",
        "feed_url": "https://techcrunch.com/category/artificial-intelligence/feed/",
        "website_url": "https://techcrunch.com",
        "description": "TechCrunch AI",
    },
    {
        "name": "MIT Technology Review AI",
        "feed_url": "https://www.technologyreview.com/topic/artificial-intelligence/feed/",
        "website_url": "https://www.technologyreview.com",
        "description": "MIT Technology Review AI",
    },
    {
        "name": "Python Software Foundation",
        "feed_url": "https://pyfound.blogspot.com/feeds/posts/default",
        "website_url": "https://www.python.org",
        "description": "Official Python News",
    },
]


async def main() -> None:
    print("Starting database seeding...\n")

    async for session in get_db_session():
        container = Container(session)

        repository = container.source_repository

        inserted = 0
        skipped = 0

        for item in DEFAULT_SOURCES:
            existing = await repository.get_by_feed_url(
                item["feed_url"],
            )

            if existing is not None:
                skipped += 1
                continue

            source = Source.create(
                name=item["name"],
                feed_url=item["feed_url"],
                website_url=item["website_url"],
                description=item["description"],
            )

            await repository.create(source)

            inserted += 1

        print("=" * 50)
        print("Database Seed Complete")
        print("=" * 50)
        print(f"Inserted : {inserted}")
        print(f"Skipped  : {skipped}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
