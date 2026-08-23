from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class DigestArticleView:
    """
    Immutable article metadata prepared for digest rendering.
    """

    article_id: UUID
    title: str
    url: str
    summary: str
    source_name: str
    category_name: str | None
    published_at: datetime
