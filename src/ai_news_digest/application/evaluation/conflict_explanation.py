"""
Conflict explanation utilities for M82.

Generates explainable reasons for detected conflicts.
"""

from __future__ import annotations

from ai_news_digest.domain.enums.conflict_type import ConflictType

EXPLANATION_TEMPLATES: dict[ConflictType, str] = {
    ConflictType.NUMERIC: (
        "Both claims refer to the same subject but report different numeric values."
    ),
    ConflictType.DATE: (
        "The claims describe different dates for the same event."
    ),
    ConflictType.EVENT_STATUS: (
        "The claims describe incompatible event statuses."
    ),
    ConflictType.PRODUCT_ATTRIBUTE: (
        "The claims report different attributes for the same product."
    ),
    ConflictType.COMPANY_STATEMENT: (
        "The claims contain incompatible statements about the same company."
    ),
    ConflictType.AVAILABILITY: (
        "The claims disagree on the availability of the same item."
    ),
    ConflictType.ANNOUNCEMENT: (
        "The claims describe incompatible announcements."
    ),
    ConflictType.QUANTITY: (
        "The claims report different quantities for the same subject."
    ),
    ConflictType.OTHER: (
        "The claims appear to describe incompatible facts about the same subject."
    ),
}


def build_conflict_explanation(
    conflict_type: ConflictType,
    claim_a_text: str,
    claim_b_text: str,
    extra_detail: str = "",
) -> str:
    """Build a structured, explainable conflict explanation."""
    base = EXPLANATION_TEMPLATES.get(
        conflict_type, EXPLANATION_TEMPLATES[ConflictType.OTHER]
    )
    detail = f" {extra_detail}" if extra_detail else ""
    return f"{base}{detail}"


__all__ = ["build_conflict_explanation"]
