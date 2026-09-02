"""
Unit tests for PDFRenderer.
"""

from __future__ import annotations

import pytest

from ai_news_digest.domain.enums.digest_format import DigestFormat
from ai_news_digest.domain.models.digest import Digest
from ai_news_digest.infrastructure.rendering.pdf_renderer import PDFRenderer


@pytest.fixture
def renderer() -> PDFRenderer:
    """Create a PDFRenderer instance."""
    return PDFRenderer()


@pytest.fixture
def sample_digest() -> Digest:
    """Create a sample Digest."""
    return Digest.create(
        title="Test Digest",
        content="Test content",
        digest_format=DigestFormat.PDF,
    )


def test_pdf_renderer_format(renderer: PDFRenderer) -> None:
    """Test renderer format property."""
    assert renderer.format == DigestFormat.PDF


def test_pdf_renderer_render_basic(renderer: PDFRenderer, sample_digest: Digest) -> None:
    """Test basic PDF rendering."""
    rendered = renderer.render(sample_digest)

    assert rendered.format == DigestFormat.PDF
    assert isinstance(rendered.content, bytes)
    assert rendered.content.startswith(b"%PDF")
    assert len(rendered.content) > 0


def test_pdf_renderer_render_multiline_content(renderer: PDFRenderer) -> None:
    """Test PDF rendering with multiline content."""
    digest = Digest.create(
        title="Multiline Digest",
        content="Line 1\nLine 2\nLine 3",
        digest_format=DigestFormat.PDF,
    )

    rendered = renderer.render(digest)

    assert rendered.format == DigestFormat.PDF
    assert len(rendered.content) > 0


def test_pdf_renderer_render_empty_content(renderer: PDFRenderer) -> None:
    """Test PDF rendering with empty content."""
    digest = Digest.create(
        title="Empty Digest",
        content="",
        digest_format=DigestFormat.PDF,
    )

    rendered = renderer.render(digest)

    assert rendered.format == DigestFormat.PDF
    # Should still produce PDF even with empty content
