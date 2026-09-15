from __future__ import annotations

from enum import StrEnum


class RelationshipType(StrEnum):
    """Explicit, validated relationship types for the knowledge graph."""

    RELATED_TO = "related_to"
    COMPETES_WITH = "competes_with"
    PARTNERS_WITH = "partners_with"
    COLLABORATES_WITH = "collaborates_with"
    USES_TECHNOLOGY = "uses_technology"
    PROVIDES_TECHNOLOGY_TO = "provides_technology_to"
    ANNOUNCED = "announced"
    MENTIONED_WITH = "mentioned_with"
    ACQUIRED = "acquired"
    ACQUIRED_BY = "acquired_by"
    INVESTS_IN = "invests_in"


__all__ = ["RelationshipType"]
