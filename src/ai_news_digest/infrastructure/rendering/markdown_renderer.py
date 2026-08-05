from __future__ import annotations

from ai_news_digest.application.rendering.renderer import DigestRenderer, RenderedDigest
from ai_news_digest.domain.enums.digest_format import DigestFormat
from ai_news_digest.domain.models.digest import Digest


class MarkdownRenderer(DigestRenderer):
    """Render a Digest as Markdown."""

    @property
    def format(self) -> DigestFormat:
        return DigestFormat.MARKDOWN

    def render(self, digest: Digest) -> RenderedDigest:
        lines = [
            f"# {digest.title}",
            "",
            f"Generated: {digest.generated_at.isoformat()}",
            "",
        ]

        if digest.content.strip():
            lines.append(digest.content.strip())
        else:
            lines.append("_No digest content available._")

        return RenderedDigest(
            digest_id=digest.id,
            format=self.format,
            content="\n".join(lines),
        )
