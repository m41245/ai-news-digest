from __future__ import annotations


def normalize_topic(raw: str) -> str | None:
    """Normalize a raw topic string.

    - Strips surrounding whitespace.
    - Collapses internal whitespace.
    - Returns ``None`` for empty strings.

    Casing is preserved as-is; deduplication should be case-insensitive
    at the call site.
    """
    cleaned = " ".join(raw.split())
    if not cleaned:
        return None
    return cleaned


def dedupe_topics(topics: tuple[str, ...]) -> tuple[str, ...]:
    """Deduplicate topics case-insensitively, preserving first-seen casing."""
    seen: set[str] = set()
    result: list[str] = []
    for raw in topics:
        normalized = normalize_topic(raw)
        if normalized is None:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(normalized)
    return tuple(result)


__all__ = ["dedupe_topics", "normalize_topic"]
