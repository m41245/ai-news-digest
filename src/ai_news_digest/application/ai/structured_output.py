from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StructuredIntelligence(BaseModel):
    """Validated structured intelligence produced by an AI provider.

    All semantic fields are normalized and bounded before persistence.
    """

    model_config = ConfigDict(frozen=True)

    summary: str = Field(..., min_length=1)
    key_takeaways: tuple[str, ...] = Field(default_factory=tuple)
    why_it_matters: str | None = Field(default=None)
    categories: tuple[str, ...] = Field(default_factory=tuple)
    companies: tuple[str, ...] = Field(default_factory=tuple)
    topics: tuple[str, ...] = Field(default_factory=tuple)
    confidence: float | None = Field(default=None)
    importance: float | None = Field(default=None)

    @field_validator("summary", mode="before")
    @classmethod
    def _strip_summary(cls, value: Any) -> str:
        text = str(value).strip()
        if not text:
            raise ValueError("summary must not be empty.")
        return text

    @field_validator("key_takeaways", mode="before")
    @classmethod
    def _normalize_takeaways(cls, value: Any) -> tuple[str, ...]:
        if value is None:
            return ()
        if isinstance(value, str):
            value = [value]
        items = [str(item).strip() for item in value]
        non_empty = [text for text in items if text]
        if len(non_empty) > 8:
            raise ValueError("key_takeaways must contain at most 8 items.")
        result: list[str] = []
        for text in non_empty:
            if len(text) > 300:
                text = text[:297] + "..."
            result.append(text)
        return tuple(result)

    @field_validator("why_it_matters", mode="before")
    @classmethod
    def _normalize_why_it_matters(cls, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            raise ValueError("why_it_matters must not be empty.")
        if len(text) > 2000:
            text = text[:1997] + "..."
        return text

    @field_validator("categories", mode="before")
    @classmethod
    def _dedupe_categories(cls, value: Any) -> tuple[str, ...]:
        return _dedupe_and_limit(value, limit=5, max_len=64)

    @field_validator("companies", mode="before")
    @classmethod
    def _dedupe_companies(cls, value: Any) -> tuple[str, ...]:
        return _dedupe_and_limit(value, limit=10, max_len=128)

    @field_validator("topics", mode="before")
    @classmethod
    def _dedupe_topics(cls, value: Any) -> tuple[str, ...]:
        return _dedupe_and_limit(value, limit=10, max_len=64)

    @field_validator("confidence", mode="before")
    @classmethod
    def _coerce_confidence(cls, value: Any) -> float | None:
        if value is None:
            return None
        return max(0.0, min(1.0, float(value)))

    @field_validator("importance", mode="before")
    @classmethod
    def _coerce_importance(cls, value: Any) -> float | None:
        if value is None:
            return None
        return max(0.0, min(1.0, float(value)))


def _dedupe_and_limit(values: Any, *, limit: int, max_len: int) -> tuple[str, ...]:
    """Deduplicate (case-insensitive), trim, and bound a tuple of strings."""
    seen: set[str] = set()
    result: list[str] = []
    if values is None:
        return ()
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

    raw_importance = data.get("importance_score", data.get("importance"))
    raw_why = data.get("why_it_matters")

    try:
        return StructuredIntelligence(
            summary=data.get("summary", "") or "",
            key_takeaways=data.get("key_takeaways", []) or [],
            why_it_matters=raw_why if raw_why is not None else None,
            categories=data.get("categories", []) or [],
            companies=data.get("companies", []) or [],
            topics=data.get("topics", []) or [],
            confidence=data.get("confidence"),
            importance=raw_importance,
        )
    except Exception as exc:
        raise ValueError(f"Invalid structured analysis: {exc}") from exc


__all__ = ["StructuredIntelligence", "validate_structured_output"]
