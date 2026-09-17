"""
Graph intelligence API endpoints for M90/M91.

Provides bounded, explainable graph traversal and discovery:

- Entity connections
- Story cluster connections
- Graph paths between entities
- Entity neighborhoods
- Temporal entity evolution
- Relationship history
- Relationship change detection
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from ai_news_digest.api.v1.dependencies.dependencies import get_container
from ai_news_digest.api.v1.routes._graph_utils import build_graph_name_map
from ai_news_digest.api.v1.schemas.common import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT
from ai_news_digest.api.v1.schemas.graph import (
    PublicEntityConnectionsResponse,
    PublicEntityEvolutionResponse,
    PublicEntityRelationshipHistoryResponse,
    PublicGraphConnectionResponse,
    PublicGraphPathResponse,
    PublicRelationshipChangeEventResponse,
    PublicTemporalGraphConnectionResponse,
)
from ai_news_digest.application.services.graph_intelligence import (
    temporal_graph_intelligence_service as _temporal_graph_module,
)
from ai_news_digest.application.services.graph_intelligence.graph_intelligence_service import (
    GraphIntelligenceService,
)
from ai_news_digest.bootstrap.container import Container
from ai_news_digest.core.config import get_settings
from ai_news_digest.core.exceptions import ResourceNotFoundError

router = APIRouter(
    prefix="/graph",
    tags=["Graph Intelligence"],
)


@router.get(
    "/entities/{entity_type}/{entity_id}/connections",
    response_model=PublicEntityConnectionsResponse,
    summary="Get graph connections for an entity",
)
async def get_entity_connections(
    entity_type: str,
    entity_id: UUID,
    container: Annotated[Container, Depends(get_container)],
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_LIMIT)] = DEFAULT_PAGE_LIMIT,
    offset: Annotated[int, Query(ge=0)] = 0,
    observed_from: Annotated[
        str | None,
        Query(description="Filter relationships observed after this ISO datetime"),
    ] = None,
    observed_to: Annotated[
        str | None,
        Query(description="Filter relationships observed before this ISO datetime"),
    ] = None,
    active_at: Annotated[
        str | None,
        Query(description="Filter relationships active at this ISO datetime"),
    ] = None,
) -> PublicEntityConnectionsResponse:
    """Return bounded, explainable graph connections for an entity."""
    settings = get_settings()
    if not settings.knowledge_graph_enabled:
        return PublicEntityConnectionsResponse(
            entity_type=entity_type,
            entity_id=str(entity_id),
            connections=[],
            total=0,
            limit=limit,
            offset=offset,
        )

    normalized_type = entity_type.lower()
    if normalized_type not in ("company", "topic", "category", "story", "article"):
        return PublicEntityConnectionsResponse(
            entity_type=entity_type,
            entity_id=str(entity_id),
            connections=[],
            total=0,
            limit=limit,
            offset=offset,
        )

    observed_from_dt = datetime.fromisoformat(observed_from) if observed_from else None
    observed_to_dt = datetime.fromisoformat(observed_to) if observed_to else None
    active_at_dt = datetime.fromisoformat(active_at) if active_at else None

    relationships = await container.relationship_repository.list_for_entity_with_temporal(
        entity_type=normalized_type,
        entity_id=entity_id,
        status=None,
        observed_from=observed_from_dt,
        observed_to=observed_to_dt,
        active_at=active_at_dt,
        limit=200,
    )

    service = GraphIntelligenceService()
    name_map = await build_graph_name_map(container, relationships)
    name_map[f"{normalized_type}:{entity_id}"] = f"Self ({normalized_type})"

    connections = service.get_entity_connections(
        entity_type=normalized_type,
        entity_id=str(entity_id),
        relationships=relationships,
        name_resolver=lambda e_type, e_id: name_map.get(f"{e_type}:{e_id}", f"{e_type} {e_id[:8]}"),
    )

    total = len(connections)
    page = connections[offset : offset + limit]

    return PublicEntityConnectionsResponse(
        entity_type=entity_type,
        entity_id=str(entity_id),
        connections=[
            PublicGraphConnectionResponse(
                entity_type=c.entity_type,
                entity_id=c.entity_id,
                name=c.name,
                relationship_type=c.relationship_type,
                status=c.status,
                score=round(c.score, 4),
                signals=c.signals,
                explanation=c.explanation,
                source_count=c.source_count,
                is_disputed=c.is_disputed,
                is_retracted=c.is_retracted,
            )
            for c in page
        ],
        total=total,
        limit=limit,
        offset=offset,
        truncated=total > limit + offset,
    )


@router.get(
    "/story-clusters/{cluster_id}/connections",
    response_model=PublicEntityConnectionsResponse,
    summary="Get graph connections for a story cluster",
)
async def get_story_cluster_connections(
    cluster_id: UUID,
    container: Annotated[Container, Depends(get_container)],
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_LIMIT)] = DEFAULT_PAGE_LIMIT,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PublicEntityConnectionsResponse:
    """Return bounded graph connections for a story cluster."""
    settings = get_settings()
    if not settings.knowledge_graph_enabled:
        return PublicEntityConnectionsResponse(
            entity_type="story",
            entity_id=str(cluster_id),
            connections=[],
            total=0,
            limit=limit,
            offset=offset,
        )

    cluster = await container.story_cluster_repository.get_by_id(cluster_id)
    if cluster is None:
        raise ResourceNotFoundError(f"Story cluster {cluster_id} not found.")

    relationships = await container.relationship_repository.list_for_entity(
        entity_type="story",
        entity_id=cluster_id,
        status=None,
        limit=200,
    )

    service = GraphIntelligenceService()
    name_map = await build_graph_name_map(container, relationships)
    name_map[f"story:{cluster_id}"] = cluster.title

    connections = service.get_entity_connections(
        entity_type="story",
        entity_id=str(cluster_id),
        relationships=relationships,
        name_resolver=lambda e_type, e_id: name_map.get(f"{e_type}:{e_id}", f"{e_type} {e_id[:8]}"),
    )

    total = len(connections)
    page = connections[offset : offset + limit]

    return PublicEntityConnectionsResponse(
        entity_type="story",
        entity_id=str(cluster_id),
        connections=[
            PublicGraphConnectionResponse(
                entity_type=c.entity_type,
                entity_id=c.entity_id,
                name=c.name,
                relationship_type=c.relationship_type,
                status=c.status,
                score=round(c.score, 4),
                signals=c.signals,
                explanation=c.explanation,
                source_count=c.source_count,
                is_disputed=c.is_disputed,
                is_retracted=c.is_retracted,
            )
            for c in page
        ],
        total=total,
        limit=limit,
        offset=offset,
        truncated=total > limit + offset,
    )


@router.get(
    "/path/{source_type}/{source_id}/{target_type}/{target_id}",
    response_model=PublicGraphPathResponse,
    summary="Find explainable path between two entities",
)
async def find_graph_path(
    source_type: str,
    source_id: UUID,
    target_type: str,
    target_id: UUID,
    container: Annotated[Container, Depends(get_container)],
    at_time: Annotated[
        str | None,
        Query(description="Evaluate path at this ISO datetime (optional)"),
    ] = None,
) -> PublicGraphPathResponse:
    """Find a bounded explainable path between two entities."""
    settings = get_settings()
    if not settings.knowledge_graph_enabled:
        return PublicGraphPathResponse()

    at_time_dt = datetime.fromisoformat(at_time) if at_time else None

    relationships = await container.relationship_repository.list_for_entity(
        entity_type=source_type,
        entity_id=source_id,
        status=None,
        limit=200,
    )

    target_rels = await container.relationship_repository.list_for_entity(
        entity_type=target_type,
        entity_id=target_id,
        status=None,
        limit=200,
    )

    all_rels = _deduplicate_relationships(relationships + target_rels)

    if at_time_dt is not None:
        temporal_service = _temporal_graph_module.TemporalGraphIntelligenceService()
        filtered_rels = temporal_service.filter_relationships_at_time(all_rels, at_time_dt)
    else:
        filtered_rels = all_rels

    path_service = GraphIntelligenceService()
    path = path_service.find_path(
        relationships=filtered_rels,
        source_type=source_type,
        source_id=str(source_id),
        target_type=target_type,
        target_id=str(target_id),
    )

    if path is None:
        return PublicGraphPathResponse()

    return PublicGraphPathResponse(
        path=path.path,
        length=path.length,
        explanation=path.explanation,
    )


@router.get(
    "/entities/{entity_type}/{entity_id}/evolution",
    response_model=PublicEntityEvolutionResponse,
    summary="Get temporal evolution view for an entity",
)
async def get_entity_evolution(
    entity_type: str,
    entity_id: UUID,
    container: Annotated[Container, Depends(get_container)],
) -> PublicEntityEvolutionResponse:
    """Return bounded temporal evolution view for an entity."""
    settings = get_settings()
    if not settings.knowledge_graph_enabled:
        return PublicEntityEvolutionResponse(
            entity_type=entity_type,
            entity_id=str(entity_id),
        )

    normalized_type = entity_type.lower()
    if normalized_type not in ("company", "topic", "category", "story", "article"):
        return PublicEntityEvolutionResponse(
            entity_type=entity_type,
            entity_id=str(entity_id),
        )

    relationships = await container.relationship_repository.list_for_entity(
        entity_type=normalized_type,
        entity_id=entity_id,
        status=None,
        limit=200,
    )

    service = _temporal_graph_module.TemporalGraphIntelligenceService()
    name_map = await build_graph_name_map(container, relationships)
    name_map[f"{normalized_type}:{entity_id}"] = f"Self ({normalized_type})"

    now = datetime.now(UTC)
    evolution = service.get_entity_evolution(
        entity_type=normalized_type,
        entity_id=str(entity_id),
        relationships=relationships,
        name_resolver=lambda e_type, e_id: name_map.get(f"{e_type}:{e_id}", f"{e_type} {e_id[:8]}"),
        now=now,
    )

    return PublicEntityEvolutionResponse(
        entity_type=evolution.entity_type,
        entity_id=evolution.entity_id,
        new_connections=evolution.new_connections,
        recently_active=evolution.recently_active,
        recently_changed=evolution.recently_changed,
        historical_connections=evolution.historical_connections,
        total_connections=evolution.total_connections,
        generated_at=evolution.generated_at,
    )


@router.get(
    "/entities/{entity_type}/{entity_id}/history",
    response_model=PublicEntityRelationshipHistoryResponse,
    summary="Get bounded relationship history for an entity",
)
async def get_entity_relationship_history(
    entity_type: str,
    entity_id: UUID,
    container: Annotated[Container, Depends(get_container)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> PublicEntityRelationshipHistoryResponse:
    """Return bounded relationship history for an entity."""
    settings = get_settings()
    if not settings.knowledge_graph_enabled:
        return PublicEntityRelationshipHistoryResponse(
            entity_type=entity_type,
            entity_id=str(entity_id),
        )

    normalized_type = entity_type.lower()
    if normalized_type not in ("company", "topic", "category", "story", "article"):
        return PublicEntityRelationshipHistoryResponse(
            entity_type=entity_type,
            entity_id=str(entity_id),
        )

    history = (
        await container.relationship_repository.get_entity_relationship_history(
            entity_type=normalized_type,
            entity_id=entity_id,
            limit=limit,
        )
    )

    return PublicEntityRelationshipHistoryResponse(
        entity_type=normalized_type,
        entity_id=str(entity_id),
        history=history,
        total=len(history),
        limit=limit,
    )


@router.get(
    "/entities/{entity_type}/{entity_id}/changes",
    response_model=list[PublicRelationshipChangeEventResponse],
    summary="Get relationship change events for an entity",
)
async def get_entity_relationship_changes(
    entity_type: str,
    entity_id: UUID,
    container: Annotated[Container, Depends(get_container)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[PublicRelationshipChangeEventResponse]:
    """Return bounded relationship change events for an entity."""
    settings = get_settings()
    if not settings.knowledge_graph_enabled:
        return []

    normalized_type = entity_type.lower()
    if normalized_type not in ("company", "topic", "category", "story", "article"):
        return []

    relationships = await container.relationship_repository.list_for_entity(
        entity_type=normalized_type,
        entity_id=entity_id,
        status=None,
        limit=200,
    )

    service = _temporal_graph_module.TemporalGraphIntelligenceService()
    name_map = await build_graph_name_map(container, relationships)
    name_map[f"{normalized_type}:{entity_id}"] = f"Self ({normalized_type})"

    now = datetime.now(UTC)
    changes = service.detect_relationship_changes(
        entity_type=normalized_type,
        entity_id=str(entity_id),
        relationships=relationships,
        name_resolver=lambda e_type, e_id: name_map.get(f"{e_type}:{e_id}", f"{e_type} {e_id[:8]}"),
        now=now,
    )

    return [
        PublicRelationshipChangeEventResponse(
            change_type=c.change_type,
            relationship_type=c.relationship_type,
            object_entity_type=c.object_entity_type,
            object_entity_id=c.object_entity_id,
            object_name=c.object_name,
            observed_at=c.observed_at,
            explanation=c.explanation,
        )
        for c in changes[:limit]
    ]


@router.get(
    "/entities/{entity_type}/{entity_id}/temporal-connections",
    response_model=PublicEntityConnectionsResponse,
    summary="Get temporally-enriched graph connections for an entity",
)
async def get_entity_temporal_connections(
    entity_type: str,
    entity_id: UUID,
    container: Annotated[Container, Depends(get_container)],
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_LIMIT)] = DEFAULT_PAGE_LIMIT,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PublicEntityConnectionsResponse:
    """Return temporally-enriched graph connections for an entity."""
    settings = get_settings()
    if not settings.knowledge_graph_enabled:
        return PublicEntityConnectionsResponse(
            entity_type=entity_type,
            entity_id=str(entity_id),
            connections=[],
            total=0,
            limit=limit,
            offset=offset,
        )

    normalized_type = entity_type.lower()
    if normalized_type not in ("company", "topic", "category", "story", "article"):
        return PublicEntityConnectionsResponse(
            entity_type=entity_type,
            entity_id=str(entity_id),
            connections=[],
            total=0,
            limit=limit,
            offset=offset,
        )

    relationships = await container.relationship_repository.list_for_entity(
        entity_type=normalized_type,
        entity_id=entity_id,
        status=None,
        limit=200,
    )

    service = _temporal_graph_module.TemporalGraphIntelligenceService()
    name_map = await build_graph_name_map(container, relationships)
    name_map[f"{normalized_type}:{entity_id}"] = f"Self ({normalized_type})"

    connections = service.get_entity_connections_temporal(
        entity_type=normalized_type,
        entity_id=str(entity_id),
        relationships=relationships,
        name_resolver=lambda e_type, e_id: name_map.get(f"{e_type}:{e_id}", f"{e_type} {e_id[:8]}"),
    )

    total = len(connections)
    page = connections[offset : offset + limit]
    temporal_page = [
        PublicTemporalGraphConnectionResponse(
            entity_type=c.entity_type,
            entity_id=c.entity_id,
            name=c.name,
            relationship_type=c.relationship_type,
            status=c.status,
            score=round(c.score, 4),
            signals=c.signals,
            explanation=c.explanation,
            source_count=c.source_count,
            is_disputed=c.is_disputed,
            is_retracted=c.is_retracted,
            first_observed_at=c.first_observed_at,
            last_observed_at=c.last_observed_at,
            observation_count=c.observation_count,
            activity_status=c.activity_status,
            activity_score=round(c.activity_score, 4),
        )
        for c in page
    ]

    return PublicEntityConnectionsResponse(
        entity_type=entity_type,
        entity_id=str(entity_id),
        connections=temporal_page,  # type: ignore[arg-type]
        total=total,
        limit=limit,
        offset=offset,
        truncated=total > limit + offset,
    )


def _deduplicate_relationships(relationships: list[Any]) -> list[Any]:
    """Deduplicate relationships by canonical key."""
    seen: set[tuple[Any, ...]] = set()
    result: list[Any] = []
    for rel in relationships:
        key = (
            rel.subject_entity_type.value,
            str(rel.subject_entity_id),
            rel.relationship_type.value,
            rel.object_entity_type.value,
            str(rel.object_entity_id),
        )
        if key not in seen:
            seen.add(key)
            result.append(rel)
    return result


__all__ = ["router"]
