"""
Graph intelligence API schemas for M90.
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


__all__ = [
    "PublicEntityConnectionsResponse",
    "PublicGraphConnectionResponse",
    "PublicGraphPathResponse",
    "PublicRelatedStoryGraphResponse",
]
