"""
Unit tests for Digest domain model.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from ai_news_digest.domain.enums.digest_format import DigestFormat
from ai_news_digest.domain.models.digest import Digest


def test_digest_create_with_all_fields() -> None:
    """Test Digest.create with all fields."""
    article_ids = [uuid4(), uuid4(), uuid4()]

    digest = Digest.create(
        title="Test Digest",
        content="Test content",
        digest_format=DigestFormat.MARKDOWN,
        article_ids=article_ids,
    )

    assert digest.id is not None
    assert digest.title == "Test Digest"
    assert digest.content == "Test content"
    assert digest.format == DigestFormat.MARKDOWN
    assert digest.article_ids == article_ids
    assert digest.generated_at is not None


def test_digest_create_without_article_ids() -> None:
    """Test Digest.create without article_ids."""
    digest = Digest.create(
        title="Test Digest",
        content="Test content",
        digest_format=DigestFormat.MARKDOWN,
    )

    assert digest.article_ids == []


def test_digest_create_with_empty_article_ids() -> None:
    """Test Digest.create with empty article_ids list."""
    digest = Digest.create(
        title="Test Digest",
        content="Test content",
        digest_format=DigestFormat.MARKDOWN,
        article_ids=[],
    )

    assert digest.article_ids == []


def test_digest_create_html_format() -> None:
    """Test Digest.create with HTML format."""
    digest = Digest.create(
        title="Test Digest",
        content="Test content",
        digest_format=DigestFormat.HTML,
    )

    assert digest.format == DigestFormat.HTML


def test_digest_create_pdf_format() -> None:
    """Test Digest.create with PDF format."""
    digest = Digest.create(
        title="Test Digest",
        content="Test content",
        digest_format=DigestFormat.PDF,
    )

    assert digest.format == DigestFormat.PDF


def test_digest_create_generates_id() -> None:
    """Test Digest.create generates unique IDs."""
    digest1 = Digest.create(
        title="Digest 1",
        content="Content 1",
        digest_format=DigestFormat.MARKDOWN,
    )

    digest2 = Digest.create(
        title="Digest 2",
        content="Content 2",
        digest_format=DigestFormat.MARKDOWN,
    )

    assert digest1.id != digest2.id


def test_digest_create_sets_generated_at() -> None:
    """Test Digest.create sets generated_at to current time."""
    before = datetime.now(UTC)
    digest = Digest.create(
        title="Test Digest",
        content="Test content",
        digest_format=DigestFormat.MARKDOWN,
    )
    after = datetime.now(UTC)

    assert before <= digest.generated_at <= after


def test_digest_article_ids_default_factory() -> None:
    """Test that article_ids uses default_factory."""
    digest = Digest.create(
        title="Test Digest",
        content="Test content",
        digest_format=DigestFormat.MARKDOWN,
    )

    assert isinstance(digest.article_ids, list)
