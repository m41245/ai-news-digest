from __future__ import annotations

from typing import Any


class Contradiction:
    """Represents a detected contradiction between articles."""

    def __init__(self, *, needs_verification: bool = False) -> None:
        self.needs_verification = needs_verification

    def to_dict(self) -> dict[str, Any]:
        return {"needs_verification": self.needs_verification}


def detect_contradictions(timeline: list[Any]) -> list[Contradiction]:
    """Detect contradictions in a cluster timeline."""
    return []
