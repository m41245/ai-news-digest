"""
API routes for intelligence quality and provenance (M92).

Provides authenticated endpoints for quality assessment and provenance
inspection of intelligence entities.
"""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException

from ai_news_digest.api.v1.dependencies.dependencies import get_container
from ai_news_digest.api.v1.schemas.intelligence_quality import (
    IntelligenceQualityResponse,
    ProvenanceResponse,
)
from ai_news_digest.application.services.intelligence_quality_service import (
    IntelligenceQualityService,
)
from ai_news_digest.bootstrap.container import Container
from ai_news_digest.domain.provenance import (
    for_article,
    for_claim,
    for_conflict,
    for_digest,
    for_relationship,
    for_story_cluster,
    for_story_event,
    for_trend,
)

router = APIRouter(
    prefix="/intelligence",
    tags=["Intelligence Quality"],
)


def _to_provenance_response(provenance: Any) -> ProvenanceResponse:
    """Convert ProvenanceInfo to API response."""
    return ProvenanceResponse(
        intelligence_type=provenance.intelligence_type.value,
        entity_id=provenance.entity_id,
        source=provenance.source.value if provenance.source else None,
        ai_provider=provenance.ai_provider,
        ai_model=provenance.ai_model,
        prompt_version=provenance.prompt_version,
        schema_version=provenance.schema_version,
        processing_timestamp=provenance.processing_timestamp,
        detection_version=provenance.detection_version,
        lineage=provenance.lineage[:20],
        is_complete=provenance.is_complete,
        completeness_gaps=provenance.completeness_gaps,
    )


@router.get(
    "/provenance/{entity_type}/{entity_id}",
    response_model=ProvenanceResponse,
    summary="Get provenance for an intelligence entity",
)
async def get_entity_provenance(
    entity_type: str,
    entity_id: str,
    container: Annotated[Container, Depends(get_container)],
) -> ProvenanceResponse:
    """Return provenance information for an intelligence entity."""
    from uuid import UUID

    from ai_news_digest.core.exceptions import ResourceNotFoundError

    try:
        eid = UUID(entity_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid entity_id") from None

    provenance = None
    entity_type_lower = entity_type.lower().replace("-", "_")

    if entity_type_lower == "article":
        article = await container.article_repository.get_by_id(eid)
        if article is None:
            raise ResourceNotFoundError(f"Article {entity_id} not found.")
        provenance = for_article(article)
    elif entity_type_lower == "claim":
        claim = await container.claim_repository.get_by_id(eid)
        if claim is None:
            raise ResourceNotFoundError(f"Claim {entity_id} not found.")
        provenance = for_claim(claim)
    elif entity_type_lower == "conflict":
        conflict = await container.conflict_repository.get_by_id(eid)
        if conflict is None:
            raise ResourceNotFoundError(f"Conflict {entity_id} not found.")
        provenance = for_conflict(conflict)
    elif entity_type_lower == "relationship":
        relationship = await container.relationship_repository.get_by_id(eid)
        if relationship is None:
            raise ResourceNotFoundError(f"Relationship {entity_id} not found.")
        provenance = for_relationship(relationship)
    elif entity_type_lower == "story_cluster":
        cluster = await container.story_cluster_repository.get_by_id(eid)
        if cluster is None:
            raise ResourceNotFoundError(f"Story cluster {entity_id} not found.")
        provenance = for_story_cluster(cluster)
    elif entity_type_lower == "story_event":
        event = await container.story_event_repository.get_by_id(eid)
        if event is None:
            raise ResourceNotFoundError(f"Story event {entity_id} not found.")
        provenance = for_story_event(event)
    elif entity_type_lower == "trend":
        trend = await container.trend_repository.get_by_id(eid)
        if trend is None:
            raise ResourceNotFoundError(f"Trend {entity_id} not found.")
        provenance = for_trend(trend)
    elif entity_type_lower == "digest":
        digest = await container.digest_repository.get_by_id(eid)
        if digest is None:
            raise ResourceNotFoundError(f"Digest {entity_id} not found.")
        provenance = for_digest(digest)
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported entity type: {entity_type}",
        )

    if provenance is None:
        raise ResourceNotFoundError(f"Entity {entity_type}/{entity_id} not found.")

    return _to_provenance_response(provenance)


