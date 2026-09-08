from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ContentCleaner:
    """
    Minimal stub implementation for M45 final closure testing.
    """

    def clean(self, content: str) -> str:
        return content
