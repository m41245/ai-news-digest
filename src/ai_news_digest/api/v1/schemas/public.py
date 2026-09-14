"""
Public-facing API response schemas.

These schemas intentionally expose a restricted, enriched view of articles,
digests and categories suitable for unauthenticated consumption. Internal
fields (raw article content, internal IDs, processing details) are omitted or
replaced with human-friendly values.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class PublicArticleResponse(BaseModel):
    """Public view of an article, enriched with source and category names."""

    id: str
    title: str
    url: str
    summary: str | None = None
    status: str
    published_at: str | None = None
    source_name: str | None = None
    category_name: str | None = None
    companies: list[str] | None = None
    topics: list[str] | None = None
    key_takeaways: list[str] | None = None
    why_it_matters: str | None = None
    importance_score: float | None = None
    confidence: float | None = None


class PublicDigestResponse(BaseModel):
    """Public view of a digest."""

    id: str
    title: str
    content: str
    format: str
    generated_at: str
    article_count: int
    top_story_cluster_id: str | None = None
    generation_method: str | None = None
    stories: list[dict[str, Any]] | None = None
    top_story: dict[str, Any] | None = None


class PublicCategoryResponse(BaseModel):
    """Public view of a category."""

    id: str
    name: str
    description: str | None = None


class PublicStoryClusterResponse(BaseModel):
    """Public view of a story cluster."""

    id: str
    title: str
    slug: str
    summary: str | None = None
    first_published_at: str | None = None
    last_updated_at: str | None = None
    importance_score: float | None = None
    confidence: float | None = None
    status: str
    article_count: int = 0
    source_count: int = 0
    recent_articles: list[dict[str, Any]] = []
    timeline: list[dict[str, Any]] = []
    what_changed: list[str] = []
    contradictions: list[dict[str, Any]] = []
    needs_verification: bool = False
    intelligence_confidence: str = "low"


class PublicTopStoryResponse(BaseModel):
    """Public view of the top story."""

    top_story_cluster_id: str | None = None
    top_story_score: float | None = None
    total_candidates: int = 0
    eligible_candidates: int = 0
    ranking_window_start: str | None = None
    ranking_window_end: str | None = None
    generated_at: str
    title: str | None = None
    slug: str | None = None
    summary: str | None = None
    importance_score: float | None = None
    confidence: float | None = None


__all__ = [
    "PublicArticleResponse",
    "PublicCategoryResponse",
    "PublicDigestResponse",
    "PublicStoryClusterResponse",
    "PublicTopStoryResponse",
]
