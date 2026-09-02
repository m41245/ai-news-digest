"""
Unit tests for ArticleResponse DTO.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from ai_news_digest.application.dto.article.response import ArticleResponse


def test_article_response_with_all_fields() -> None:
    """Test ArticleResponse with all fields."""
    response = ArticleResponse(
        id="article-123",
        title="Test Article",
        url="https://example.com/article",
        summary="Test summary",
        content="Test content",
        source_id="source-123",
        category_id="category-123",
        published_at="2024-01-01T00:00:00Z",
        fetched_at="2024-01-01T00:00:00Z",
        status="pending",
    )

    assert response.id == "article-123"
    assert response.title == "Test Article"
    assert response.url == "https://example.com/article"
    assert response.summary == "Test summary"
    assert response.content == "Test content"
    assert response.source_id == "source-123"
    assert response.category_id == "category-123"
    assert response.published_at == "2024-01-01T00:00:00Z"
    assert response.fetched_at == "2024-01-01T00:00:00Z"
    assert response.status == "pending"


def test_article_response_without_category() -> None:
    """Test ArticleResponse without category_id."""
    response = ArticleResponse(
        id="article-123",
        title="Test Article",
        url="https://example.com/article",
        summary="Test summary",
        content="Test content",
        source_id="source-123",
        category_id=None,
        published_at="2024-01-01T00:00:00Z",
        fetched_at="2024-01-01T00:00:00Z",
        status="pending",
    )

    assert response.category_id is None


def test_article_response_without_content() -> None:
    """Test ArticleResponse without content."""
    response = ArticleResponse(
        id="article-123",
        title="Test Article",
        url="https://example.com/article",
        summary="Test summary",
        content=None,
        source_id="source-123",
        category_id=None,
        published_at="2024-01-01T00:00:00Z",
        fetched_at="2024-01-01T00:00:00Z",
        status="pending",
    )

    assert response.content is None


def test_article_response_frozen() -> None:
    """Test ArticleResponse is frozen."""
    response = ArticleResponse(
        id="article-123",
        title="Test Article",
        url="https://example.com/article",
        summary="Test summary",
        content="Test content",
        source_id="source-123",
        category_id=None,
        published_at="2024-01-01T00:00:00Z",
        fetched_at="2024-01-01T00:00:00Z",
        status="pending",
    )

    with pytest.raises(FrozenInstanceError):
        response.title = "New Title"
