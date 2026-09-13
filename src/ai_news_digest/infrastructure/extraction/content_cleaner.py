from __future__ import annotations

import re
from dataclasses import dataclass, field
from html import unescape
from typing import Any

from ai_news_digest.core.logging import get_logger

_WHITESPACE_RE = re.compile(r"[ \t]+")
_MULTIPLE_BLANKS_RE = re.compile(r"\n{3,}")


@dataclass(slots=True)
class ContentCleaner:
    """Normalize extracted article text."""

    _logger: Any = field(default_factory=lambda: get_logger(__name__))

    def clean(self, content: str | None) -> str:
        """Normalize extracted article text.

        - Decode HTML entities
        - Normalize whitespace (collapse multiple spaces/tabs)
        - Normalize line endings to \\n
        - Remove repeated blank lines (max 1 consecutive blank line)
        - Remove extremely short paragraphs (likely navigation fragments)
        - Strip leading/trailing whitespace
        """
        if content is None:
            return ""

        original_length = len(content)
        cleaned = content.strip()

        if not cleaned:
            return ""

        cleaned = unescape(cleaned)

        cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")

        cleaned = _WHITESPACE_RE.sub(" ", cleaned)

        cleaned = _MULTIPLE_BLANKS_RE.sub("\n\n", cleaned)

        paragraphs: list[str] = []
        for paragraph in cleaned.split("\n"):
            paragraph = paragraph.strip()
            paragraphs.append(paragraph)

        meaningful = [
            p
            for p in paragraphs
            if p and not (len(p) < 20 and len(p.split()) < 3)
        ]

        cleaned = "\n".join(meaningful) if meaningful else "\n".join(paragraphs)

        cleaned = cleaned.strip()

        self._logger.debug(
            "Content cleaning complete",
            original_length=original_length,
            cleaned_length=len(cleaned),
        )

        return cleaned
