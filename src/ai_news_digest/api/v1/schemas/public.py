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

from ai_news_digest.api.v1.schemas.common import PaginatedResponse


class PublicConflictResponse(BaseModel):
    """Public view of a detected conflict."""

    conflict_type: str
    status: str
    confidence: float | None = None
    explanation: str
    claim_a_text: str | None = None
    claim_b_text: str | None = None
    source_a_name: str | None = None
    source_b_name: str | None = None
    same_source: bool = False
    published_at_a: str | None = None
    published_at_b: str | None = None


class PublicEvidenceResponse(BaseModel):
    """Public view of a single evidence item."""

    evidence_type: str
    excerpt: str | None = None
    source_location: str | None = None
    strength: str | None = None


class PublicClaimResponse(BaseModel):
    """Public view of a single claim."""

    claim: str
    type: str
    confidence: float | None = None
    status: str
    evidence_support_score: float | None = None
    evidence: list[PublicEvidenceResponse] | None = None


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
    claims: list[PublicClaimResponse] | None = None


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
    conflicts: list[PublicConflictResponse] = []
    needs_verification: bool = False
    intelligence_confidence: str = "low"
    activity_status: str | None = None
    activity_score: float | None = None
    latest_activity_at: str | None = None
    related_companies: list[str] = []
    related_topics: list[str] = []
    relationship_count: int = 0


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
    activity_status: str | None = None
    activity_score: float | None = None


class PublicCompanyResponse(BaseModel):
    """Public view of a company for discovery."""

    id: str
    name: str
    description: str | None = None
    article_count: int = 0


class PublicTopicResponse(BaseModel):
    """Public view of a topic for discovery."""

    id: str
    name: str
    description: str | None = None
    article_count: int = 0


class PublicStoryClusterSearchResponse(BaseModel):
    """Lightweight search result for a story cluster."""

    id: str
    title: str
    slug: str
    summary: str | None = None
    first_published_at: str | None = None
    importance_score: float | None = None
    confidence: float | None = None
    status: str
    article_count: int = 0
    source_count: int = 0
    activity_status: str | None = None
    activity_score: float | None = None
    latest_activity_at: str | None = None


class PublicTrendSearchResponse(BaseModel):
    """Lightweight search result for a trend."""

    id: str
    trend_type: str
    display_name: str
    status: str
    trend_score: float
    momentum_score: float
    recent_activity: int = 0
    baseline_activity: int = 0
    source_count: int = 0
    story_count: int = 0
    event_count: int = 0
    explanation: str
    first_detected_at: str | None = None
    last_detected_at: str | None = None


class PublicTrendResponse(BaseModel):
    """Public view of a trend."""

    id: str
    trend_type: str
    display_name: str
    status: str
    trend_score: float
    momentum_score: float
    recent_activity: int = 0
    baseline_activity: int = 0
    source_count: int = 0
    story_count: int = 0
    event_count: int = 0
    explanation: str
    first_detected_at: str | None = None
    last_detected_at: str | None = None
    trend_metadata: dict[str, str] | None = None


class SearchResponse(BaseModel):
    """Combined search results across articles and story clusters."""

    articles: PaginatedResponse[PublicArticleResponse]
    stories: PaginatedResponse[PublicStoryClusterSearchResponse]


class RelatedStoryResponse(BaseModel):
    """Public view of a related story cluster."""

    cluster_id: str
    title: str
    summary: str | None = None
    similarity: float = 0.0
    article_count: int = 0
    source_count: int = 0
    reason: str = "Semantically related"


__all__ = [
    "PublicArticleResponse",
    "PublicCategoryResponse",
    "PublicCompanyResponse",
    "PublicDigestResponse",
    "PublicStoryClusterResponse",
    "PublicStoryClusterSearchResponse",
    "PublicTopStoryResponse",
    "PublicTopicResponse",
    "PublicTrendResponse",
    "PublicTrendSearchResponse",
    "RelatedStoryResponse",
    "SearchResponse",
]
