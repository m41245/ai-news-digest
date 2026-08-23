"""
Unit tests for Source domain model.
"""

from __future__ import annotations

from uuid import UUID

from ai_news_digest.domain.models.source import Source


def test_source_creation():
    """Test that a Source can be created with valid parameters."""
    source = Source.create(
        name="Test Source",
        feed_url="https://example.com/feed.xml",
        website_url="https://example.com",
        description="Test description",
        is_active=True,
    )

    assert isinstance(source.id, UUID)
    assert source.name == "Test Source"
    assert source.feed_url == "https://example.com/feed.xml"
    assert source.website_url == "https://example.com"
    assert source.description == "Test description"
    assert source.is_active is True
    assert source.created_at is not None


def test_source_creation_minimal():
    """Test that a Source can be created with minimal parameters."""
    source = Source.create(
        name="Test Source",
        feed_url="https://example.com/feed.xml",
    )

    assert source.name == "Test Source"
    assert source.feed_url == "https://example.com/feed.xml"
    assert source.website_url is None
    assert source.description is None
    assert source.is_active is True


def test_source_creation_inactive():
    """Test that a Source can be created as inactive."""
    source = Source.create(
        name="Test Source",
        feed_url="https://example.com/feed.xml",
        is_active=False,
    )

    assert source.is_active is False


def test_source_update_name():
    """Test updating a source's name."""
    source = Source.create(
        name="Test Source",
        feed_url="https://example.com/feed.xml",
    )

    source.update(name="Updated Name")

    assert source.name == "Updated Name"
    assert source.feed_url == "https://example.com/feed.xml"


def test_source_update_multiple_fields():
    """Test updating multiple source fields."""
    source = Source.create(
        name="Test Source",
        feed_url="https://example.com/feed.xml",
    )

    source.update(
        name="Updated Name",
        feed_url="https://updated.com/feed.xml",
        description="Updated description",
        is_active=False,
    )

    assert source.name == "Updated Name"
    assert source.feed_url == "https://updated.com/feed.xml"
    assert source.description == "Updated description"
    assert source.is_active is False


def test_source_update_partial():
    """Test that partial updates don't affect other fields."""
    source = Source.create(
        name="Test Source",
        feed_url="https://example.com/feed.xml",
        website_url="https://example.com",
        description="Test description",
    )

    source.update(name="Updated Name")

    assert source.name == "Updated Name"
    assert source.feed_url == "https://example.com/feed.xml"
    assert source.website_url == "https://example.com"
    assert source.description == "Test description"


def test_source_activate():
    """Test activating a source."""
    source = Source.create(
        name="Test Source",
        feed_url="https://example.com/feed.xml",
        is_active=False,
    )

    source.activate()

    assert source.is_active is True


def test_source_deactivate():
    """Test deactivating a source."""
    source = Source.create(
        name="Test Source",
        feed_url="https://example.com/feed.xml",
        is_active=True,
    )

    source.deactivate()

    assert source.is_active is False
