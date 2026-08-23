"""
Unit tests for Article domain model.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from ai_news_digest.domain.enums.article_status import ArticleStatus
from ai_news_digest.domain.models.article import Article


def test_article_creation():
    """Test that an Article can be created with valid parameters."""
    source_id = uuid4()
    published_at = datetime.now(UTC)

    article = Article.create(
        title="Test Article",
        url="https://example.com/article",
        summary="Test summary",
        content="Test content",
        source_id=source_id,
        category_id=None,
        published_at=published_at,
    )

    assert isinstance(article.id, UUID)
    assert article.title == "Test Article"
    assert article.url == "https://example.com/article"
    assert article.summary == "Test summary"
    assert article.content == "Test content"
    assert article.source_id == source_id
    assert article.category_id is None
    assert article.status == ArticleStatus.NEW
    assert article.published_at == published_at
    assert article.fetched_at is not None


def test_article_with_category():
    """Test that an Article can be created with a category."""
    source_id = uuid4()
    category_id = uuid4()
    published_at = datetime.now(UTC)

    article = Article.create(
        title="Test Article",
        url="https://example.com/article",
        summary="Test summary",
        content="Test content",
        source_id=source_id,
        category_id=category_id,
        published_at=published_at,
    )

    assert article.category_id == category_id


def test_article_without_content():
    """Test that an Article can be created without content."""
    source_id = uuid4()
    published_at = datetime.now(UTC)

    article = Article.create(
        title="Test Article",
        url="https://example.com/article",
        summary="Test summary",
        content=None,
        source_id=source_id,
        category_id=None,
        published_at=published_at,
    )

    assert article.content is None
