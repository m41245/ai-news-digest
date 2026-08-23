from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class RssEntry:
    """
    Normalized RSS entry returned by an RSS fetcher.
    """

    title: str
    url: str
    summary: str
    content: str | None
    published_at: datetime
    author: str | None = None
    guid: str | None = None
