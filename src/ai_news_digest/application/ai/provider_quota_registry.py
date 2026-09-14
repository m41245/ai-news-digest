from __future__ import annotations

from abc import ABC, abstractmethod

from ai_news_digest.application.ai.quota import (
    GlobalBudgetState,
    ProviderQuotaConfig,
    ProviderUsage,
    QuotaEligibility,
    QuotaWindow,
)


class ProviderQuotaRegistry(ABC):
    """Abstract store for provider quota configuration and usage state."""

    @abstractmethod
    async def get_provider_quota(self, provider_id: str) -> ProviderQuotaConfig | None:
        """Return the quota configuration for a provider, or None if unconfigured."""

    @abstractmethod
    async def set_provider_quota(self, config: ProviderQuotaConfig) -> None:
        """Persist quota configuration for a provider."""

    @abstractmethod
    async def get_usage(
        self,
        provider_id: str,
        window: QuotaWindow,
    ) -> list[ProviderUsage]:
        """Return recorded usage for a provider in the given window."""

    @abstractmethod
    async def record_usage(self, usage: ProviderUsage) -> None:
        """Record a usage event for a provider."""

    @abstractmethod
    async def check_quota_eligibility(
        self,
        provider_id: str,
        window: QuotaWindow,
        estimated_tokens: int = 0,
        estimated_cost: float = 0.0,
    ) -> QuotaEligibility:
        """Check whether a provider has remaining quota for the given window."""

    @abstractmethod
    async def get_global_budget(self) -> GlobalBudgetState:
        """Return the current global budget state."""

    @abstractmethod
    async def update_global_budget(self, spend: float) -> GlobalBudgetState:
        """Add spend to the global budget and return the updated state."""

    @abstractmethod
    async def reset_provider_quota(self, provider_id: str) -> None:
        """Reset usage counters for a provider (e.g., window rollover)."""

    @abstractmethod
    async def get_all_quota_states(self) -> dict[str, ProviderQuotaConfig]:
        """Return quota configurations for all providers."""


__all__ = ["ProviderQuotaRegistry"]
