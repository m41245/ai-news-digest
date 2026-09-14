"""
Conflict confidence model for M82.

Computes a transparent, deterministic confidence score for a detected conflict.
This is NOT a calibrated statistical model; it is a weighted heuristic.
"""

from __future__ import annotations

from dataclasses import dataclass

from ai_news_digest.domain.enums.conflict_type import ConflictType

_COMPATIBLE_TYPE_GROUPS: dict[str, set[str]] = {
    "quantitative": {"quantitative"},
    "event": {"event", "announcement"},
    "product": {"product", "research"},
    "company": {"company", "event"},
    "policy": {"policy"},
    "general": {"general", "other"},
}

_NUMERIC_CONFIDENCE_BOOST = 0.3
_DATE_CONFIDENCE_BOOST = 0.2
_EVENT_STATE_CONFIDENCE_BOOST = 0.25
_LLM_AGREEMENT_BOOST = 0.1


@dataclass
class ConflictConfidenceFactors:
    """Factors contributing to conflict confidence."""

    entity_match: bool = False
    claim_type_compatible: bool = False
    temporal_compatible: bool = False
    numeric_mismatch: bool = False
    date_mismatch: bool = False
    event_state_mismatch: bool = False
    evidence_support_a: float = 0.0
    evidence_support_b: float = 0.0
    source_independent: bool = False
    llm_agreement: bool = False


def compute_conflict_confidence(
    factors: ConflictConfidenceFactors,
    conflict_type: ConflictType,
) -> float:
    """Compute a deterministic confidence score in [0.0, 1.0].

    Factors:
    - entity_match: +0.3
    - claim_type_compatible: +0.1
    - temporal_compatible: +0.1
    - numeric/date/event mismatch: +0.2-0.3 depending on type
    - evidence support (average of both): +0.0 to +0.2
    - source_independent: +0.1
    - llm_agreement: +0.1
    """
    confidence = 0.0

    if factors.entity_match:
        confidence += 0.3
    if factors.claim_type_compatible:
        confidence += 0.1
    if factors.temporal_compatible:
        confidence += 0.1

    if conflict_type == ConflictType.NUMERIC and factors.numeric_mismatch:
        confidence += _NUMERIC_CONFIDENCE_BOOST
    elif conflict_type == ConflictType.DATE and factors.date_mismatch:
        confidence += _DATE_CONFIDENCE_BOOST
    elif conflict_type == ConflictType.EVENT_STATUS and factors.event_state_mismatch:
        confidence += _EVENT_STATE_CONFIDENCE_BOOST

    avg_evidence = (factors.evidence_support_a + factors.evidence_support_b) / 2.0
    confidence += min(avg_evidence * 0.2, 0.2)

    if factors.source_independent:
        confidence += 0.1

    if factors.llm_agreement:
        confidence += _LLM_AGREEMENT_BOOST

    return min(max(confidence, 0.0), 1.0)


__all__ = ["ConflictConfidenceFactors", "compute_conflict_confidence"]
