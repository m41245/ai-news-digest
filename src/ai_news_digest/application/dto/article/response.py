from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class ArticleResponse:
    """
    Response DTO representing an article.
    """

    id: str
    title: str
    url: str
    summary: str
    content: str | None
    source_id: str
    category_id: str | None
    published_at: str
    fetched_at: str
    status: str
