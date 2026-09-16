"""
Graph intelligence API endpoints for M90.

Provides bounded, explainable graph traversal and discovery:

- Entity connections
- Story cluster connections
- Graph paths between entities
- Entity neighborhoods
"""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from ai_news_digest.api.v1.dependencies.dependencies import get_container
from ai_news_digest.api.v1.schemas.common import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT
from ai_news_digest.api.v1.schemas.graph import (
    PublicEntityConnectionsResponse,
    PublicGraphConnectionResponse,
    PublicGraphPathResponse,
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

    relationships = await container.relationship_repository.list_for_entity(
        entity_type=normalized_type,
        entity_id=entity_id,
        status=None,
        limit=200,
    )

    service = GraphIntelligenceService()
    name_map = await _build_name_map(container, relationships)
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
    name_map = await _build_name_map(container, relationships)
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
) -> PublicGraphPathResponse:
    """Find a bounded explainable path between two entities."""
    settings = get_settings()
    if not settings.knowledge_graph_enabled:
        return PublicGraphPathResponse()

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

    service = GraphIntelligenceService()
    path = service.find_path(
        relationships=all_rels,
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


async def _build_name_map(
    container: Container,
    relationships: list[Any],
) -> dict[str, str]:
    """Build a map of entity keys to display names."""
    name_map: dict[str, str] = {}
    company_ids: list[str] = []
    topic_ids: list[str] = []
    category_ids: list[str] = []
    story_ids: list[str] = []

    for rel in relationships:
        if rel.object_entity_type.value == "company":
            company_ids.append(str(rel.object_entity_id))
        elif rel.object_entity_type.value == "topic":
            topic_ids.append(str(rel.object_entity_id))
        elif rel.object_entity_type.value == "category":
            category_ids.append(str(rel.object_entity_id))
        elif rel.object_entity_type.value == "story":
            story_ids.append(str(rel.object_entity_id))

        if rel.subject_entity_type.value == "company":
            company_ids.append(str(rel.subject_entity_id))
        elif rel.subject_entity_type.value == "topic":
            topic_ids.append(str(rel.subject_entity_id))
        elif rel.subject_entity_type.value == "category":
            category_ids.append(str(rel.subject_entity_id))
        elif rel.subject_entity_type.value == "story":
            story_ids.append(str(rel.subject_entity_id))

    if company_ids:
        companies = await container.company_repository.list_by_ids(company_ids)
        for c in companies:
            name_map[f"company:{c.id}"] = c.name

    if topic_ids:
        topics = await container.topic_repository.list_by_ids(topic_ids)
        for t in topics:
            name_map[f"topic:{t.id}"] = t.name

    if category_ids:
        unique_cat_ids = list(set(category_ids))
        categories = await container.category_repository.list_by_ids(
            [UUID(cid) for cid in unique_cat_ids]
        )
        for cat in categories:
            name_map[f"category:{cat.id}"] = cat.name

    if story_ids:
        unique_story_ids = list(set(story_ids))
        clusters = await container.story_cluster_repository.get_by_ids(
            [UUID(sid) for sid in unique_story_ids]
        )
        for cluster in clusters:
            name_map[f"story:{cluster.id}"] = cluster.title

    return name_map


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
