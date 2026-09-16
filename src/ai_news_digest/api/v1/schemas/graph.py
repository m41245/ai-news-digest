"""
Graph intelligence API schemas for M90/M91.
"""

from __future__ import annotations

from pydantic import BaseModel


class PublicGraphConnectionResponse(BaseModel):
    """A single graph connection for an entity."""

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


class PublicGraphPathResponse(BaseModel):
    """An explainable path between two entities."""

    path: list[dict[str, object]] = []
    length: int = 0
    explanation: str = ""


class PublicEntityConnectionsResponse(BaseModel):
    """Graph connections for a single entity."""

    entity_type: str
    entity_id: str
    connections: list[PublicGraphConnectionResponse] = []
    total: int = 0
    limit: int = 20
    offset: int = 0
    truncated: bool = False


class PublicRelatedStoryGraphResponse(BaseModel):
    """Graph-enriched related story signal."""

    cluster_id: str
    title: str
    graph_score: float = 0.0
    signals: list[str] = []
    explanation: str = ""
    shared_companies: list[str] = []
    shared_topics: list[str] = []
    shared_categories: list[str] = []
    relationship_count: int = 0


class PublicTemporalGraphConnectionResponse(BaseModel):
    """A graph connection enriched with temporal intelligence."""

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
    first_observed_at: str | None = None
    last_observed_at: str | None = None
    observation_count: int = 0
    activity_status: str | None = None
    activity_score: float = 0.0


class PublicEntityEvolutionResponse(BaseModel):
    """Temporal evolution view for an entity."""

    entity_type: str
    entity_id: str
    new_connections: list[dict[str, object]] = []
    recently_active: list[dict[str, object]] = []
    recently_changed: list[dict[str, object]] = []
    historical_connections: list[dict[str, object]] = []
    total_connections: int = 0
    generated_at: str = ""


class PublicRelationshipChangeEventResponse(BaseModel):
    """A detected relationship change event."""

    change_type: str
    relationship_type: str
    object_entity_type: str
    object_entity_id: str
    object_name: str
    observed_at: str | None = None
    explanation: str = ""


class PublicEntityRelationshipHistoryResponse(BaseModel):
    """Bounded relationship history for an entity."""

    entity_type: str
    entity_id: str
    history: list[dict[str, object]] = []
    total: int = 0
    limit: int = 50


class PublicRelationshipActivityResponse(BaseModel):
    """Activity summary for a relationship."""

    relationship_type: str
    status: str
    first_observed_at: str | None = None
    last_observed_at: str | None = None
    observation_count: int = 0
    source_count: int = 0
    activity_score: float = 0.0
    activity_status: str = ""
    explanation: str = ""


__all__ = [
    "PublicEntityConnectionsResponse",
    "PublicEntityEvolutionResponse",
    "PublicEntityRelationshipHistoryResponse",
    "PublicGraphConnectionResponse",
    "PublicGraphPathResponse",
    "PublicRelatedStoryGraphResponse",
    "PublicRelationshipActivityResponse",
    "PublicRelationshipChangeEventResponse",
    "PublicTemporalGraphConnectionResponse",
]
