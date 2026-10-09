from __future__ import annotations

from abc import ABC, abstractmethod

from ai_news_digest.application.ai.quota import (
    GlobalBudgetState,
    ProviderQuotaConfig,
    ProviderUsage,
    QuotaEligibility,
    QuotaLimit,
    QuotaReservationRequest,
    QuotaReservationResult,
    QuotaWindow,
    ReleaseResult,
    ReservationState,
    SettlementResult,
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
        limit: QuotaLimit | None = None,
    ) -> QuotaEligibility:
        """Check whether a provider has remaining quota for the given window.

        When ``limit`` is omitted, the limit for ``window`` is loaded from the
        registry's stored quota configuration. When provided, the supplied limit
        is used directly and the registry performs only the usage-accounting
        check against Redis. This lets callers driven by settings-defined limits
        enforce them without first persisting them to Redis.
        """

    @abstractmethod
    async def reserve_capacity(
        self,
        request: QuotaReservationRequest,
    ) -> QuotaReservationResult:
        """Atomically check limits and global budget, then record a reservation.

        The reservation holds estimated capacity until it is either settled
        (with actual usage) or released.  Concurrent calls compete atomically
        for remaining capacity.  When a required limit or budget cannot be
        verified due to a store failure, the reservation fails closed.
        """

    @abstractmethod
    async def settle_reservation(
        self,
        reservation_id: str,
        actual_usage: ProviderUsage,
        actual_cost: float | None = None,
    ) -> SettlementResult:
        """Reconcile a reservation against actual provider usage.

        Atomically releases the reserved capacity and records the actual
        usage and spend.  Idempotent: repeated calls for the same
        reservation must not double-count.  A reservation that was
        released or already settled returns without additional side
        effects.
        """

    @abstractmethod
    async def release_reservation(self, reservation_id: str) -> ReleaseResult:
        """Release a pending reservation, freeing reserved capacity.

        Idempotent: calling release on an already-released or settled
        reservation is a safe no-op.  Releasing a settled reservation
        does not refund consumed capacity.
        """

    @abstractmethod
    async def get_reservation(self, reservation_id: str) -> ReservationState | None:
        """Return the current state of a reservation, or None if not found."""

    @abstractmethod
    async def list_outstanding_reservations(self) -> list[ReservationState]:
        """Return all reservations that are not yet settled or released."""

    @abstractmethod
    async def expire_reservations(self, max_age_seconds: int = 86400) -> int:
        """Mark pending reservations older than *max_age_seconds* as expired.

        Returns the number of reservations transitioned to the expired state.
        Expired reservations remain in the expired state and are not
        automatically settled.
        """

    @abstractmethod
    async def reconcile_reservations(
        self,
        max_age_seconds: int = 86400,
        batch_limit: int | None = None,
    ) -> int:
        """Expired reservations must be released so reserved capacity is freed.

        Marks pending reservations older than *max_age_seconds* as expired,
        then releases each expired reservation — returning the reserved
        capacity to the available pool.  When *batch_limit* is provided, at
        most that many reservations are released per call so a large backlog
        cannot monopolise a single worker cycle.  Returns the number of
        reservations reconciled (expired-and-released) in this batch.  Reservations
        that were already settled or released are skipped.
        """

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
