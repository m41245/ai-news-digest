"""
Unit tests for RssEntry value object.
"""

from __future__ import annotations

from datetime import UTC, datetime

from ai_news_digest.domain.models.rss_entry import RssEntry


def test_rss_entry_creation():
    """Test that an RssEntry can be created with valid parameters."""
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


def test_rss_entry_without_content():
    """Test that an RssEntry can be created without content."""
    published_at = datetime.now(UTC)

    entry = RssEntry(
        title="Test Article",
        url="https://example.com/article",
        summary="Test summary",
        content=None,
        published_at=published_at,
    )

    assert entry.content is None
