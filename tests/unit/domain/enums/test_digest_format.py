"""
Unit tests for DigestFormat enum.
"""

from __future__ import annotations

from ai_news_digest.domain.enums.digest_format import DigestFormat


def test_digest_format_values() -> None:
    """Test DigestFormat enum values."""
    assert DigestFormat.HTML == "html"
    assert DigestFormat.MARKDOWN == "markdown"
    assert DigestFormat.PDF == "pdf"


def test_digest_format_is_string_enum() -> None:
    """Test DigestFormat is a StrEnum."""
    assert isinstance(DigestFormat.HTML, str)


def test_digest_format_comparison() -> None:
    """Test DigestFormat comparison."""
    assert DigestFormat.HTML == "html"
    assert DigestFormat.HTML != "markdown"


def test_digest_format_iteration() -> None:
    """Test iterating over DigestFormat values."""
    formats = list(DigestFormat)

    assert len(formats) == 3
    assert DigestFormat.HTML in formats
    assert DigestFormat.MARKDOWN in formats
    assert DigestFormat.PDF in formats
