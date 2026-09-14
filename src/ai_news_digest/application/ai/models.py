from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class AIResponseFormat(StrEnum):
    TEXT = "text"
    JSON = "json"
    MARKDOWN = "markdown"


@dataclass(frozen=True, slots=True)
class RoutingContext:
    """Extensible request-level routing context."""

    capability: str | None = None
    preferred_provider: str | None = None
    excluded_providers: frozenset[str] = frozenset()


@dataclass(slots=True)
class RoutingDecision:
    """Structured outcome of a provider routing decision."""

    selected_provider_id: str | None
    capability: str | None
    candidate_provider_ids: list[str]
    rejected_provider_ids: list[tuple[str, str]]
    attempted_provider_ids: list[str]
    fallback_used: bool
    reason: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AIRequest:
    """
    Universal AI request understood by every provider.
    """

    system_prompt: str
    user_prompt: str

    temperature: float = 0.2
    max_tokens: int = 1024

    response_format: AIResponseFormat = AIResponseFormat.TEXT

    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AIUsage:
    """
    Token usage information returned by providers.
    """

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass(slots=True)
class AIResponse:
    """
    Universal AI response.
    """

    provider: str

    model: str

    content: str

    usage: AIUsage

    latency_ms: float

    metadata: dict[str, Any] = field(default_factory=dict)
