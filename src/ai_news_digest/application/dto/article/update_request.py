from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class UpdateArticleRequest:
    """
    Request DTO for updating an article.
    """

    id: str
    title: str | None = None
    summary: str | None = None
    content: str | None = None
    category_id: str | None = None
