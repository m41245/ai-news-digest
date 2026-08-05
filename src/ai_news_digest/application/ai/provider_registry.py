from __future__ import annotations

from collections.abc import Iterator

from ai_news_digest.application.ai.providers.base import AIProvider  # type: ignore[import-untyped]


class ProviderRegistry:
    """
    Stores every AI provider available to the application.

    Providers register themselves here during application startup.
    """

    def __init__(self) -> None:
        self._providers: dict[str, AIProvider] = {}

    def register(
        self,
        provider: AIProvider,
    ) -> None:
        """
        Register a provider.

        Existing providers with the same name are replaced.
        """

        self._providers[
            provider.provider_name.lower()
        ] = provider

    def unregister(
        self,
        provider_name: str,
    ) -> None:
        self._providers.pop(
            provider_name.lower(),
            None,
        )

    def get(
        self,
        provider_name: str,
    ) -> AIProvider:
        return self._providers[
            provider_name.lower()
        ]

    def all(self) -> list[AIProvider]:
        return list(self._providers.values())

    def names(self) -> list[str]:
        return list(self._providers.keys())

    def __contains__(
        self,
        provider_name: str,
    ) -> bool:
        return provider_name.lower() in self._providers

    def __len__(self) -> int:
        return len(self._providers)

    def __iter__(self) -> Iterator[AIProvider]:
        return iter(self._providers.values())