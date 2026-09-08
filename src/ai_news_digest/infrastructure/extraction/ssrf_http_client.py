from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SsrfHttpArticleFetcher:
    """
    Minimal stub implementation for M45 final closure testing.
    """

    max_response_bytes: int = 5_000_000

    async def fetch(self, url: str) -> str:
        return ""
