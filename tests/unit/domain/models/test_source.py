"""
Unit tests for Source domain model.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from ai_news_digest.domain.enums.source_status import SourceStatus
from ai_news_digest.domain.enums.source_type import SourceType
from ai_news_digest.domain.models.source import Source


def _make_source(feed_url: str) -> Source:
    """Build a Source bypassing create-time validation (for invalid URLs)."""
    return Source(
        id=uuid4(),
        name="Test Source",
        feed_url=feed_url,
        website_url=None,
        description=None,
        is_active=True,
        source_type=SourceType.OTHER,
        status=SourceStatus.PENDING_REVIEW,
        created_at=datetime.now(UTC),
    )


def test_source_create_with_all_fields() -> None:
    """Test Source.create with all fields."""
    source = Source.create(
        name="Test Source",
        feed_url="https://example.com/feed.xml",
        website_url="https://example.com",
        description="Test description",
        is_active=True,
    )

    assert source.id is not None
    assert source.name == "Test Source"
    assert source.feed_url == "https://example.com/feed.xml"
    assert source.website_url == "https://example.com"
    assert source.description == "Test description"
    assert source.is_active is True
    assert source.created_at is not None


def test_source_create_with_required_fields_only() -> None:
    """Test Source.create with only required fields."""
    source = Source.create(
        name="Test Source",
        feed_url="https://example.com/feed.xml",
    )

    assert source.name == "Test Source"
    assert source.feed_url == "https://example.com/feed.xml"
    assert source.website_url is None
    assert source.description is None
    assert source.is_active is True  # Default value


def test_source_create_inactive() -> None:
    """Test Source.create with is_active=False."""
    source = Source.create(
        name="Test Source",
        feed_url="https://example.com/feed.xml",
        is_active=False,
    )

    assert source.is_active is False


def test_source_create_generates_id() -> None:
    """Test Source.create generates unique IDs."""
    source1 = Source.create(
        name="Source 1",
        feed_url="https://example.com/feed1.xml",
    )

    source2 = Source.create(
        name="Source 2",
        feed_url="https://example.com/feed2.xml",
    )

    assert source1.id != source2.id


def test_source_create_sets_created_at() -> None:
    """Test Source.create sets created_at to current time."""
    before = datetime.now(UTC)
    source = Source.create(
        name="Test Source",
        feed_url="https://example.com/feed.xml",
    )
    after = datetime.now(UTC)

    assert before <= source.created_at <= after


def test_source_update_name() -> None:
    """Test Source.update with name."""
    source = Source.create(
        name="Original Name",
        feed_url="https://example.com/feed.xml",
    )

    source.update(name="Updated Name")

    assert source.name == "Updated Name"


def test_source_update_feed_url() -> None:
    """Test Source.update with feed_url."""
    source = Source.create(
        name="Test Source",
        feed_url="https://example.com/feed.xml",
    )

    source.update(feed_url="https://updated.com/feed.xml")

    assert source.feed_url == "https://updated.com/feed.xml"


def test_source_update_website_url() -> None:
    """Test Source.update with website_url."""
    source = Source.create(
        name="Test Source",
        feed_url="https://example.com/feed.xml",
    )

    source.update(website_url="https://updated.com")

    assert source.website_url == "https://updated.com"


def test_source_update_description() -> None:
    """Test Source.update with description."""
    source = Source.create(
        name="Test Source",
        feed_url="https://example.com/feed.xml",
    )

    source.update(description="Updated description")

    assert source.description == "Updated description"


def test_source_update_is_active() -> None:
    """Test Source.update with is_active."""
    source = Source.create(
        name="Test Source",
        feed_url="https://example.com/feed.xml",
        is_active=True,
    )

    source.update(is_active=False)

    assert source.is_active is False


def test_source_update_partial() -> None:
    """Test Source.update with partial fields."""
    source = Source.create(
        name="Original Name",
        feed_url="https://example.com/feed.xml",
        website_url="https://example.com",
        description="Original description",
    )

    source.update(name="Updated Name", description="Updated description")

    assert source.name == "Updated Name"
    assert source.feed_url == "https://example.com/feed.xml"  # Unchanged
    assert source.website_url == "https://example.com"  # Unchanged
    assert source.description == "Updated description"


def test_source_update_none_values() -> None:
    """Test Source.update with None values doesn't change fields."""
    source = Source.create(
        name="Test Source",
        feed_url="https://example.com/feed.xml",
        website_url="https://example.com",
    )

    source.update(name=None, feed_url=None)

    assert source.name == "Test Source"  # Unchanged
    assert source.feed_url == "https://example.com/feed.xml"  # Unchanged


def test_source_activate() -> None:
    """Test Source.activate method."""
    source = Source.create(
        name="Test Source",
        feed_url="https://example.com/feed.xml",
        is_active=False,
    )

    source.activate()

    assert source.is_active is True


def test_source_deactivate() -> None:
    """Test Source.deactivate method."""
    source = Source.create(
        name="Test Source",
        feed_url="https://example.com/feed.xml",
        is_active=True,
    )

    source.deactivate()

    assert source.is_active is False


def test_source_validate_valid_feed_url() -> None:
    """Test Source.validate with valid feed URL."""
    source = Source.create(
        name="Test Source",
        feed_url="https://example.com/feed.xml",
    )

    Source.validate(source)


def test_source_validate_feed_url_http() -> None:
    """Test Source.validate with http feed URL."""
    source = Source.create(
        name="Test Source",
        feed_url="http://example.com/feed.xml",
    )

    Source.validate(source)


def test_source_validate_feed_url_missing_scheme() -> None:
    """Test Source.validate raises on missing scheme."""
    source = _make_source(feed_url="example.com/feed.xml")

    with pytest.raises(ValueError, match="scheme"):
        Source.validate(source)


def test_source_validate_feed_url_invalid_scheme() -> None:
    """Test Source.validate raises on invalid scheme."""
    source = _make_source(feed_url="ftp://example.com/feed.xml")

    with pytest.raises(ValueError, match="http or https"):
        Source.validate(source)


def test_source_validate_feed_url_missing_host() -> None:
    """Test Source.validate raises on missing host."""
    source = _make_source(feed_url="https://")

    with pytest.raises(ValueError, match="host"):
        Source.validate(source)


def test_source_validate_feed_url_static_method() -> None:
    """Test Source.validate_feed_url static method."""
    Source.validate_feed_url("https://example.com/feed.xml")

    with pytest.raises(ValueError):
        Source.validate_feed_url("not-a-url")
