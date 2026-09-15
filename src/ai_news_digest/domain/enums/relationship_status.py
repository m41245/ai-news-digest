from __future__ import annotations

from enum import StrEnum


class RelationshipStatus(StrEnum):
    """Evidence-backed status of a knowledge graph relationship."""

    CANDIDATE = "candidate"
    VERIFIED = "verified"
    DISPUTED = "disputed"
    RETRACTED = "retracted"
    INACTIVE = "inactive"


__all__ = ["RelationshipStatus"]
