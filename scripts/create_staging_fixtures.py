"""Minimal safe staging fixtures for Step 2.2C validation."""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import asyncpg

STAGING_DB_URL = "postgresql://postgres:St4g1ng_P0stgr3s_S3cur3_Pw_2026!@localhost:5432/ai_news_digest_staging"


async def main() -> None:
    conn = await asyncpg.connect(STAGING_DB_URL)

    try:
        # Verify we are in staging
        db_name = await conn.fetchval("SELECT current_database()")
        if db_name != "ai_news_digest_staging":
            raise RuntimeError(f"Refusing to write fixtures to non-staging database: {db_name}")

        # Check existing data - if we have articles, we're good
        article_count = await conn.fetchval("SELECT count(*) FROM articles")
        if article_count > 0:
            print("Database already has articles, skipping fixture creation.")
            return

        # Ensure a verified source exists
        source_row = await conn.fetchrow(
            "SELECT id FROM sources WHERE name = $1", "Staging Tech News"
        )
        if source_row:
            source_id = source_row["id"]
            print(f"Using existing source: {source_id}")
        else:
            source_id = str(uuid4())
            await conn.execute(
                """
                INSERT INTO sources (id, name, feed_url, website_url,
                    description, is_active, status, source_type,
                    publisher, verification_notes, priority)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                """,
                source_id,
                "Staging Tech News",
                "https://example.com/staging-tech/rss.xml",
                "https://example.com/staging-tech",
                "A verified staging source for pipeline validation.",
                True,
                "verified",
                "tech_publication",
                "Staging Media",
                "Created for Step 2.2C staging validation.",
                10,
            )
            print(f"Created source: {source_id}")

        # Ensure a category exists
        category_row = await conn.fetchrow(
            "SELECT id FROM categories WHERE name = $1", "Technology"
        )
        if category_row:
            category_id = category_row["id"]
            print(f"Using existing category: {category_id}")
        else:
            category_id = str(uuid4())
            await conn.execute(
                """
                INSERT INTO categories (id, name, description)
                VALUES ($1, $2, $3)
                """,
                category_id,
                "Technology",
                "Technology news category.",
            )
            print(f"Created category: {category_id}")

        # Create 3 articles in NEW status
        articles = []
        now = datetime.now(UTC)
        for i in range(3):
            article_id = str(uuid4())
            published_at = now - timedelta(hours=i + 1)
            await conn.execute(
                """
                INSERT INTO articles (
                    id, source_id, category_id, title, url, summary, content,
                    status, published_at, fetched_at, extraction_method, extraction_quality
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                """,
                article_id,
                source_id,
                category_id,
                f"Staging Test Article {i + 1}",
                f"https://example.com/staging-tech/article-{i + 1}",
                f"This is a summary for staging test article {i + 1}. It covers a tech topic.",
                f"Full content for staging test article {i + 1}. "
                f"This is used to validate the direct runner pipeline.",
                "new",
                published_at,
                now,
                "rss",
                "full",
            )
            articles.append(article_id)
            print(f"Created article: {article_id}")

        print(
            f"\nFixture creation complete. Created 1 source, "
            f"1 category, {len(articles)} articles."
        )
        print("All data is safe staging-only test data.")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
