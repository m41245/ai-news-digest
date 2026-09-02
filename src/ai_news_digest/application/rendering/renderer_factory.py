from __future__ import annotations

from ai_news_digest.application.rendering.renderer import DigestRenderer
from ai_news_digest.core.exceptions import ValidationError
from ai_news_digest.domain.enums.digest_format import DigestFormat
from ai_news_digest.infrastructure.rendering.html_renderer import HTMLRenderer
from ai_news_digest.infrastructure.rendering.markdown_renderer import MarkdownRenderer
from ai_news_digest.infrastructure.rendering.pdf_renderer import PDFRenderer


class DigestRendererFactory:
    """Factory for creating digest renderers by format."""

    def __init__(self) -> None:
        self._renderers: dict[DigestFormat, DigestRenderer] = {
            DigestFormat.MARKDOWN: MarkdownRenderer(),
            DigestFormat.HTML: HTMLRenderer(),
            DigestFormat.PDF: PDFRenderer(),
        }

    def get_renderer(self, digest_format: DigestFormat) -> DigestRenderer:
        """Get a renderer for the specified digest format."""
        renderer = self._renderers.get(digest_format)

        if renderer is None:
            raise ValidationError(f"No renderer available for digest format: {digest_format}")

        return renderer
