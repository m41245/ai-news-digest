from __future__ import annotations

from ai_news_digest.application.ai.models import (
    AIRequest,
    AIResponse,
)
from ai_news_digest.application.ai.provider_registry import (
    ProviderRegistry,
)
from ai_news_digest.application.ai.providers.base import (
    AIProvider,
)
from ai_news_digest.core.exceptions import ExternalServiceError


class ProviderManager:
    """Dynamically selects the best available AI provider."""

    def __init__(
        self,
        registry: ProviderRegistry,
    ) -> None:
        self._registry = registry

    async def generate(
        self,
        request: AIRequest,
    ) -> AIResponse:
        """Generate a response using the highest-ranked provider."""
        providers = await self._available_providers()

        if not providers:
            raise ExternalServiceError("No AI providers are currently available.")

        last_exception: Exception | None = None

        for provider in providers:
            try:
                return await provider.generate(request)

            except Exception as exc:
                last_exception = exc

        raise ExternalServiceError("Every AI provider failed.") from last_exception

    async def _available_providers(
        self,
    ) -> list[AIProvider]:
        """Return providers sorted by priority."""
        available: list[AIProvider] = []

        for provider in self._registry:
            if await provider.available():
                available.append(provider)

        available.sort(
            key=lambda provider: provider.priority(),
            reverse=True,
        )

        return available
