from __future__ import annotations

from ai_news_digest.application.rendering.renderer import DigestRenderer
from ai_news_digest.domain.enums.digest_format import DigestFormat
from ai_news_digest.infrastructure.rendering.html_renderer import HTMLRenderer
from ai_news_digest.infrastructure.rendering.markdown_renderer import MarkdownRenderer
from ai_news_digest.infrastructure.rendering.pdf_renderer import PDFRenderer


class DigestRendererFactory:
    """Select a renderer by DigestFormat."""

    def __init__(self) -> None:
        self._renderers: dict[DigestFormat, DigestRenderer] = {
            DigestFormat.MARKDOWN: MarkdownRenderer(),
            DigestFormat.HTML: HTMLRenderer(),
            DigestFormat.PDF: PDFRenderer(),
        }

    def get_renderer(self, digest_format: DigestFormat) -> DigestRenderer:
        try:
            return self._renderers[digest_format]
        except KeyError as exc:
            raise ValueError(
                f"No renderer registered for digest format: {digest_format}"
            ) from exc
