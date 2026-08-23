from __future__ import annotations

from datetime import UTC

from reportlab.lib.pagesizes import letter  # type: ignore[import-untyped]
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # type: ignore[import-untyped]
from reportlab.lib.units import inch  # type: ignore[import-untyped]
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer  # type: ignore[import-untyped]

from ai_news_digest.application.rendering.renderer import DigestRenderer, RenderedDigest
from ai_news_digest.domain.enums.digest_format import DigestFormat
from ai_news_digest.domain.models.digest import Digest


class PDFRenderer(DigestRenderer):
    """PDF renderer for digests using ReportLab."""

    @property
    def format(self) -> DigestFormat:
        return DigestFormat.PDF

    def render(self, digest: Digest) -> RenderedDigest:
        """Render a digest to PDF format."""
        from io import BytesIO

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        title_style = ParagraphStyle(
            "DigestTitle",
            parent=styles["Heading1"],
            fontSize=24,
            spaceAfter=20,
            textColor="#2c3e50",
        )

        meta_style = ParagraphStyle(
            "DigestMeta",
            parent=styles["Normal"],
            fontSize=10,
            textColor="#7f8c8d",
            spaceAfter=20,
        )

        story.append(Paragraph(self._escape(digest.title), title_style))
        story.append(
            Paragraph(
                f"Generated: {digest.generated_at.astimezone(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
                meta_style,
            )
        )
        story.append(Spacer(1, 0.2 * inch))

        body_style = ParagraphStyle(
            "DigestBody",
            parent=styles["Normal"],
            fontSize=11,
            leading=16,
            spaceAfter=10,
        )

        heading2_style = ParagraphStyle(
            "DigestH2",
            parent=styles["Heading2"],
            fontSize=16,
            spaceAfter=10,
            spaceBefore=16,
            textColor="#2c3e50",
        )

        heading3_style = ParagraphStyle(
            "DigestH3",
            parent=styles["Heading3"],
            fontSize=13,
            spaceAfter=6,
            spaceBefore=12,
            textColor="#34495e",
        )

        if digest.content.strip():
            for line in digest.content.split("\n"):
                stripped = line.strip()
                if not stripped:
                    continue

                if stripped.startswith("# ") and len(stripped) > 2:
                    story.append(Paragraph(self._escape(stripped[2:]), title_style))
                elif stripped.startswith("## ") and len(stripped) > 3:
                    story.append(Paragraph(self._escape(stripped[3:]), heading2_style))
                elif stripped.startswith("### ") and len(stripped) > 4:
                    story.append(Paragraph(self._escape(stripped[4:]), heading3_style))
                elif stripped == "---":
                    story.append(Spacer(1, 0.1 * inch))
                else:
                    story.append(Paragraph(self._escape(stripped), body_style))
        else:
            story.append(Paragraph("*No digest content available.*", body_style))

        doc.build(story)
        pdf_content = buffer.getvalue()
        buffer.close()

        return RenderedDigest(
            format=DigestFormat.PDF,
            content=pdf_content,
        )

    def _escape(self, text: str) -> str:
        """Escape text for safe PDF rendering."""
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
