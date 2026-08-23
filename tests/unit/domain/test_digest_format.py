"""
Unit tests for DigestFormat enum.
"""

from __future__ import annotations

from ai_news_digest.domain.enums.digest_format import DigestFormat


def test_digest_format_values() -> None:
    """Test that all DigestFormat enum values are accessible."""
    assert DigestFormat.HTML.value == "html"
    assert DigestFormat.MARKDOWN.value == "markdown"
    assert DigestFormat.PDF.value == "pdf"


def test_digest_format_is_string_enum():
    """Test that DigestFormat is a StrEnum."""
    assert isinstance(DigestFormat.HTML, str)
    assert isinstance(DigestFormat.MARKDOWN, str)
    assert isinstance(DigestFormat.PDF, str)
