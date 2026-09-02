"""
Unit tests for UpdateArticleRequest DTO.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from ai_news_digest.application.dto.article.update_request import UpdateArticleRequest


def test_update_article_request_with_all_fields() -> None:
    """Test UpdateArticleRequest with all fields."""
    request = UpdateArticleRequest(
        id="article-123",
        title="Updated Title",
        summary="Updated summary",
        content="Updated content",
        category_id="category-123",
    )

    assert request.id == "article-123"
    assert request.title == "Updated Title"
    assert request.summary == "Updated summary"
    assert request.content == "Updated content"
    assert request.category_id == "category-123"


def test_update_article_request_with_id_only() -> None:
    """Test UpdateArticleRequest with only id field."""
    request = UpdateArticleRequest(id="article-123")

    assert request.id == "article-123"
    assert request.title is None
    assert request.summary is None
    assert request.content is None
    assert request.category_id is None


def test_update_article_request_with_partial_fields() -> None:
    """Test UpdateArticleRequest with partial fields."""
    request = UpdateArticleRequest(
        id="article-123",
        title="Updated Title",
    )

    assert request.id == "article-123"
    assert request.title == "Updated Title"
    assert request.summary is None
    assert request.content is None
    assert request.category_id is None


def test_update_article_request_frozen() -> None:
    """Test UpdateArticleRequest is frozen."""
    request = UpdateArticleRequest(id="article-123")

    with pytest.raises(FrozenInstanceError):
        request.title = "New Title"
