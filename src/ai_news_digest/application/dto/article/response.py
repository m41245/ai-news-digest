from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class ArticleResponse:
    """Response DTO representing an article."""

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
    importance_score: float | None = None
    confidence: float | None = None
    key_takeaways: tuple[str, ...] = ()
    why_it_matters: str | None = None
    companies: tuple[str, ...] = ()
    topics: tuple[str, ...] = ()
    categories: tuple[str, ...] = ()
    ai_provider: str | None = None
    ai_model: str | None = None
    ai_processed_at: str | None = None
