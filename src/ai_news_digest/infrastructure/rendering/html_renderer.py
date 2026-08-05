from __future__ import annotations

from html import escape

from ai_news_digest.application.rendering.renderer import DigestRenderer, RenderedDigest
from ai_news_digest.domain.enums.digest_format import DigestFormat
from ai_news_digest.domain.models.digest import Digest


class HTMLRenderer(DigestRenderer):
    """Render a Digest as HTML."""

    @property
    def format(self) -> DigestFormat:
        return DigestFormat.HTML

    def render(self, digest: Digest) -> RenderedDigest:
        safe_title = escape(digest.title)
        safe_content = escape(digest.content).replace("\n", "<br>\n")

        html = (
            "<html>\n"
            "  <head><meta charset='utf-8'><title>"
            f"{safe_title}</title></head>\n"
            "  <body>\n"
            f"    <h1>{safe_title}</h1>\n"
            f"    <p><strong>Generated:</strong> {digest.generated_at.isoformat()}</p>\n"
            f"    <div>{safe_content}</div>\n"
            "  </body>\n"
            "</html>\n"
        )

        return RenderedDigest(
            digest_id=digest.id,
            format=self.format,
            content=html,
        )
