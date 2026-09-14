from __future__ import annotations

from enum import StrEnum


class EvidenceStrength(StrEnum):
    """Strength of evidence supporting a claim."""

    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    NONE = "none"
