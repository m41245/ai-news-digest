from __future__ import annotations

from ai_news_digest.application.ai.capability import Capability


class CapabilityRegistry:
    """Registry of capability-to-provider relationships.

    This registry does not own provider instances or provider lifecycle behavior.
    It stores only capability metadata and the provider identifiers that advertise
    those capabilities. The provider registry remains the source of truth for the
    concrete provider objects themselves.
    """

    def __init__(self) -> None:
        self._capabilities: dict[str, Capability] = {}
        self._providers_by_capability: dict[str, set[str]] = {}

    def register_capability(self, capability: Capability) -> Capability:
        """Register a new capability definition."""
        if capability.id in self._capabilities:
            raise ValueError(f"Capability with id '{capability.id}' is already registered.")

        self._capabilities[capability.id] = capability
        self._providers_by_capability.setdefault(capability.id, set())
        return capability

    def remove_capability(self, capability_id: str) -> Capability:
        """Remove a capability definition and all of its provider mappings."""
        if capability_id not in self._capabilities:
            raise KeyError(f"Capability with id '{capability_id}' was not found.")

        capability = self._capabilities.pop(capability_id)
        self._providers_by_capability.pop(capability_id, None)
        return capability

    def register_provider(self, capability_id: str, provider_id: str) -> None:
        """Associate a provider id with an existing capability."""
        if capability_id not in self._capabilities:
            raise KeyError(f"Capability with id '{capability_id}' was not found.")

        self._providers_by_capability.setdefault(capability_id, set()).add(provider_id)

    def remove_provider(self, capability_id: str, provider_id: str) -> None:
        """Remove a provider id from a capability mapping."""
        providers = self._providers_by_capability.get(capability_id)
        if providers is None:
            raise KeyError(f"Capability with id '{capability_id}' was not found.")

        try:
            providers.remove(provider_id)
        except KeyError as exc:
            raise KeyError(
                f"Provider with id '{provider_id}' was not found for capability '{capability_id}'."
            ) from exc

        if not providers:
            self._providers_by_capability.pop(capability_id, None)

    def providers_for(self, capability_id: str) -> set[str]:
        """Return all provider ids that advertise a given capability."""
        if capability_id not in self._capabilities:
            raise KeyError(f"Capability with id '{capability_id}' was not found.")

        return set(self._providers_by_capability.get(capability_id, set()))

    def capabilities(self) -> list[Capability]:
        """Return all registered capability definitions."""
        return list(self._capabilities.values())

    def exists(self, capability_id: str) -> bool:
        """Return True when a capability id is already registered."""
        return capability_id in self._capabilities


__all__ = ["CapabilityRegistry"]
