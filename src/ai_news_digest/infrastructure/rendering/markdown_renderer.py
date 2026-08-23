from __future__ import annotations

from datetime import UTC

from ai_news_digest.application.rendering.renderer import DigestRenderer, RenderedDigest
from ai_news_digest.domain.enums.digest_format import DigestFormat
from ai_news_digest.domain.models.digest import Digest


class MarkdownRenderer(DigestRenderer):
    """Render a Digest as Markdown."""

    @property
    def format(self) -> DigestFormat:
        return DigestFormat.MARKDOWN

    def render(self, digest: Digest) -> RenderedDigest:
        title = digest.title.strip() if digest.title else "AI News Digest"
        generated_at = digest.generated_at.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC")

        lines = [
            f"# {title}",
            "",
            f"**Generated:** {generated_at}",
            "",
            "---",
            "",
        ]

        if digest.content.strip():
            lines.append(digest.content.strip())
        else:
            lines.append("*No digest content available.*")

        return RenderedDigest(
            format=self.format,
            content="\n".join(lines),
        )
