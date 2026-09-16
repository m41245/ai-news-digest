"""
API schemas for intelligence quality and provenance (M92).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ProvenanceResponse(BaseModel):
    """Provenance information for an intelligence entity."""

    intelligence_type: str
    entity_id: str
    source: str | None = None
    ai_provider: str | None = None
    ai_model: str | None = None
    prompt_version: str | None = None
    schema_version: str = "v1"
    processing_timestamp: str | None = None
    detection_version: str | None = None
    lineage: list[str] = []
    is_complete: bool = True
    completeness_gaps: list[str] = []


class QualityFlagResponse(BaseModel):
    """A single quality flag."""

    flag: str
    severity: str = "warning"


class IntelligenceQualityResponse(BaseModel):
    """Quality assessment for an intelligence entity."""

    entity_type: str
    entity_id: str
    flags: list[str] = []
    evidence_count: int = 0
    source_count: int = 0
    independent_source_count: int = 0
    conflict_present: bool = False
    conflict_count: int = 0
    provenance_complete: bool = True
    freshness: str = "unknown"
    overall_score: float = 0.0
    explanation: str = ""


class PublicProvenancedClaimResponse(BaseModel):
    """Public view of a claim with provenance."""

    claim: str
    type: str
    confidence: float | None = None
    status: str
    evidence_support_score: float | None = None
    provenance_source: str | None = None
    schema_version: str = "v1"
    prompt_version: str | None = None
    evidence: list[dict[str, Any]] | None = None


class PublicProvenancedEvidenceResponse(BaseModel):
    """Public view of evidence with bounded provenance."""

    evidence_type: str
    excerpt: str | None = None
    source_location: str | None = None
    strength: str | None = None
    article_title: str | None = None
    source_name: str | None = None
    published_at: str | None = None


class PublicProvenancedArticleResponse(BaseModel):
    """Public view of an article with provenance metadata."""

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
    claims: list[PublicProvenancedClaimResponse] | None = None
    provenance_source: str | None = None
    ai_provider: str | None = None
    ai_model: str | None = None
    ai_processed_at: str | None = None
    extraction_quality: str | None = None


class PublicProvenancedRelationshipResponse(BaseModel):
    """Public view of a relationship with provenance."""

    id: str
    subject_entity_type: str
    subject_entity_id: str
    relationship_type: str
    object_entity_type: str
    object_entity_id: str
    status: str
    confidence: float | None = None
    provenance_source: str | None = None
    ai_provider: str | None = None
    ai_model: str | None = None
    observed_at: str | None = None
    first_observed_at: str | None = None
    last_observed_at: str | None = None
    observation_count: int = 0
    source_count: int = 0
    activity_status: str | None = None
    activity_score: float = 0.0
    explanation: str = ""


class PublicProvenancedStoryClusterResponse(BaseModel):
    """Public view of a story cluster with provenance and quality."""

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
    independent_source_count: int = 0
    recent_articles: list[dict[str, Any]] = []
    timeline: list[dict[str, Any]] = []
    what_changed: list[str] = []
    contradictions: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    needs_verification: bool = False
    intelligence_confidence: str = "low"
    activity_status: str | None = None
    activity_score: float | None = None
    latest_activity_at: str | None = None
    related_companies: list[str] = []
    related_topics: list[str] = []
    relationship_count: int = 0
    graph_connections: list[dict[str, Any]] = []
    provenance_complete: bool = True
    quality_flags: list[str] = []
    quality_explanation: str = ""
    overall_quality_score: float = 0.0


class PublicProvenancedTrendResponse(BaseModel):
    """Public view of a trend with provenance."""

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
    provenance_complete: bool = True
    quality_flags: list[str] = []


__all__ = [
    "IntelligenceQualityResponse",
    "ProvenanceResponse",
    "PublicProvenancedArticleResponse",
    "PublicProvenancedClaimResponse",
    "PublicProvenancedEvidenceResponse",
    "PublicProvenancedRelationshipResponse",
    "PublicProvenancedStoryClusterResponse",
    "PublicProvenancedTrendResponse",
    "QualityFlagResponse",
]
