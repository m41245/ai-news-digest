from __future__ import annotations

from dataclasses import dataclass


@dataclass
class StdlibHtmlExtractor:
    """
    Minimal stub implementation for M45 final closure testing.
    """

    def extract(self, html: str) -> str:
        return html
