from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class AIResponseFormat(StrEnum):
    TEXT = "text"
    JSON = "json"
    MARKDOWN = "markdown"


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
