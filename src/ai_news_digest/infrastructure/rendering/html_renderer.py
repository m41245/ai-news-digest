from __future__ import annotations

from datetime import UTC
from html import escape
from re import sub

from ai_news_digest.application.rendering.renderer import DigestRenderer, RenderedDigest
from ai_news_digest.domain.enums.digest_format import DigestFormat
from ai_news_digest.domain.models.digest import Digest


class HTMLRenderer(DigestRenderer):
    """Render a Digest as valid, escaped HTML5."""

    @property
    def format(self) -> DigestFormat:
        return DigestFormat.HTML

    def render(self, digest: Digest) -> RenderedDigest:
        safe_title = escape(digest.title)
        generated_at = digest.generated_at.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC")
        body = self._markdown_to_html(digest.content)

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{safe_title}</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto,
      Oxygen, Ubuntu, Cantarell, sans-serif;
      line-height: 1.6;
      max-width: 800px;
      margin: 0 auto;
      padding: 20px;
      color: #333;
    }}
    h1 {{
      color: #2c3e50;
      border-bottom: 2px solid #3498db;
      padding-bottom: 10px;
    }}
    h2 {{
      color: #2c3e50;
      margin-top: 30px;
      border-bottom: 1px solid #ddd;
      padding-bottom: 5px;
    }}
    h3 {{
      color: #34495e;
      margin-top: 20px;
    }}
    .meta {{
      color: #7f8c8d;
      font-size: 0.9em;
      margin-bottom: 20px;
    }}
    a {{
      color: #3498db;
      text-decoration: none;
    }}
    a:hover {{
      text-decoration: underline;
    }}
    hr {{
      border: none;
      border-top: 1px solid #ddd;
      margin: 20px 0;
    }}
    @media print {{
      body {{
        max-width: 100%;
      }}
    }}
  </style>
</head>
<body>
  <h1>{safe_title}</h1>
  <div class="meta">Generated: {generated_at}</div>
  <hr>
  <div class="content">
{body}
  </div>
</body>
</html>"""

        return RenderedDigest(
            format=self.format,
            content=html,
        )

    def _markdown_to_html(self, markdown: str) -> str:
        """
        Convert our controlled Markdown subset to safe HTML.
        All user/article content is escaped before formatting.
        """
        if not markdown.strip():
            return ""

        lines = markdown.split("\n")
        html_lines: list[str] = []
        in_paragraph = False

        for line in lines:
            stripped = line.strip()

            if not stripped:
                if in_paragraph:
                    html_lines.append("</p>")
                    in_paragraph = False
                continue

            if stripped.startswith("# ") and len(stripped) > 2:
                if in_paragraph:
                    html_lines.append("</p>")
                    in_paragraph = False
                html_lines.append(f"<h1>{self._escape(stripped[2:])}</h1>")
            elif stripped.startswith("## ") and len(stripped) > 3:
                if in_paragraph:
                    html_lines.append("</p>")
                    in_paragraph = False
                html_lines.append(f"<h2>{self._escape(stripped[3:])}</h2>")
            elif stripped.startswith("### ") and len(stripped) > 4:
                if in_paragraph:
                    html_lines.append("</p>")
                    in_paragraph = False
                html_lines.append(f"<h3>{self._escape(stripped[4:])}</h3>")
            elif stripped == "---":
                if in_paragraph:
                    html_lines.append("</p>")
                    in_paragraph = False
                html_lines.append("<hr>")
            elif stripped.startswith("[") and "](" in stripped and stripped.endswith(")"):
                if in_paragraph:
                    html_lines.append("</p>")
                    in_paragraph = False
                html_lines.append(f"<p>{self._format_link(stripped)}</p>")
            elif stripped.startswith("**") and "**" in stripped[2:]:
                if in_paragraph:
                    html_lines.append("</p>")
                    in_paragraph = False
                html_lines.append(f"<p>{self._format_bold(stripped)}</p>")
            elif (
                stripped.startswith("*")
                and stripped.endswith("*")
                and not stripped.startswith("**")
            ):
                if in_paragraph:
                    html_lines.append("</p>")
                    in_paragraph = False
                html_lines.append(f"<p>{self._format_italic(stripped)}</p>")
            else:
                if not in_paragraph:
                    html_lines.append("<p>")
                    in_paragraph = True
                html_lines.append(self._escape(stripped))

        if in_paragraph:
            html_lines.append("</p>")

        return "\n".join(html_lines)

    def _escape(self, text: str) -> str:
        """Escape HTML special characters."""
        return escape(text)

    def _format_bold(self, text: str) -> str:
        """Format **bold** Markdown syntax to HTML."""
        escaped = self._escape(text)
        return sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)

    def _format_italic(self, text: str) -> str:
        """Format *italic* Markdown syntax to HTML."""
        escaped = self._escape(text)
        return sub(r"\*(.+?)\*", r"<em>\1</em>", escaped)

    def _format_link(self, text: str) -> str:
        """Format [text](url) Markdown syntax to safe HTML."""
        escaped = self._escape(text)
        return sub(
            r"\[(.+?)\]\((.+?)\)",
            lambda m: f'<a href="{self._escape(m.group(2))}">{self._escape(m.group(1))}</a>',
            escaped,
        )
