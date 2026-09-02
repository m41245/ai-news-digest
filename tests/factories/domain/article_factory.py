"""
Factory for creating Article domain entities in tests.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from ai_news_digest.domain.enums.article_status import ArticleStatus
from ai_news_digest.domain.models.article import Article


def create_article(
    *,
    entity_id: str | None = None,
    title: str = "Test Article",
    url: str = "https://example.com/test-article",
    summary: str = "Test summary",
    content: str | None = "Test content",
    source_id: UUID | None = None,
    category_id: UUID | None = None,
    status: ArticleStatus = ArticleStatus.NEW,
    published_at: datetime | None = None,
) -> Article:
    """
    Create a test Article domain entity.

    Args:
        entity_id: Optional article ID
        title: Article title
        url: Article URL
        summary: Article summary
        content: Optional article content
        source_id: Source ID
        category_id: Optional category ID
        status: Article status
        published_at: Publication datetime

    Returns:
        Article domain entity
    """
    if source_id is None:
        source_id = uuid4()

    if published_at is None:
        published_at = datetime.now(UTC)

    article = Article.create(
        title=title,
        url=url,
        summary=summary,
        content=content,
        source_id=source_id,
        category_id=category_id,
        published_at=published_at,
    )

    if entity_id is not None:
        object.__setattr__(article, "id", entity_id)

    return article
