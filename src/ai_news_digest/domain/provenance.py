"""
Intelligence provenance model for M92.

Provides a unified provenance abstraction across all intelligence entities.
Reuses existing ProvenanceSource from Relationship and extends the concept
to claims, evidence, conflicts, articles, story clusters, trends, and events.

Provenance is inferred deterministically from existing AI metadata fields.
No new database columns are required for the core model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from ai_news_digest.domain.models.relationship import ProvenanceSource


class IntelligenceType(StrEnum):
    """Type of intelligence entity."""

    ARTICLE = "article"
    CLAIM = "claim"
    EVIDENCE = "evidence"
    CONFLICT = "conflict"
    STORY_CLUSTER = "story_cluster"
    STORY_EVENT = "story_event"
    STORY_ACTIVITY = "story_activity"
    TREND = "trend"
    RELATIONSHIP = "relationship"
    DIGEST = "digest"
    RANKING = "ranking"
    RECOMMENDATION = "recommendation"


@dataclass(slots=True)
class ProvenanceInfo:
    """Structured provenance for any intelligence entity."""

    intelligence_type: IntelligenceType
    entity_id: str
    source: ProvenanceSource
    ai_provider: str | None = None
    ai_model: str | None = None
    prompt_version: str | None = None
    schema_version: str = "v1"
    processing_timestamp: str | None = None
    detection_version: str | None = None
    lineage: list[str] = field(default_factory=list)
    is_complete: bool = True
    completeness_gaps: list[str] = field(default_factory=list)


def _first_set(*values: Any) -> Any:
    """Return the first non-None value."""
    for value in values:
        if value is not None:
            return value
    return None


def _infer_provenance_source(*, ai_provider: str | None, ai_model: str | None) -> ProvenanceSource:
    """Infer ProvenanceSource from AI metadata fields."""
    if ai_provider is not None or ai_model is not None:
        return ProvenanceSource.AI_EXTRACTED
    return ProvenanceSource.DETERMINISTIC


def for_article(article: Any) -> ProvenanceInfo:
    """Build provenance info for an Article."""
    source = _infer_provenance_source(
        ai_provider=getattr(article, "ai_provider", None),
        ai_model=getattr(article, "ai_model", None),
    )
    lineage: list[str] = []
    if getattr(article, "source_id", None):
        lineage.append(f"source:{article.source_id}")
    if getattr(article, "cluster_id", None):
        lineage.append(f"cluster:{article.cluster_id}")
    if getattr(article, "category_id", None):
        lineage.append(f"category:{article.category_id}")

    gaps: list[str] = []
    if source == ProvenanceSource.AI_EXTRACTED:
        if not getattr(article, "ai_provider", None):
            gaps.append("ai_provider")
        if not getattr(article, "ai_model", None):
            gaps.append("ai_model")
        if not getattr(article, "ai_processed_at", None):
            gaps.append("ai_processed_at")

    return ProvenanceInfo(
        intelligence_type=IntelligenceType.ARTICLE,
        entity_id=str(getattr(article, "id", "")),
        source=source,
        ai_provider=getattr(article, "ai_provider", None),
        ai_model=getattr(article, "ai_model", None),
        prompt_version=getattr(article, "ai_prompt_version", None),
        schema_version=getattr(article, "schema_version", "v1"),
        processing_timestamp=(
            getattr(article, "ai_processed_at", None).isoformat()  # type: ignore[union-attr]
            if getattr(article, "ai_processed_at", None)
            else None
        ),
        lineage=lineage,
        is_complete=len(gaps) == 0,
        completeness_gaps=gaps,
    )


def for_claim(claim: Any) -> ProvenanceInfo:
    """Build provenance info for a Claim."""
    source = _infer_provenance_source(
        ai_provider=getattr(claim, "ai_provider", None),
        ai_model=getattr(claim, "ai_model", None),
    )
    lineage: list[str] = []
    if getattr(claim, "article_id", None):
        lineage.append(f"article:{claim.article_id}")
    if getattr(claim, "source_id", None):
        lineage.append(f"source:{claim.source_id}")

    gaps: list[str] = []
    if source == ProvenanceSource.AI_EXTRACTED:
        if not getattr(claim, "ai_provider", None):
            gaps.append("ai_provider")
        if not getattr(claim, "ai_model", None):
            gaps.append("ai_model")
        if not getattr(claim, "prompt_version", None):
            gaps.append("prompt_version")

    return ProvenanceInfo(
        intelligence_type=IntelligenceType.CLAIM,
        entity_id=str(getattr(claim, "id", "")),
        source=source,
        ai_provider=getattr(claim, "ai_provider", None),
        ai_model=getattr(claim, "ai_model", None),
        prompt_version=getattr(claim, "prompt_version", None),
        schema_version=getattr(claim, "schema_version", "v1"),
        processing_timestamp=(
            getattr(claim, "created_at", None).isoformat()  # type: ignore[union-attr]
            if getattr(claim, "created_at", None)
            else None
        ),
        lineage=lineage,
        is_complete=len(gaps) == 0,
        completeness_gaps=gaps,
    )


def for_evidence(evidence: Any) -> ProvenanceInfo:
    """Build provenance info for Evidence."""
    source = ProvenanceSource.DETERMINISTIC
    lineage: list[str] = []
    if getattr(evidence, "claim_id", None):
        lineage.append(f"claim:{evidence.claim_id}")
    if getattr(evidence, "article_id", None):
        lineage.append(f"article:{evidence.article_id}")

    return ProvenanceInfo(
        intelligence_type=IntelligenceType.EVIDENCE,
        entity_id=str(getattr(evidence, "id", "")),
        source=source,
        schema_version="v1",
        processing_timestamp=(
            getattr(evidence, "created_at", None).isoformat()  # type: ignore[union-attr]
            if getattr(evidence, "created_at", None)
            else None
        ),
        lineage=lineage,
        is_complete=bool(lineage),
        completeness_gaps=[] if lineage else ["article_id", "claim_id"],
    )


def for_conflict(conflict: Any) -> ProvenanceInfo:
    """Build provenance info for a Conflict."""
    source = ProvenanceSource.DETERMINISTIC
    lineage: list[str] = []
    if getattr(conflict, "claim_a_id", None):
        lineage.append(f"claim_a:{conflict.claim_a_id}")
    if getattr(conflict, "claim_b_id", None):
        lineage.append(f"claim_b:{conflict.claim_b_id}")
    if getattr(conflict, "article_a_id", None):
        lineage.append(f"article_a:{conflict.article_a_id}")
    if getattr(conflict, "article_b_id", None):
        lineage.append(f"article_b:{conflict.article_b_id}")
    if getattr(conflict, "story_cluster_id", None):
        lineage.append(f"story_cluster:{conflict.story_cluster_id}")

    return ProvenanceInfo(
        intelligence_type=IntelligenceType.CONFLICT,
        entity_id=str(getattr(conflict, "id", "")),
        source=source,
        detection_version=getattr(conflict, "detection_version", None),
        processing_timestamp=(
            getattr(conflict, "created_at", None).isoformat()  # type: ignore[union-attr]
            if getattr(conflict, "created_at", None)
            else None
        ),
        lineage=lineage,
        is_complete=len([x for x in lineage if x.startswith("claim_")]) >= 2,
        completeness_gaps=(
            []
            if len([x for x in lineage if x.startswith("claim_")]) >= 2
            else ["claim_a_id", "claim_b_id"]
        ),
    )


def for_relationship(relationship: Any) -> ProvenanceInfo:
    """Build provenance info for a Relationship."""
    lineage: list[str] = []
    if getattr(relationship, "article_id", None):
        lineage.append(f"article:{relationship.article_id}")
    if getattr(relationship, "story_cluster_id", None):
        lineage.append(f"story_cluster:{relationship.story_cluster_id}")
    if getattr(relationship, "claim_id", None):
        lineage.append(f"claim:{relationship.claim_id}")
    if getattr(relationship, "evidence_id", None):
        lineage.append(f"evidence:{relationship.evidence_id}")

    gaps: list[str] = []
    if not lineage:
        gaps.append("article_id, story_cluster_id, claim_id, or evidence_id")

    return ProvenanceInfo(
        intelligence_type=IntelligenceType.RELATIONSHIP,
        entity_id=str(getattr(relationship, "id", "")),
        source=getattr(relationship, "provenance_source", ProvenanceSource.DETERMINISTIC),
        ai_provider=getattr(relationship, "ai_provider", None),
        ai_model=getattr(relationship, "ai_model", None),
        prompt_version=getattr(relationship, "ai_prompt_version", None),
        schema_version=getattr(relationship, "schema_version", "v1"),
        processing_timestamp=(
            getattr(relationship, "created_at", None).isoformat()  # type: ignore[union-attr]
            if getattr(relationship, "created_at", None)
            else None
        ),
        lineage=lineage,
        is_complete=len(gaps) == 0,
        completeness_gaps=gaps,
    )


def for_story_cluster(cluster: Any) -> ProvenanceInfo:
    """Build provenance info for a StoryCluster."""
    lineage: list[str] = []
    if getattr(cluster, "representative_article_id", None):
        lineage.append(f"article:{cluster.representative_article_id}")
    if getattr(cluster, "latest_article_id", None):
        lineage.append(f"article_latest:{cluster.latest_article_id}")

    return ProvenanceInfo(
        intelligence_type=IntelligenceType.STORY_CLUSTER,
        entity_id=str(getattr(cluster, "id", "")),
        source=ProvenanceSource.DETERMINISTIC,
        processing_timestamp=(
            getattr(cluster, "created_at", None).isoformat()  # type: ignore[union-attr]
            if getattr(cluster, "created_at", None)
            else None
        ),
        lineage=lineage,
        is_complete=bool(lineage),
        completeness_gaps=[] if lineage else ["representative_article_id"],
    )


def for_story_event(event: Any) -> ProvenanceInfo:
    """Build provenance info for a StoryEvent."""
    lineage: list[str] = []
    if getattr(event, "story_cluster_id", None):
        lineage.append(f"story_cluster:{event.story_cluster_id}")
    if getattr(event, "representative_article_id", None):
        lineage.append(f"article:{event.representative_article_id}")

    gaps: list[str] = []
    if getattr(event, "ai_provider", None) or getattr(event, "ai_model", None):
        if not getattr(event, "ai_provider", None):
            gaps.append("ai_provider")
        if not getattr(event, "ai_model", None):
            gaps.append("ai_model")
        source = ProvenanceSource.AI_EXTRACTED
    else:
        source = ProvenanceSource.DETERMINISTIC

    return ProvenanceInfo(
        intelligence_type=IntelligenceType.STORY_EVENT,
        entity_id=str(getattr(event, "id", "")),
        source=source,
        ai_provider=getattr(event, "ai_provider", None),
        ai_model=getattr(event, "ai_model", None),
        prompt_version=getattr(event, "prompt_version", None),
        schema_version=getattr(event, "schema_version", "v1"),
        processing_timestamp=(
            getattr(event, "created_at", None).isoformat()  # type: ignore[union-attr]
            if getattr(event, "created_at", None)
            else None
        ),
        lineage=lineage,
        is_complete=len(gaps) == 0,
        completeness_gaps=gaps,
    )


def for_trend(trend: Any) -> ProvenanceInfo:
    """Build provenance info for a Trend."""
    lineage: list[str] = []
    for cid in list(getattr(trend, "related_company_ids", []) or [])[:5]:
        lineage.append(f"company:{cid}")
    for tid in list(getattr(trend, "related_topic_ids", []) or [])[:5]:
        lineage.append(f"topic:{tid}")
    for cid in list(getattr(trend, "related_category_ids", []) or [])[:5]:
        lineage.append(f"category:{cid}")

    return ProvenanceInfo(
        intelligence_type=IntelligenceType.TREND,
        entity_id=str(getattr(trend, "id", "")),
        source=ProvenanceSource.DETERMINISTIC,
        processing_timestamp=(
            getattr(trend, "created_at", None).isoformat()  # type: ignore[union-attr]
            if getattr(trend, "created_at", None)
            else None
        ),
        lineage=lineage,
        is_complete=bool(lineage),
        completeness_gaps=[] if lineage else ["related_company_ids", "related_topic_ids"],
    )


def for_digest(digest: Any) -> ProvenanceInfo:
    """Build provenance info for a Digest."""
    lineage: list[str] = []
    for aid in list(getattr(digest, "article_ids", []) or [])[:10]:
        lineage.append(f"article:{aid}")
    if getattr(digest, "top_story_cluster_id", None):
        lineage.append(f"top_story:{digest.top_story_cluster_id}")

    gaps: list[str] = []
    if getattr(digest, "provider", None) or getattr(digest, "model", None):
        if not getattr(digest, "provider", None):
            gaps.append("provider")
        if not getattr(digest, "model", None):
            gaps.append("model")
        source = ProvenanceSource.AI_EXTRACTED
    else:
        source = ProvenanceSource.DETERMINISTIC

    return ProvenanceInfo(
        intelligence_type=IntelligenceType.DIGEST,
        entity_id=str(getattr(digest, "id", "")),
        source=source,
        ai_provider=getattr(digest, "provider", None),
        ai_model=getattr(digest, "model", None),
        schema_version="v1",
        processing_timestamp=getattr(digest, "generated_at", None),
        lineage=lineage,
        is_complete=len(gaps) == 0,
        completeness_gaps=gaps,
    )


__all__ = [
    "IntelligenceType",
    "ProvenanceInfo",
    "for_article",
    "for_claim",
    "for_conflict",
    "for_digest",
    "for_evidence",
    "for_relationship",
    "for_story_cluster",
    "for_story_event",
    "for_trend",
]
