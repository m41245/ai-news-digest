from __future__ import annotations

from collections.abc import Iterator
from typing import cast

from ai_news_digest.application.ai.free_models import (
    FREE_PROVIDER_MODEL_ALLOWLIST,
    is_allowlisted_free_model,
    is_free_only_mode,
)
from ai_news_digest.application.ai.providers.base import AIProvider
from ai_news_digest.exceptions import InvalidPluginError
from ai_news_digest.plugin_registry import PluginRegistry


class ProviderRegistry:
    """Registry for provider plugins.

    This registry intentionally delegates its storage and lookup behavior to the
    generic platform PluginRegistry. It validates provider compatibility before
    registration, but it does not implement routing, scoring, or provider-specific
    selection behavior.
    """

    def __init__(self, free_only: bool | None = None) -> None:
        self._registry = PluginRegistry()
        self._free_only = free_only if free_only is not None else is_free_only_mode()

    def register(self, provider: AIProvider) -> AIProvider:
        """Register a provider plugin using its immutable id."""
        if not isinstance(provider, AIProvider):
            raise InvalidPluginError("Provider registration requires an instance of AIProvider.")

        provider_id = provider.id
        model_name = getattr(provider, "model_name", None)

        if (
            self._free_only or provider_id in FREE_PROVIDER_MODEL_ALLOWLIST
        ) and not is_allowlisted_free_model(provider_id, model_name):
            raise InvalidPluginError(
                f"Provider '{provider_id}' model '{model_name}' is not an "
                "allowlisted free-tier model."
            )

        self._registry.register(provider)
        return provider

    def unregister(self, provider_id: str) -> AIProvider:
        """Remove and return a provider plugin by its id."""
        return cast(AIProvider, self._registry.unregister(provider_id))

    def get(self, provider_id: str) -> AIProvider:
        """Return a provider plugin by its id."""
        return cast(AIProvider, self._registry.get(provider_id))

    def list_all(self) -> list[AIProvider]:
        """Return all registered provider plugins."""
        return [cast(AIProvider, plugin) for plugin in self._registry.list()]

    def exists(self, provider_id: str) -> bool:
        """Return True when a provider id is already registered."""
        return self._registry.exists(provider_id)

    def __contains__(self, provider_id: str) -> bool:
        """Support 'provider_id in registry' checks."""
        return self.exists(provider_id)

    def __len__(self) -> int:
        """Return the number of registered providers."""
        return len(self._registry)

    def __iter__(self) -> Iterator[AIProvider]:
        """Iterate over registered providers."""
        return iter(self.list_all())

    def all(self) -> list[AIProvider]:
        """Return all registered provider plugins."""
        return self.list_all()

    def names(self) -> list[str]:
        """Return all registered provider ids."""
        return [provider.id for provider in self.list_all()]
