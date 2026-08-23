"""
Unit tests for Article domain model.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from ai_news_digest.domain.enums.article_status import ArticleStatus
from ai_news_digest.domain.models.article import Article


def test_article_create_with_all_fields() -> None:
    """Test Article.create with all fields."""
    source_id = uuid4()
    category_id = uuid4()
    published_at = datetime.now(UTC)

    article = Article.create(
        title="Test Article",
        url="https://example.com/article",
        summary="Test summary",
        content="Test content",
        source_id=source_id,
        published_at=published_at,
        category_id=category_id,
    )

    assert article.id is not None
    assert article.title == "Test Article"
    assert article.url == "https://example.com/article"
    assert article.summary == "Test summary"
    assert article.content == "Test content"
    assert article.source_id == source_id
    assert article.category_id == category_id
    assert article.published_at == published_at
    assert article.fetched_at is not None
    assert article.status == ArticleStatus.NEW


def test_article_create_without_category() -> None:
    """Test Article.create without category_id."""
    source_id = uuid4()
    published_at = datetime.now(UTC)

    article = Article.create(
        title="Test Article",
        url="https://example.com/article",
        summary="Test summary",
        content=None,
        source_id=source_id,
        published_at=published_at,
    )

    assert article.category_id is None


def test_article_create_without_content() -> None:
    """Test Article.create without content."""
    source_id = uuid4()
    published_at = datetime.now(UTC)

    article = Article.create(
        title="Test Article",
        url="https://example.com/article",
        summary="Test summary",
        content=None,
        source_id=source_id,
        published_at=published_at,
    )

    assert article.content is None


def test_article_create_generates_id() -> None:
    """Test Article.create generates unique IDs."""
    source_id = uuid4()
    published_at = datetime.now(UTC)

    article1 = Article.create(
        title="Article 1",
        url="https://example.com/article1",
        summary="Summary 1",
        content=None,
        source_id=source_id,
        published_at=published_at,
    )

    article2 = Article.create(
        title="Article 2",
        url="https://example.com/article2",
        summary="Summary 2",
        content=None,
        source_id=source_id,
        published_at=published_at,
    )

    assert article1.id != article2.id


def test_article_create_sets_fetched_at() -> None:
    """Test Article.create sets fetched_at to current time."""
    source_id = uuid4()
    published_at = datetime.now(UTC)

    before = datetime.now(UTC)
    article = Article.create(
        title="Test Article",
        url="https://example.com/article",
        summary="Test summary",
        content=None,
        source_id=source_id,
        published_at=published_at,
    )
    after = datetime.now(UTC)

    assert before <= article.fetched_at <= after


def test_article_create_sets_status_to_new() -> None:
    """Test Article.create sets status to NEW."""
    source_id = uuid4()
    published_at = datetime.now(UTC)

    article = Article.create(
        title="Test Article",
        url="https://example.com/article",
        summary="Test summary",
        content=None,
        source_id=source_id,
        published_at=published_at,
    )

    assert article.status == ArticleStatus.NEW