@router.get(
    "/quality/{entity_type}/{entity_id}",
    response_model=IntelligenceQualityResponse,
    summary="Get quality assessment for an intelligence entity",
)
async def get_entity_quality(
    entity_type: str,
    entity_id: str,
    container: Annotated[Container, Depends(get_container)],
) -> IntelligenceQualityResponse:
    """Return quality diagnostics for an intelligence entity."""
    from uuid import UUID

    from ai_news_digest.core.exceptions import ResourceNotFoundError

    try:
        eid = UUID(entity_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid entity_id") from None

    quality_service = IntelligenceQualityService()
    entity_type_lower = entity_type.lower().replace("-", "_")

    if entity_type_lower == "claim":
        claim = await container.claim_repository.get_by_id(eid)
        if claim is None:
            raise ResourceNotFoundError(f"Claim {entity_id} not found.")
        evidence_items = await container.claim_repository.list_evidence_by_claim_id(eid)
        recent_conflicts = await container.conflict_repository.list_recent(limit=500)
        claim_conflicts = [
            c for c in recent_conflicts
            if c.claim_a_id == eid or c.claim_b_id == eid
        ]
        result = quality_service.evaluate_claim(
            claim=claim,
            evidence_items=evidence_items,
            conflicts=claim_conflicts,
        )
        return IntelligenceQualityResponse(
            entity_type=result.entity_type,
            entity_id=result.entity_id,
            flags=result.flags,
            evidence_count=result.evidence_count,
            source_count=result.source_count,
            independent_source_count=result.independent_source_count,
            conflict_present=result.conflict_present,
            conflict_count=result.conflict_count,
            provenance_complete=result.provenance_complete,
            freshness=result.freshness,
            overall_score=result.overall_score,
            explanation=result.explanation,
        )

    if entity_type_lower == "relationship":
        relationship = await container.relationship_repository.get_by_id(eid)
        if relationship is None:
            raise ResourceNotFoundError(f"Relationship {entity_id} not found.")
        result = quality_service.evaluate_relationship(relationship)
        return IntelligenceQualityResponse(
            entity_type=result.entity_type,
            entity_id=result.entity_id,
            flags=result.flags,
            evidence_count=result.evidence_count,
            source_count=result.source_count,
            independent_source_count=result.independent_source_count,
            conflict_present=result.conflict_present,
            conflict_count=result.conflict_count,
            provenance_complete=result.provenance_complete,
            freshness=result.freshness,
            overall_score=result.overall_score,
            explanation=result.explanation,
        )

    if entity_type_lower == "story_cluster":
        cluster = await container.story_cluster_repository.get_by_id(eid)
        if cluster is None:
            raise ResourceNotFoundError(f"Story cluster {entity_id} not found.")
        articles = await container.article_repository.list_by_cluster_id(cluster_id=eid, limit=500)
        article_count = len(articles)
        unique_source_ids = {a.source_id for a in articles if getattr(a, "source_id", None)}
        source_count = len(unique_source_ids)
        evidence_count = 0
        conflict_count = 0
        try:
            all_claims: list[Any] = []
            for article in articles:
                try:
                    claims = await container.claim_repository.list_by_article_id(article.id)
                    all_claims.extend(claims)
                except Exception:
                    logging.getLogger(__name__).warning(
                        "Failed to list claims for article %s", article.id
                    )
            evidence_count = len(all_claims)
            recent_conflicts = await container.conflict_repository.list_recent(limit=500)
            article_ids = {a.id for a in articles}
            conflict_count = sum(
                1 for c in recent_conflicts
                if getattr(c, "article_a_id", None) in article_ids
                or getattr(c, "article_b_id", None) in article_ids
            )
        except Exception:
            logging.getLogger(__name__).warning(
                "Failed to list conflicts for story cluster %s", cluster.id
            )

        result = quality_service.evaluate_story_cluster(
            cluster=cluster,
            article_count=article_count,
            source_count=source_count,
            evidence_count=evidence_count,
            conflict_count=conflict_count,
        )
        return IntelligenceQualityResponse(
            entity_type=result.entity_type,
            entity_id=result.entity_id,
            flags=result.flags,
            evidence_count=result.evidence_count,
            source_count=result.source_count,
            independent_source_count=result.independent_source_count,
            conflict_present=result.conflict_present,
            conflict_count=result.conflict_count,
            provenance_complete=result.provenance_complete,
            freshness=result.freshness,
            overall_score=result.overall_score,
            explanation=result.explanation,
        )

    if entity_type_lower == "trend":
        trend = await container.trend_repository.get_by_id(eid)
        if trend is None:
            raise ResourceNotFoundError(f"Trend {entity_id} not found.")
        result = quality_service.evaluate_trend(trend)
        return IntelligenceQualityResponse(
            entity_type=result.entity_type,
            entity_id=result.entity_id,
            flags=result.flags,
            evidence_count=result.evidence_count,
            source_count=result.source_count,
            independent_source_count=result.independent_source_count,
            conflict_present=result.conflict_present,
            conflict_count=result.conflict_count,
            provenance_complete=result.provenance_complete,
            freshness=result.freshness,
            overall_score=result.overall_score,
            explanation=result.explanation,
        )

    raise HTTPException(
        status_code=400,
        detail=f"Quality assessment not supported for entity type: {entity_type}",
    )


__all__ = ["router"]
