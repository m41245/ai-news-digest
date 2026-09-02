"""
Factory for creating SQLAlchemy model instances in tests.
"""

from __future__ import annotations

from datetime import UTC, datetime

from ai_news_digest.infrastructure.database.models.article_model import ArticleModel
from ai_news_digest.infrastructure.database.models.category_model import CategoryModel
from ai_news_digest.infrastructure.database.models.digest_model import DigestModel
from ai_news_digest.infrastructure.database.models.source_model import SourceModel


def create_article_model(
    *,
    entity_id: str | None = None,
    title: str = "Test Article",
    url: str = "https://example.com/test-article",
    summary: str = "Test summary",
    content: str | None = "Test content",
    source_id: str,
    category_id: str | None = None,
    status: str = "new",
    published_at: datetime | None = None,
    fetched_at: datetime | None = None,
) -> ArticleModel:
    """
    Create a test ArticleModel instance.

    Args:
        entity_id: Optional article ID
        title: Article title
        url: Article URL
        summary: Article summary
        content: Optional article content
        source_id: Source ID
        category_id: Optional category ID
        status: Article status string
        published_at: Publication datetime
        fetched_at: Fetch datetime

    Returns:
        ArticleModel instance
    """
    now = datetime.now(UTC)

    if published_at is None:
        published_at = now

    if fetched_at is None:
        fetched_at = now

    return ArticleModel(
        id=entity_id,
        title=title,
        url=url,
        summary=summary,
        content=content,
        source_id=source_id,
        category_id=category_id,
        status=status,
        published_at=published_at,
        fetched_at=fetched_at,
        created_at=now,
        updated_at=now,
    )


def create_source_model(
    *,
    entity_id: str | None = None,
    name: str = "Test Source",
    feed_url: str = "https://example.com/feed.xml",
    description: str | None = "Test description",
    is_active: bool = True,
) -> SourceModel:
    """
    Create a test SourceModel instance.

    Args:
        entity_id: Optional source ID
        name: Source name
        feed_url: RSS feed URL
        description: Optional description
        is_active: Whether the source is active

    Returns:
        SourceModel instance
    """
    now = datetime.now(UTC)

    return SourceModel(
        id=entity_id,
        name=name,
        feed_url=feed_url,
        description=description,
        is_active=is_active,
        created_at=now,
        updated_at=now,
    )


def create_category_model(
    *,
    entity_id: str | None = None,
    name: str = "Test Category",
    description: str | None = "Test description",
) -> CategoryModel:
    """
    Create a test CategoryModel instance.

    Args:
        entity_id: Optional category ID
        name: Category name
        description: Optional description

    Returns:
        CategoryModel instance
    """
    now = datetime.now(UTC)

    return CategoryModel(
        id=entity_id,
        name=name,
        description=description,
        created_at=now,
        updated_at=now,
    )


def create_digest_model(
    *,
    entity_id: str | None = None,
    title: str = "Test Digest",
    content: str = "Test digest content",
    digest_format: str = "markdown",
    generated_at: datetime | None = None,
) -> DigestModel:
    """
    Create a test DigestModel instance.

    Args:
        entity_id: Optional digest ID
        title: Digest title
        content: Digest content
        digest_format: Digest format string
        generated_at: Generation datetime

    Returns:
        DigestModel instance
    """
    now = datetime.now(UTC)

    if generated_at is None:
        generated_at = now

    return DigestModel(
        id=entity_id,
        title=title,
        content=content,
        format=digest_format,
        generated_at=generated_at,
        created_at=now,
        updated_at=now,
    )
