from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class StructuredIntelligence:
    """Validated structured intelligence produced by an AI provider.

    All semantic fields are normalized and bounded before persistence.
    """

    summary: str = ""
    key_takeaways: tuple[str, ...] = ()
    why_it_matters: str | None = None
    categories: tuple[str, ...] = ()
    companies: tuple[str, ...] = ()
    topics: tuple[str, ...] = ()
    confidence: float | None = None
    importance: float | None = None

    def __post_init__(self) -> None:
        if not self.summary or not self.summary.strip():
            raise ValueError("summary must not be empty.")
        self.summary = self.summary.strip()

        if len(self.key_takeaways) > 8:
            raise ValueError("key_takeaways must contain at most 8 items.")
        normalized_takeaways: list[str] = []
        for item in self.key_takeaways:
            text = str(item).strip()
            if not text:
                continue
            if len(text) > 300:
                text = text[:297] + "..."
            normalized_takeaways.append(text)
        self.key_takeaways = tuple(normalized_takeaways[:8])

        if self.why_it_matters is not None:
            if not self.why_it_matters.strip():
                raise ValueError("why_it_matters must not be empty.")
            self.why_it_matters = self.why_it_matters.strip()
            if len(self.why_it_matters) > 2000:
                self.why_it_matters = self.why_it_matters[:1997] + "..."

        if self.confidence is not None:
            self.confidence = max(0.0, min(1.0, float(self.confidence)))
        if self.importance is not None:
            self.importance = max(0.0, min(1.0, float(self.importance)))

        self.categories = _dedupe_and_limit(self.categories, limit=5, max_len=64)
        self.companies = _dedupe_and_limit(self.companies, limit=10, max_len=128)
        self.topics = _dedupe_and_limit(self.topics, limit=10, max_len=64)


def _dedupe_and_limit(
    values: tuple[str, ...],
    *,
    limit: int,
    max_len: int,
) -> tuple[str, ...]:
    """Deduplicate (case-insensitive), trim, and bound a tuple of strings."""
    seen: set[str] = set()
    result: list[str] = []
    for raw in values:
        text = str(raw).strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        if len(text) > max_len:
            text = text[: max_len - 1] + "…"
        result.append(text)
        if len(result) >= limit:
            break
    return tuple(result)


def validate_structured_output(data: dict[str, Any]) -> StructuredIntelligence:
    """Validate and coerce a raw provider response dict into StructuredIntelligence.

    Raises ``ValueError`` for irrecoverable validation failures.
    Missing optional fields are replaced with safe defaults.
    """
    if not isinstance(data, dict):
        raise ValueError("AI response must be a JSON object.")

    raw_why = data.get("why_it_matters")
    why_it_matters: str | None = None
    if raw_why is not None:
        text = str(raw_why).strip()
        if text:
            why_it_matters = text

    return StructuredIntelligence(
        summary=str(data.get("summary", "") or ""),
        key_takeaways=tuple(data.get("key_takeaways", []) or []),
        why_it_matters=why_it_matters,
        categories=tuple(data.get("categories", []) or []),
        companies=tuple(data.get("companies", []) or []),
        topics=tuple(data.get("topics", []) or []),
        confidence=data.get("confidence"),
        importance=data.get("importance_score", data.get("importance")),
    )


__all__ = ["StructuredIntelligence", "validate_structured_output"]
