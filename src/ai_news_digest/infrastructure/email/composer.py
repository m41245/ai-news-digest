from __future__ import annotations

from dataclasses import dataclass

from ai_news_digest.domain.models.digest import Digest


@dataclass(slots=True, frozen=True)
class ComposedEmail:
    """
    Immutable email content produced by an EmailComposer.
    """

    subject: str
    html_body: str
    text_body: str


class EmailComposer:
    """
    Builds email content from a Digest without mutating the digest or
    performing any I/O.
    """

    def compose(self, digest: Digest) -> ComposedEmail:
        """
        Produce a ComposedEmail from the given digest.
        """
        subject = digest.title

        html_body = self._render_html(digest)
        text_body = self._build_plain_text(digest.title, digest.content)

        return ComposedEmail(
            subject=subject,
            html_body=html_body,
            text_body=text_body,
        )

    def _render_html(self, digest: Digest) -> str:
        """
        Render digest content to safe HTML.
        """
        from ai_news_digest.application.rendering.renderer_factory import (
            DigestRendererFactory,
        )
        from ai_news_digest.domain.enums.digest_format import DigestFormat

        renderer_factory = DigestRendererFactory()
        html_renderer = renderer_factory.get_renderer(DigestFormat.HTML)
        rendered = html_renderer.render(digest)
        html_content = rendered.content
        if isinstance(html_content, bytes):
            html_content = html_content.decode("utf-8")
        return html_content

    def _build_plain_text(self, title: str, content: str) -> str:
        """
        Build a plain-text fallback from digest content.
        """
        lines = [title, "", "=" * len(title), ""]
        for paragraph in content.split("\n\n"):
            lines.append(paragraph.strip())
            lines.append("")
        return "\n".join(lines)


__all__ = ["ComposedEmail", "EmailComposer"]
