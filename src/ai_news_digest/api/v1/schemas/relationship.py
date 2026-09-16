"""
Knowledge graph relationship schemas for M89/M91.
"""

from __future__ import annotations

from pydantic import BaseModel


class PublicRelationshipResponse(BaseModel):
    """Public view of a knowledge graph relationship."""

    id: str
    subject_entity_type: str
    subject_entity_id: str
    relationship_type: str
    object_entity_type: str
    object_entity_id: str
    status: str
    confidence: float | None = None
    provenance_source: str | None = None
    observed_at: str | None = None
    first_observed_at: str | None = None
    last_observed_at: str | None = None
    observation_count: int = 0
    source_count: int = 0
    activity_status: str | None = None
    activity_score: float = 0.0
    explanation: str = ""


class PublicEntityRelationshipsResponse(BaseModel):
    """Relationships for a single entity."""

    entity_type: str
    entity_id: str
    relationships: list[PublicRelationshipResponse]


class PublicStoryRelationshipsResponse(BaseModel):
    """Compact relationship summary for a story cluster."""

    cluster_id: str
    related_companies: list[str] = []
    related_topics: list[str] = []
    relationship_count: int = 0


__all__ = [
    "PublicEntityRelationshipsResponse",
    "PublicRelationshipResponse",
    "PublicStoryRelationshipsResponse",
]
