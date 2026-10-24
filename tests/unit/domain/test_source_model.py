"""
Unit tests for Source domain model.
"""

from __future__ import annotations

from uuid import UUID

from ai_news_digest.domain.enums.source_status import SourceStatus
from ai_news_digest.domain.enums.source_type import SourceType
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


def test_source_trust_metadata_defaults():
    """Newly created sources default trust/health metadata to safe values."""
    source = Source.create(
        name="Test Source",
        feed_url="https://example.com/feed.xml",
    )

    assert source.publisher is None
    assert source.verification_notes is None
    assert source.priority == 0
    assert source.last_successful_fetch_at is None
    assert source.last_failed_fetch_at is None
    assert source.failure_count == 0


def test_source_create_with_trust_metadata():
    """Source.create accepts publisher, verification notes, and priority."""
    source = Source.create(
        name="Test Source",
        feed_url="https://example.com/feed.xml",
        publisher="Example Publisher",
        verification_notes="Curated trusted source.",
        source_type=SourceType.OFFICIAL_COMPANY,
        priority=5,
    )

    assert source.publisher == "Example Publisher"
    assert source.verification_notes == "Curated trusted source."
    assert source.source_type == SourceType.OFFICIAL_COMPANY
    assert source.priority == 5


def test_source_update_trust_metadata():
    """Partial updates can modify trust/health metadata without touching other fields."""
    source = Source.create(
        name="Test Source",
        feed_url="https://example.com/feed.xml",
        publisher="Original Publisher",
    )

    source.update(verification_notes="Updated notes.", priority=10)

    assert source.publisher == "Original Publisher"
    assert source.verification_notes == "Updated notes."
    assert source.priority == 10


def test_source_is_eligible_when_active_and_verified():
    """Only active, verified sources are eligible."""
    source = Source.create(
        name="Verified Source",
        feed_url="https://example.com/feed.xml",
        is_active=True,
        status=SourceStatus.VERIFIED,
    )

    assert source.is_eligible() is True


def test_source_is_not_eligible_when_pending_review():
    """Pending-review sources are not eligible."""
    source = Source.create(
        name="Pending Source",
        feed_url="https://example.com/feed.xml",
        is_active=True,
        status=SourceStatus.PENDING_REVIEW,
    )

    assert source.is_eligible() is False


def test_source_is_not_eligible_when_rejected():
    """Rejected sources are not eligible."""
    source = Source.create(
        name="Rejected Source",
        feed_url="https://example.com/feed.xml",
        is_active=True,
        status=SourceStatus.REJECTED,
    )

    assert source.is_eligible() is False


def test_source_is_not_eligible_when_inactive():
    """Inactive sources are not eligible even when verified."""
    source = Source.create(
        name="Inactive Source",
        feed_url="https://example.com/feed.xml",
        is_active=False,
        status=SourceStatus.VERIFIED,
    )

    assert source.is_eligible() is False


def test_source_record_successful_fetch():
    """A successful fetch timestamps success and resets failure count."""
    source = Source.create(
        name="Test Source",
        feed_url="https://example.com/feed.xml",
        failure_count=3,
    )

    source.record_successful_fetch()

    assert source.last_successful_fetch_at is not None
    assert source.failure_count == 0


def test_source_record_failed_fetch_increments_count_without_revoking_trust():
    """A failed fetch timestamps failure and increments count but keeps status."""
    source = Source.create(
        name="Test Source",
        feed_url="https://example.com/feed.xml",
        status=SourceStatus.VERIFIED,
        failure_count=1,
    )

    source.record_failed_fetch()

    assert source.last_failed_fetch_at is not None
    assert source.failure_count == 2
    # Trust state is not automatically revoked by a temporary failure.
    assert source.status == SourceStatus.VERIFIED
    assert source.is_eligible() is True
