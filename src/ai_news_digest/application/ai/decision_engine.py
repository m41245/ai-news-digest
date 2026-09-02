from __future__ import annotations

from ai_news_digest.application.ai.capability_registry import CapabilityRegistry
from ai_news_digest.application.ai.provider_registry import ProviderRegistry


class DecisionEngine:
    """Return provider ids that satisfy a set of required capabilities.

    This service intentionally stays generic and metadata-driven. It does not
    execute providers, call external APIs, or contain any provider-specific
    behavior. It only answers capability-based selection questions using the
    platform registries.
    """

    def __init__(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
    ) -> None:
        self._provider_registry = provider_registry
        self._capability_registry = capability_registry

    def resolve(self, required_capabilities: set[str]) -> set[str]:
        """Return provider ids that satisfy all requested capabilities.

        If no capabilities are requested, the result is empty.
        The result is computed using intersection semantics so every provider in
        the result advertises all required capabilities.
        """
        if not required_capabilities:
            return set()

        candidate_ids: set[str] | None = None

        for capability_id in required_capabilities:
            if not self._capability_registry.exists(capability_id):
                return set()

            providers = self._capability_registry.providers_for(capability_id)

            if candidate_ids is None:
                candidate_ids = set(providers)
                continue

            candidate_ids &= providers

        if candidate_ids is None:
            return set()

        return {
            provider_id
            for provider_id in candidate_ids
            if self._provider_registry.exists(provider_id)
        }


__all__ = ["DecisionEngine"]
