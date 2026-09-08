from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def get_provider_priority_provider_id(provider_registry: Any) -> str | None:
    return None


@dataclass
class AnalyzeArticleUseCase:
    """
    Minimal stub implementation for M45 final closure testing.
    """

    def __init__(self, provider_registry: Any, provider_id: str | None) -> None:
        self.provider_registry = provider_registry
        self.provider_id = provider_id
