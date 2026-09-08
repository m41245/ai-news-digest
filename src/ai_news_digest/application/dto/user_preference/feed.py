from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class PersonalizedFeedItemResponse(BaseModel):
    """A single item in the personalized feed."""

    id: str
    title: str
    source_name: str | None = None
    source_type: str | None = None
    published_at: str | None = None
    latest_update_at: str | None = None
    importance_score: float | None = None
    confidence: float | None = None
    companies: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    cluster_id: str | None = None
    cluster_slug: str | None = None
    article_count: int = 0
    source_count: int = 0
    relevance_reasons: list[str] = Field(default_factory=list)
    relevance_score: float = 0.0
    is_fallback: bool = False
    correction_signals: bool = False
    contradiction_signals: bool = False


class PersonalizedFeedResponse(BaseModel):
    """Paginated response for the personalized feed."""

    items: list[PersonalizedFeedItemResponse] = Field(default_factory=list)
    total: int = 0
    limit: int = 20
    offset: int = 0
    empty_reason: str | None = None


FeedSort = Literal["published_at", "importance", "relevance"]


__all__ = [
    "FeedSort",
    "PersonalizedFeedItemResponse",
    "PersonalizedFeedResponse",
]
