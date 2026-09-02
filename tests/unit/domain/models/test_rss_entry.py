"""
Unit tests for RssEntry domain model.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from ai_news_digest.domain.models.rss_entry import RssEntry


def test_rss_entry_with_all_fields() -> None:
    """Test RssEntry with all fields."""
    published_at = datetime.now(UTC)

    entry = RssEntry(
        title="Test Article",
        url="https://example.com/article",
        summary="Test summary",
        content="Test content",
        published_at=published_at,
    )

    assert entry.title == "Test Article"
    assert entry.url == "https://example.com/article"
    assert entry.summary == "Test summary"
    assert entry.content == "Test content"
    assert entry.published_at == published_at


def test_rss_entry_without_content() -> None:
    """Test RssEntry without content."""
    published_at = datetime.now(UTC)

    entry = RssEntry(
        title="Test Article",
        url="https://example.com/article",
        summary="Test summary",
        content=None,
        published_at=published_at,
    )

    assert entry.content is None


def test_rss_entry_slots() -> None:
    """Test RssEntry uses slots."""
    entry = RssEntry(
        title="Test Article",
        url="https://example.com/article",
        summary="Test summary",
        content=None,
        published_at=datetime.now(UTC),
    )

    # Should not be able to add arbitrary attributes due to slots
    with pytest.raises(AttributeError):
        entry.new_attr = "value"
