"""
Unit tests for Digest domain model.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from ai_news_digest.domain.enums.digest_format import DigestFormat
from ai_news_digest.domain.models.digest import Digest


def test_digest_creation():
    """Test that a Digest can be created with valid parameters."""
    article_ids = [uuid4(), uuid4(), uuid4()]

    digest = Digest.create(
        title="Test Digest",
        content="Test digest content",
        digest_format=DigestFormat.MARKDOWN,
        article_ids=article_ids,
    )

    assert isinstance(digest.id, UUID)
    assert digest.title == "Test Digest"
    assert digest.content == "Test digest content"
    assert digest.format == DigestFormat.MARKDOWN
    assert digest.article_ids == article_ids
    assert digest.generated_at is not None


def test_digest_creation_without_articles():
    """Test that a Digest can be created without article IDs."""
    digest = Digest.create(
        title="Test Digest",
        content="Test digest content",
        digest_format=DigestFormat.HTML,
    )

    assert digest.article_ids == []


def test_digest_creation_with_none_articles():
    """Test that passing None for article_ids results in empty list."""
    digest = Digest.create(
        title="Test Digest",
        content="Test digest content",
        digest_format=DigestFormat.PDF,
        article_ids=None,
    )

    assert digest.article_ids == []


def test_digest_different_formats():
    """Test creating digests with different formats."""
    for digest_format in [DigestFormat.HTML, DigestFormat.MARKDOWN, DigestFormat.PDF]:
        digest = Digest.create(
            title="Test Digest",
            content="Test content",
            digest_format=digest_format,
        )
        assert digest.format == digest_format
