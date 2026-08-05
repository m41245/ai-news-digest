from __future__ import annotations

from ai_news_digest.application.ai.models import (
    AIRequest,
    AIResponse,
)
from ai_news_digest.application.ai.provider_registry import (
    ProviderRegistry,
)
from ai_news_digest.application.ai.providers.base import (  # type: ignore[import-untyped]
    AIProvider,
)


class ProviderManager:
    """
    Dynamically selects the best available AI provider.

    Future versions will use weighted scoring based on:
        - Quality
        - Cost
        - Latency
        - Reliability
        - Context window
        - Historical performance
    """

    def __init__(
        self,
        registry: ProviderRegistry,
    ) -> None:
        self._registry = registry

    async def generate(
        self,
        request: AIRequest,
    ) -> AIResponse:
        """
        Generate a response using the highest-ranked provider.
        """

        providers = await self._available_providers()

        if not providers:
            raise RuntimeError(
                "No AI providers are currently available."
            )

        last_exception: Exception | None = None

        for provider in providers:
            try:
                return await provider.generate(request)  # type: ignore[no-any-return]

            except Exception as exc:
                last_exception = exc

        raise RuntimeError(
            "Every AI provider failed."
        ) from last_exception

    async def _available_providers(
        self,
    ) -> list[AIProvider]:
        """
        Return providers sorted by priority.

        Version 1:
            Uses provider.priority()

        Future:
            Uses weighted scoring engine.
        """

        available: list[AIProvider] = []

        for provider in self._registry:
            if await provider.available():
                available.append(provider)

        available.sort(
            key=lambda provider: provider.priority(),
            reverse=True,
        )

        return available