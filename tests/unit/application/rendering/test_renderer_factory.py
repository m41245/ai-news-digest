"""
Unit tests for DigestRendererFactory.
"""

from __future__ import annotations

import pytest

from ai_news_digest.application.rendering.renderer_factory import DigestRendererFactory
from ai_news_digest.core.exceptions import ValidationError
from ai_news_digest.domain.enums.digest_format import DigestFormat
from ai_news_digest.infrastructure.rendering.html_renderer import HTMLRenderer
from ai_news_digest.infrastructure.rendering.markdown_renderer import MarkdownRenderer
from ai_news_digest.infrastructure.rendering.pdf_renderer import PDFRenderer


@pytest.fixture
def factory() -> DigestRendererFactory:
    """Create a DigestRendererFactory instance."""
    return DigestRendererFactory()


def test_factory_get_renderer_markdown(factory: DigestRendererFactory) -> None:
    """Test getting markdown renderer."""
    renderer = factory.get_renderer(DigestFormat.MARKDOWN)

    assert isinstance(renderer, MarkdownRenderer)
    assert renderer.format == DigestFormat.MARKDOWN


def test_factory_get_renderer_html(factory: DigestRendererFactory) -> None:
    """Test getting HTML renderer."""
    renderer = factory.get_renderer(DigestFormat.HTML)

    assert isinstance(renderer, HTMLRenderer)
    assert renderer.format == DigestFormat.HTML


def test_factory_get_renderer_pdf(factory: DigestRendererFactory) -> None:
    """Test getting PDF renderer."""
    renderer = factory.get_renderer(DigestFormat.PDF)

    assert isinstance(renderer, PDFRenderer)
    assert renderer.format == DigestFormat.PDF


def test_factory_get_renderer_invalid_format(factory: DigestRendererFactory) -> None:
    """Test getting renderer for invalid format raises ValidationError."""
    factory._renderers = {}  # Clear all renderers

    with pytest.raises(ValidationError, match="No renderer available for digest format"):
        factory.get_renderer(DigestFormat.MARKDOWN)
