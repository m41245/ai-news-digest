"""Pydantic schemas for the Story Intelligence Brief API (M95)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class BriefSourceItem(BaseModel):
    """Public view of a source contributing to the story."""

    publisher: str
    source_type: str
    source_role: str
    article_count: int
    provenance_source: str | None = None
    articles: list[dict[str, Any]] | None = None


class BriefEvidenceItem(BaseModel):
    """Public view of a single evidence item for a claim."""

    evidence_type: str
    excerpt: str | None = None
    source_location: str | None = None
    strength: str | None = None
    article_title: str | None = None
    source_name: str | None = None
    published_at: str | None = None


class BriefClaimItem(BaseModel):
    """Public view of a claim with bounded evidence."""

    claim_text: str
    type: str
    status: str
    confidence: float | None = None
    evidence_support_score: float | None = None
    evidence_count: int = 0
    evidence: list[BriefEvidenceItem] | None = None
    provenance_source: str | None = None


class BriefConflictItem(BaseModel):
    """Public view of a conflict/contradiction between claims."""

    conflict_type: str
    status: str
    confidence: float | None = None
    explanation: str
    source_a_name: str | None = None
    source_b_name: str | None = None
    same_source: bool = False
    published_at_a: str | None = None
    published_at_b: str | None = None


class BriefTimelineItem(BaseModel):
    """Public view of a timeline entry."""

    id: str | None = None
    title: str | None = None
    url: str | None = None
    summary: str | None = None
    published_at: str | None = None
    source_name: str | None = None
    source_type: str | None = None
    source_role: str | None = None
    importance_score: float | None = None
    confidence: float | None = None


class BriefTrendContext(BaseModel):
    """Public view of a trend this story belongs to."""

    id: str
    trend_type: str
    display_name: str
    status: str
    trend_score: float
    momentum_score: float
    explanation: str | None = None


class BriefEntityContext(BaseModel):
    """Public view of an entity related to the story."""

    id: str
    name: str
    entity_type: str


class BriefGraphConnection(BaseModel):
    """Public view of a graph connection."""

    entity_type: str
    entity_id: str
    name: str
    relationship_type: str | None = None
    status: str | None = None
    score: float = 0.0
    signals: list[str] = []
    explanation: str = ""
    source_count: int = 0
    is_disputed: bool = False
    is_retracted: bool = False


class BriefRelatedStoryItem(BaseModel):
    """Public view of a related story cluster."""

    cluster_id: str
    title: str
    summary: str | None = None
    similarity: float = 0.0
    article_count: int = 0
    source_count: int = 0
    reason: str = ""


class BriefProvenanceInfo(BaseModel):
    """Public provenance indicators for the brief."""

    source: str
    article_count: int
    ai_generated_count: int
    deterministic_count: int
    is_complete: bool
    completeness_gaps: list[str] = []


class BriefQualityIndicators(BaseModel):
    """Public quality indicators for the brief."""

    overall_quality_score: float = 0.0
    quality_flags: list[str] = []
    quality_explanation: str = ""
    evidence_coverage: float = 0.0
    source_coverage: float = 0.0
    conflict_count: int = 0
    health_status: str = "insufficient_data"
    degraded: bool = False
    degraded_message: str | None = None


class BriefPersonalizationContext(BaseModel):
    """Optional personalization context."""

    user_id: str
    relevance_reason: str | None = None
    matched_companies: list[str] = []
    matched_topics: list[str] = []


class StoryIntelligenceBriefResponse(BaseModel):
    """Complete Story Intelligence Brief response."""

    id: str
    title: str
    slug: str
    status: str
    importance_score: float | None = None
    confidence: float | None = None
    ranking_score: float | None = None
    ranking_explanation: str | None = None
    first_published_at: str | None = None
    last_updated_at: str | None = None
    article_count: int = 0
    source_count: int = 0
    independent_source_count: int = 0

    summary: str | None = None
    key_takeaways: list[str] = []
    why_it_matters: str | None = None

    activity_status: str | None = None
    activity_score: float | None = None
    latest_activity_at: str | None = None

    sources: list[BriefSourceItem] = []

    claims: list[BriefClaimItem] = []

    conflicts: list[BriefConflictItem] = []

    timeline: list[BriefTimelineItem] = []

    story_evolution: dict[str, Any] | None = None

    trends: list[BriefTrendContext] | None = None

    entities: dict[str, Any] | None = None

    related_stories: list[BriefRelatedStoryItem] = []

    provenance: BriefProvenanceInfo | None = None

    quality: BriefQualityIndicators | None = None

    updated_at: str | None = None

    personalization: BriefPersonalizationContext | None = None


__all__ = [
    "BriefClaimItem",
    "BriefConflictItem",
    "BriefEntityContext",
    "BriefEvidenceItem",
    "BriefGraphConnection",
    "BriefPersonalizationContext",
    "BriefProvenanceInfo",
    "BriefQualityIndicators",
    "BriefRelatedStoryItem",
    "BriefSourceItem",
    "BriefTimelineItem",
    "BriefTrendContext",
    "StoryIntelligenceBriefResponse",
]
