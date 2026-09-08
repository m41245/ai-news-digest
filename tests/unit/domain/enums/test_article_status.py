"""
Unit tests for ArticleStatus enum.
"""

from __future__ import annotations

from ai_news_digest.domain.enums.article_status import ArticleStatus


def test_article_status_values() -> None:
    """Test ArticleStatus enum values."""
    assert ArticleStatus.NEW == "new"
    assert ArticleStatus.ANALYZED == "analyzed"
    assert ArticleStatus.CATEGORIZED == "categorized"
    assert ArticleStatus.SUMMARIZED == "summarized"
    assert ArticleStatus.READY == "ready"
    assert ArticleStatus.FAILED == "failed"


def test_article_status_is_string_enum() -> None:
    """Test ArticleStatus is a StrEnum."""
    assert isinstance(ArticleStatus.NEW, str)


def test_article_status_comparison() -> None:
    """Test ArticleStatus comparison."""
    assert ArticleStatus.NEW == "new"
    assert ArticleStatus.NEW != "fetched"


def test_article_status_iteration() -> None:
    """Test iterating over ArticleStatus values."""
    statuses = list(ArticleStatus)

    assert len(statuses) == 6
    assert ArticleStatus.NEW in statuses
    assert ArticleStatus.ANALYZED in statuses
    assert ArticleStatus.CATEGORIZED in statuses
    assert ArticleStatus.SUMMARIZED in statuses
    assert ArticleStatus.READY in statuses
    assert ArticleStatus.FAILED in statuses
