from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping

from ai_news_digest.application.ai.provider_health import ProviderHealthState


class ProviderHealthRegistry(ABC):
    """Abstract provider health and circuit breaker state store."""

    @abstractmethod
    async def get_state(self, provider_id: str) -> ProviderHealthState:
        """Return the current health state for a provider."""

    @abstractmethod
    async def record_success(self, provider_id: str) -> ProviderHealthState:
        """Record a successful request and return the updated state."""

    @abstractmethod
    async def record_failure(
        self,
        provider_id: str,
        category: str,
    ) -> ProviderHealthState:
        """Record a failed request and return the updated state."""

    @abstractmethod
    async def is_eligible(self, provider_id: str) -> bool:
        """Return True when the provider is eligible to receive requests."""

    @abstractmethod
    async def try_acquire_probe_lease(self, provider_id: str) -> bool:
        """Attempt to acquire the half-open probe lease.

        Returns True if the lease was acquired, False otherwise.
        Only one concurrent probe per provider is permitted.
        """

    @abstractmethod
    async def release_probe_lease(self, provider_id: str) -> None:
        """Release the half-open probe lease."""

    @abstractmethod
    async def reset(self, provider_id: str) -> ProviderHealthState:
        """Reset provider health to CLOSED and return the updated state."""

    @abstractmethod
    async def get_all_states(self) -> Mapping[str, ProviderHealthState]:
        """Return health states for all known providers."""


__all__ = ["ProviderHealthRegistry"]
