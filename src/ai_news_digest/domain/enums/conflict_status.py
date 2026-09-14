from __future__ import annotations

from enum import StrEnum


class ConflictStatus(StrEnum):
    """Status of a detected conflict."""

    POTENTIAL = "potential"
    CONFIRMED = "confirmed"
    DISMISSED = "dismissed"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


__all__ = ["ConflictStatus"]
