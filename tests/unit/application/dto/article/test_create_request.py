"""
Unit tests for CreateArticleRequest DTO.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from ai_news_digest.application.dto.article.create_request import CreateArticleRequest


def test_create_article_request_with_all_fields() -> None:
    """Test CreateArticleRequest with all fields."""
    request = CreateArticleRequest(
        title="Test Article",
        url="https://example.com/article",
        summary="Test summary",
        content="Test content",
        source_id="source-123",
        published_at="2024-01-01T00:00:00Z",
        category_id="category-123",
    )

    assert request.title == "Test Article"
    assert request.url == "https://example.com/article"
    assert request.summary == "Test summary"
    assert request.content == "Test content"
    assert request.source_id == "source-123"
    assert request.published_at == "2024-01-01T00:00:00Z"
    assert request.category_id == "category-123"


def test_create_article_request_without_category() -> None:
    """Test CreateArticleRequest without category_id."""
    request = CreateArticleRequest(
        title="Test Article",
        url="https://example.com/article",
        summary="Test summary",
        content="Test content",
        source_id="source-123",
        published_at="2024-01-01T00:00:00Z",
    )

    assert request.category_id is None


def test_create_article_request_without_content() -> None:
    """Test CreateArticleRequest without content."""
    request = CreateArticleRequest(
        title="Test Article",
        url="https://example.com/article",
        summary="Test summary",
        content=None,
        source_id="source-123",
        published_at="2024-01-01T00:00:00Z",
    )

    assert request.content is None


def test_create_article_request_frozen() -> None:
    """Test CreateArticleRequest is frozen."""
    request = CreateArticleRequest(
        title="Test Article",
        url="https://example.com/article",
        summary="Test summary",
        content="Test content",
        source_id="source-123",
        published_at="2024-01-01T00:00:00Z",
    )

    with pytest.raises(FrozenInstanceError):
        request.title = "New Title"
