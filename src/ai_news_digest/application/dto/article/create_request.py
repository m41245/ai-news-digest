from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class CreateArticleRequest:
    """
    Request DTO for creating a news article.
    """

    title: str
    url: str
    summary: str
    content: str | None
    source_id: str
    published_at: str
    category_id: str | None = None
