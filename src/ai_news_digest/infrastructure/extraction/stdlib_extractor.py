from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, cast

import trafilatura

from ai_news_digest.core.logging import get_logger


@dataclass(slots=True)
class StdlibHtmlExtractor:
    """Extract main article text from HTML using trafilatura."""

    _logger: Any = field(default_factory=lambda: get_logger(__name__))

    async def extract(self, html: str, url: str | None = None) -> str:
        """Extract main article text from HTML.

        Uses trafilatura for robust boilerplate removal. Falls back to
        empty string on completely malformed input.
        """
        if not html:
            return ""

        try:
            extracted = await asyncio.to_thread(
                trafilatura.extract,
                html,
                include_comments=False,
                include_tables=True,
                url=url,
            )
            extracted = cast("str | None", extracted)
        except Exception as exc:
            self._logger.warning(
                "HTML extraction failed",
                url=url,
                error=str(exc),
            )
            return ""

        if extracted is None:
            self._logger.debug(
                "HTML extraction returned no content",
                url=url,
            )
            return ""

        self._logger.debug(
            "HTML extraction succeeded",
            url=url,
            extracted_length=len(extracted),
        )
        return extracted
