"""
Evidence validation utilities for M81.

Provides deterministic checks for evidence validity and support scoring.
"""

from __future__ import annotations

from typing import Any


def compute_evidence_support_score(
    *,
    source_content: str | None,
    evidence_list: list[object],
) -> float:
    """
    Compute a deterministic evidence support score for a claim.

    Factors checked (each contributes when valid):
    - valid source article content exists
    - evidence list is non-empty
    - each evidence has a bounded excerpt
    - excerpt actually appears in source content (when source content is available)
    - multiple independent evidence anchors

    The score is a float in [0.0, 1.0].

    This is a simple deterministic algorithm. It does NOT perform full
    natural-language entailment.
    """
    if not evidence_list:
        return 0.0

    if not source_content or not source_content.strip():
        return 0.1

    source_lower = source_content.lower()
    valid_evidence_count = 0
    excerpt_match_count = 0
    has_location = False

    for ev in evidence_list:
        excerpt = _get_attr(ev, "excerpt")
        source_location = _get_attr(ev, "source_location")
        anchor = _get_attr(ev, "anchor")

        if excerpt and len(excerpt.strip()) >= 10:
            valid_evidence_count += 1
            if excerpt.lower() in source_lower:
                excerpt_match_count += 1

        if source_location:
            has_location = True

        if anchor is not None:
            has_location = True

    if valid_evidence_count == 0:
        return 0.0

    base_score = 0.3
    if excerpt_match_count > 0:
        base_score += 0.3 * min(excerpt_match_count / valid_evidence_count, 1.0)
    if valid_evidence_count >= 2:
        base_score += 0.2
    if has_location:
        base_score += 0.2

    return min(max(base_score, 0.0), 1.0)


def _get_attr(obj: object, attr: str) -> Any:
    if isinstance(obj, dict):
        return obj.get(attr)
    return getattr(obj, attr, None)


def validate_excerpt_in_source(
    excerpt: str | None,
    source_content: str | None,
) -> bool:
    """Return True if the excerpt appears in the source content."""
    if not excerpt or not source_content:
        return False
    excerpt_lower = excerpt.strip().lower()
    if len(excerpt_lower) < 10:
        return False
    return excerpt_lower in source_content.lower()


def compute_claim_status(
    evidence_support_score: float | None,
) -> str:
    """
    Derive claim status from evidence support score.

    Uses simple thresholds:
    - score >= 0.7 -> SUPPORTED
    - score >= 0.4 -> PARTIALLY_SUPPORTED
    - score > 0.0 -> UNSUPPORTED (some evidence but weak)
    - score == 0.0 or None -> UNVERIFIED
    """
    if evidence_support_score is None:
        return "unverified"
    if evidence_support_score >= 0.7:
        return "supported"
    if evidence_support_score >= 0.4:
        return "partially_supported"
    if evidence_support_score > 0.0:
        return "unsupported"
    return "unverified"


__all__ = [
    "compute_claim_status",
    "compute_evidence_support_score",
    "validate_excerpt_in_source",
]
