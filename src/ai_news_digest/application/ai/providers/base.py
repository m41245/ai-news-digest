from __future__ import annotations

from abc import ABC, abstractmethod

from ai_news_digest.application.ai.models import (
    AIRequest,
    AIResponse,
)
from ai_news_digest.plugin import Plugin


class AIProvider(Plugin, ABC):
    """
    Base interface implemented by every AI provider.

    The rest of the application never talks directly to
    OpenAI, Gemini, Claude, Groq, etc.

    It only communicates with this interface.
    """

    @abstractmethod
    async def available(self) -> bool:
        """Return True when the provider can currently accept requests."""

    @abstractmethod
    def priority(self) -> int:
        """Return the provider priority used during selection."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """
        Human-readable provider name.
        """

    @property
    @abstractmethod
    def model_name(self) -> str:
        """
        Active model.
        """

    @property
    @abstractmethod
    def supports_streaming(self) -> bool:
        ...

    @property
    @abstractmethod
    def supports_json_mode(self) -> bool:
        ...

    @property
    @abstractmethod
    def supports_vision(self) -> bool:
        ...

    @property
    @abstractmethod
    def max_context_tokens(self) -> int:
        ...

    @abstractmethod
    async def is_available(self) -> bool:
        """
        Returns True if the provider can currently accept requests.
        """

    @abstractmethod
    async def generate(
        self,
        request: AIRequest,
    ) -> AIResponse:
        """
        Execute one AI request.
        """

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Lightweight connectivity test.
        """