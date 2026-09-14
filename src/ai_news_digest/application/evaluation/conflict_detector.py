"""
Deterministic conflict detection for M82.

Implements numeric, date, and event-state conflict detection using
rule-based heuristics. These detectors are conservative and prefer
false negatives over false positives.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ai_news_digest.domain.enums.conflict_status import ConflictStatus
from ai_news_digest.domain.enums.conflict_type import ConflictType
from ai_news_digest.domain.models.claim import Claim

if TYPE_CHECKING:
    pass


# Event states that are incompatible with each other.
_INCOMPATIBLE_STATES: dict[str, set[str]] = {
    "announced": {"cancelled", "denied"},
    "planned": {"cancelled", "completed"},
    "launched": {"cancelled", "delayed", "denied"},
    "completed": {"planned", "cancelled", "denied"},
    "acquired": {"denied"},
    "partnered": {"denied"},
    "cancelled": {"announced", "planned", "launched", "completed"},
    "delayed": {"launched", "completed"},
    "denied": {"announced", "acquired", "partnered", "launched", "completed"},
}

# Keywords mapping to event states.
_STATE_KEYWORDS: dict[str, str] = {
    "launched": "launched",
    "released": "launched",
    "shipped": "launched",
    "available": "launched",
    "available now": "launched",
    "now available": "launched",
    "announced": "announced",
    "unveiled": "announced",
    "revealed": "announced",
    "planned": "planned",
    "plans": "planned",
    "plan": "planned",
    "upcoming": "planned",
    "expected": "planned",
    "scheduled": "planned",
    "will launch": "planned",
    "will release": "planned",
    "will introduce": "planned",
    "completed": "completed",
    "finished": "completed",
    "finalized": "completed",
    "acquired": "acquired",
    "purchased": "acquired",
    "bought": "acquired",
    "partnered": "partnered",
    "collaborated": "partnered",
    "cancelled": "cancelled",
    "canceled": "cancelled",
    "denied": "denied",
    "rejected": "denied",
    "delayed": "delayed",
    "postponed": "delayed",
}


@dataclass
class DeterministicResult:
    """Result of deterministic conflict detection."""

    conflict_type: ConflictType | None
    status: ConflictStatus
    confidence: float
    explanation: str
    aspects: list[str]


def _extract_numbers(text: str) -> list[tuple[float, str | None]]:
    """Extract numbers with optional units from text."""
    results: list[tuple[float, str | None]] = []
    patterns = [
        r"(\d+(?:\.\d+)?)\s*(billion|million|thousand|percent|%|b|m|k)\b",
        r"(\d+(?:\.\d+)?)\s*(parameters|param|users|employees|dollars|\$|usd|euro|eur|gb|tb|mb|kb|units?|items?)\b",
        r"(\d+(?:\.\d+)?)\s*[x]\s*(\d+(?:\.\d+)?)",
        r"(\d+(?:\.\d+)?)\s*(?:to|-)\s*(\d+(?:\.\d+)?)",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            try:
                value = float(match.group(1))
                unit = (
                    match.group(2)
                    if match.lastindex is not None and match.lastindex >= 2
                    else None
                )
                results.append((value, unit))
            except (ValueError, IndexError):
                continue
    if not results:
        simple = re.findall(r"\b(\d+(?:\.\d+)?)\b", text)
        for num_str in simple:
            try:
                results.append((float(num_str), None))
            except ValueError:
                continue
    return results


def _normalize_number(value: float, unit: str | None) -> tuple[float, str | None]:
    """Normalize a number and unit for comparison."""
    if unit is None:
        return value, None
    unit_lower = unit.lower()
    multiplier = 1.0
    if unit_lower in {"billion", "b"}:
        multiplier = 1_000_000_000
    elif unit_lower in {"million", "m"}:
        multiplier = 1_000_000
    elif unit_lower in {"thousand", "k"}:
        multiplier = 1_000
    elif unit_lower in {"percent", "%"}:
        multiplier = 0.01
    elif unit_lower in {"tb"}:
        multiplier = 1024 ** 4
    elif unit_lower in {"gb"}:
        multiplier = 1024 ** 3
    elif unit_lower in {"mb"}:
        multiplier = 1024 ** 2
    elif unit_lower in {"kb"}:
        multiplier = 1024
    return value * multiplier, unit_lower


def detect_numeric_conflict(
    claim_a: Claim,
    claim_b: Claim,
) -> DeterministicResult | None:
    """Detect potential numeric conflicts between two claims."""
    numbers_a = _extract_numbers(claim_a.claim_text)
    numbers_b = _extract_numbers(claim_b.claim_text)
    if not numbers_a or not numbers_b:
        return None

    unit_to_values_a: dict[str | None, list[float]] = {}
    for val, unit in numbers_a:
        norm_val, norm_unit = _normalize_number(val, unit)
        unit_to_values_a.setdefault(norm_unit, []).append(norm_val)

    unit_to_values_b: dict[str | None, list[float]] = {}
    for val, unit in numbers_b:
        norm_val, norm_unit = _normalize_number(val, unit)
        unit_to_values_b.setdefault(norm_unit, []).append(norm_val)

    for unit in unit_to_values_a:
        if unit not in unit_to_values_b:
            continue
        vals_a = unit_to_values_a[unit]
        vals_b = unit_to_values_b[unit]
        min_a, max_a = min(vals_a), max(vals_a)
        min_b, max_b = min(vals_b), max(vals_b)

        if len(vals_a) == 1 and len(vals_b) == 1:
            if min_a == min_b:
                continue
        else:
            if min_a == max_b or min_b == max_a:
                continue
            if max_a >= min_b and max_b >= min_a:
                continue
            if max_a < min_b or max_b < min_a:
                continue

        unit_desc = f" with unit '{unit}'" if unit else ""
        return DeterministicResult(
            conflict_type=ConflictType.NUMERIC,
            status=ConflictStatus.POTENTIAL,
            confidence=0.6,
            explanation=(
                f"Both claims report different numeric values{unit_desc} "
                f"for the same subject."
            ),
            aspects=["differing_value"],
        )

    return None


def detect_date_conflict(
    claim_a: Claim,
    claim_b: Claim,
) -> DeterministicResult | None:
    """Detect potential date conflicts between two claims."""
    date_patterns = [
        r"\b((?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}(?:,\s*\d{4})?)\b",
        r"\b(\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)\b",
        r"\b(in\s+\d{4})\b",
        r"\b((?:q[1-4]\s*\d{4}|early\s+\d{4}|mid\s+\d{4}|late\s+\d{4}))\b",
        r"\b((?:202[0-9]|203[0-9]))\b",
    ]
    dates_a: list[str] = []
    dates_b: list[str] = []
    for pattern in date_patterns:
        dates_a.extend(re.findall(pattern, claim_a.claim_text, re.IGNORECASE))
        dates_b.extend(re.findall(pattern, claim_b.claim_text, re.IGNORECASE))

    if not dates_a or not dates_b:
        return None

    normalized_a = {d.lower().strip() for d in dates_a}
    normalized_b = {d.lower().strip() for d in dates_b}
    common = normalized_a & normalized_b
    if common:
        return None

    if normalized_a.isdisjoint(normalized_b):
        return DeterministicResult(
            conflict_type=ConflictType.DATE,
            status=ConflictStatus.POTENTIAL,
            confidence=0.5,
            explanation=(
                "Both claims contain different dates for what appears "
                "to be the same event."
            ),
            aspects=["differing_date"],
        )

    return None


def _detect_state(text: str) -> str | None:
    """Detect event state mentioned in text."""
    text_lower = text.lower()
    best_state: str | None = None
    best_pos = -1
    for keyword, state in _STATE_KEYWORDS.items():
        pos = text_lower.find(keyword)
        if pos != -1 and (best_pos == -1 or pos < best_pos):
            best_state = state
            best_pos = pos
    return best_state


def detect_event_state_conflict(
    claim_a: Claim,
    claim_b: Claim,
) -> DeterministicResult | None:
    """Detect potential event-state conflicts between two claims."""
    state_a = _detect_state(claim_a.claim_text)
    state_b = _detect_state(claim_b.claim_text)
    if state_a is None or state_b is None:
        return None
    if state_a == state_b:
        return None
    incompatible = _INCOMPATIBLE_STATES.get(state_a, set())
    if state_b in incompatible:
        return DeterministicResult(
            conflict_type=ConflictType.EVENT_STATUS,
            status=ConflictStatus.POTENTIAL,
            confidence=0.55,
            explanation=(
                f"Claims describe incompatible event states: "
                f"'{state_a}' vs '{state_b}'."
            ),
            aspects=["differing_status"],
        )
    return None


def run_deterministic_detection(
    claim_a: Claim,
    claim_b: Claim,
) -> DeterministicResult | None:
    """Run all deterministic detectors on a claim pair.

    Returns the strongest deterministic result, or None if no conflict
    is detected deterministically.
    """
    numeric = detect_numeric_conflict(claim_a, claim_b)
    if numeric is not None:
        return numeric

    date = detect_date_conflict(claim_a, claim_b)
    if date is not None:
        return date

    event = detect_event_state_conflict(claim_a, claim_b)
    if event is not None:
        return event

    return None


__all__ = [
    "DeterministicResult",
    "detect_date_conflict",
    "detect_event_state_conflict",
    "detect_numeric_conflict",
    "run_deterministic_detection",
]
