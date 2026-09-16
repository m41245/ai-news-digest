"""
Knowledge graph relationship API endpoints.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from ai_news_digest.api.v1.dependencies.dependencies import get_container
from ai_news_digest.api.v1.schemas.common import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT
from ai_news_digest.api.v1.schemas.relationship import (
    PublicEntityRelationshipsResponse,
    PublicRelationshipResponse,
    PublicStoryRelationshipsResponse,
)
from ai_news_digest.bootstrap.container import Container
from ai_news_digest.core.config import get_settings
from ai_news_digest.core.exceptions import ResourceNotFoundError

router = APIRouter(
    prefix="/relationships",
    tags=["Knowledge Graph"],
)


@router.get(
    "/entities/{entity_type}/{entity_id}",
    response_model=PublicEntityRelationshipsResponse,
    summary="Get relationships for an entity",
)
async def get_entity_relationships(
    entity_type: str,
    entity_id: UUID,
    container: Annotated[Container, Depends(get_container)],
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_LIMIT)] = DEFAULT_PAGE_LIMIT,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PublicEntityRelationshipsResponse:
    """Return knowledge graph relationships for a specific entity."""
    settings = get_settings()
    if not settings.knowledge_graph_enabled:
        return PublicEntityRelationshipsResponse(
            entity_type=entity_type,
            entity_id=str(entity_id),
            relationships=[],
        )

    relationships = await container.relationship_repository.list_for_entity(
        entity_type=entity_type,
        entity_id=entity_id,
        status="verified",
        limit=limit,
        offset=offset,
    )

    return PublicEntityRelationshipsResponse(
        entity_type=entity_type,
        entity_id=str(entity_id),
        relationships=[
            PublicRelationshipResponse(
                id=str(r.id),
                subject_entity_type=r.subject_entity_type.value,
                subject_entity_id=str(r.subject_entity_id),
                relationship_type=r.relationship_type.value,
                object_entity_type=r.object_entity_type.value,
                object_entity_id=str(r.object_entity_id),
                status=r.status.value,
                confidence=r.confidence,
                provenance_source=r.provenance_source.value,
                observed_at=r.observed_at.isoformat() if r.observed_at else None,
                first_observed_at=r.first_observed_at.isoformat() if r.first_observed_at else None,
                last_observed_at=r.last_observed_at.isoformat() if r.last_observed_at else None,
                observation_count=r.observation_count,
                source_count=r.source_count,
                activity_status=r.activity_status.value if r.activity_status else None,
                activity_score=r.activity_score,
            )
            for r in relationships
        ],
    )


@router.get(
    "/story-clusters/{cluster_id}",
    response_model=PublicStoryRelationshipsResponse,
    summary="Get relationship summary for a story cluster",
)
async def get_story_cluster_relationships(
    cluster_id: UUID,
    container: Annotated[Container, Depends(get_container)],
) -> PublicStoryRelationshipsResponse:
    """Return a compact relationship summary for a story cluster."""
    settings = get_settings()
    if not settings.knowledge_graph_enabled:
        return PublicStoryRelationshipsResponse(cluster_id=str(cluster_id))

    cluster = await container.story_cluster_repository.get_by_id(cluster_id)
    if cluster is None:
        raise ResourceNotFoundError(f"Story cluster {cluster_id} not found.")

    relationships = await container.relationship_repository.list_for_entity(
        entity_type="story",
        entity_id=cluster_id,
        status="verified",
        limit=200,
    )

    related_companies: list[str] = []
    related_topics: list[str] = []
    for r in relationships:
        if r.object_entity_type.value == "company":
            related_companies.append(str(r.object_entity_id))
        elif r.object_entity_type.value == "topic":
            related_topics.append(str(r.object_entity_id))

    company_names: list[str] = []
    if related_companies:
        companies = await container.company_repository.list_by_ids(related_companies)
        company_names = [c.name for c in companies]

    topic_names: list[str] = []
    if related_topics:
        topics = await container.topic_repository.list_by_ids(related_topics)
        topic_names = [t.name for t in topics]

    return PublicStoryRelationshipsResponse(
        cluster_id=str(cluster_id),
        related_companies=company_names,
        related_topics=topic_names,
        relationship_count=len(relationships),
    )


__all__ = ["router"]
