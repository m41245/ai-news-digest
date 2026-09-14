"""
Claim normalization and deduplication utilities for M81.

Handles whitespace, case, punctuation, and safe deduplication.
"""

from __future__ import annotations

import re


def normalize_claim_text(text: str) -> str:
    """
    Normalize a claim text for deduplication comparison.

    - Strip whitespace
    - Lowercase
    - Remove punctuation (except internal hyphens and slashes)
    - Collapse whitespace
    """
    text = text.strip().lower()
    text = re.sub(r"[^\w\s/-]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def deduplicate_claims(claims: list[dict[str, object]]) -> list[dict[str, object]]:
    """
    Remove duplicate claims from a list while preserving distinct claims.

    Uses normalized text comparison. Preserves order.
    """
    seen: set[str] = set()
    result: list[dict[str, object]] = []
    for claim in claims:
        raw_text = str(claim.get("claim", "")).strip()
        if not raw_text:
            continue
        normalized = normalize_claim_text(raw_text)
        if normalized in seen:
            continue
        seen.add(normalized)
        result.append(claim)
    return result


__all__ = ["deduplicate_claims", "normalize_claim_text"]
