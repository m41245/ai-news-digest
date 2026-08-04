from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True, frozen=True)
class ParsedArticle:
    """
    Immutable representation of an article extracted from an RSS or Atom feed.
    """

    title: str
    url: str
    summary: str
    published_at: datetime
