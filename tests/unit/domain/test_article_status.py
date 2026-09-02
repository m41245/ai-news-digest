"""
Unit tests for ArticleStatus enum.
"""

from __future__ import annotations

from ai_news_digest.domain.enums.article_status import ArticleStatus


def test_article_status_values() -> None:
    """Test that all ArticleStatus enum values are accessible."""
    assert ArticleStatus.NEW.value == "new"
    assert ArticleStatus.CATEGORIZED.value == "categorized"
    assert ArticleStatus.SUMMARIZED.value == "summarized"
    assert ArticleStatus.READY.value == "ready"
    assert ArticleStatus.FAILED.value == "failed"


def test_article_status_is_string_enum():
    """Test that ArticleStatus is a StrEnum."""
    assert isinstance(ArticleStatus.NEW, str)
