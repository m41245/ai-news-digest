from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class RecommendationItemResponse(BaseModel):
    """A single recommendation item."""

    item_type: Literal["story", "trend"] = "story"
    id: str
    title: str
    summary: str | None = None
    source_name: str | None = None
    source_type: str | None = None
    published_at: str | None = None
    latest_update_at: str | None = None
    importance_score: float | None = None
    confidence: float | None = None
    activity_status: str | None = None
    activity_score: float | None = None
    trend_score: float | None = None
    momentum_score: float | None = None
    recommendation_score: float = 0.0
    recommendation_reasons: list[str] = Field(default_factory=list)
    companies: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    cluster_id: str | None = None
    cluster_slug: str | None = None
    article_count: int = 0
    source_count: int = 0


class RecommendationResponse(BaseModel):
    """Paginated response for recommendations."""

    items: list[RecommendationItemResponse] = Field(default_factory=list)
    total: int = 0
    limit: int = 20
    offset: int = 0
    empty_reason: str | None = None


RecommendationSort = Literal["recommendation", "published_at", "importance"]


__all__ = [
    "RecommendationItemResponse",
    "RecommendationResponse",
    "RecommendationSort",
]
