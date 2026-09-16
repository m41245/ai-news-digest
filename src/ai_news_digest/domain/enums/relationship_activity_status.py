from __future__ import annotations

from enum import StrEnum


class RelationshipActivityStatus(StrEnum):
    """Temporal activity state of a knowledge graph relationship."""

    NEW = "new"
    EMERGING = "emerging"
    ACTIVE = "active"
    STABLE = "stable"
    DECLINING = "declining"
    STALE = "stale"


__all__ = ["RelationshipActivityStatus"]
