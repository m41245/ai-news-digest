from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum


class QuotaWindow(StrEnum):
    """Supported quota window granularities."""

    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    MONTH = "month"

    def window_seconds(self) -> int:
        if self == QuotaWindow.MINUTE:
            return 60
        if self == QuotaWindow.HOUR:
            return 3600
        if self == QuotaWindow.DAY:
            return 86400
        if self == QuotaWindow.MONTH:
            return 2592000
        raise AssertionError(f"Unknown QuotaWindow: {self}")


@dataclass(slots=True)
class QuotaLimit:
    """A single dimension of a provider quota."""

    window: QuotaWindow
    request_limit: int | None = None
    token_limit: int | None = None
    cost_limit: Decimal | None = None

    def __post_init__(self) -> None:
        if self.request_limit is None and self.token_limit is None and self.cost_limit is None:
            raise ValueError(
                "At least one of request_limit, token_limit, or cost_limit must be set."
            )
        if self.request_limit is not None and self.request_limit < 0:
            raise ValueError("request_limit must be >= 0.")
        if self.token_limit is not None and self.token_limit < 0:
            raise ValueError("token_limit must be >= 0.")
        if self.cost_limit is not None and self.cost_limit < 0:
            raise ValueError("cost_limit must be >= 0.")


@dataclass(slots=True)
class ProviderQuotaConfig:
    """Normalized quota configuration for a provider."""

    provider_id: str
    limits: list[QuotaLimit] = field(default_factory=list)

    def limit_for(self, window: QuotaWindow) -> QuotaLimit | None:
        for limit in self.limits:
            if limit.window == window:
                return limit
        return None

    def has_limit(self, window: QuotaWindow) -> bool:
        return self.limit_for(window) is not None


@dataclass(slots=True)
class ProviderUsage:
    """Normalized usage recorded for a single provider request."""

    provider_id: str
    request_count: int = 1
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: Decimal = Decimal("0")
    usage_known: bool = False
    cost_known: bool = False
    window: QuotaWindow = QuotaWindow.DAY
    recorded_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if self.total_tokens == 0 and (self.input_tokens > 0 or self.output_tokens > 0):
            object.__setattr__(self, "total_tokens", self.input_tokens + self.output_tokens)
        if self.usage_known and self.total_tokens == 0:
            object.__setattr__(self, "total_tokens", self.input_tokens + self.output_tokens)


@dataclass(slots=True)
class QuotaEligibility:
    """Result of a quota eligibility check."""

    eligible: bool
    reason: str
    quota: ProviderQuotaConfig | None = None
    limit: QuotaLimit | None = None
    remaining_requests: int | None = None
    remaining_tokens: int | None = None
    remaining_cost: Decimal | None = None


@dataclass(slots=True)
class GlobalBudgetState:
    """Global AI budget state."""

    daily_budget: Decimal = Decimal("0")
    monthly_budget: Decimal = Decimal("0")
    daily_spend: Decimal = Decimal("0")
    monthly_spend: Decimal = Decimal("0")
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def daily_remaining(self) -> Decimal:
        return max(Decimal("0"), self.daily_budget - self.daily_spend)

    @property
    def monthly_remaining(self) -> Decimal:
        return max(Decimal("0"), self.monthly_budget - self.monthly_spend)

    @property
    def daily_exhausted(self) -> bool:
        return self.daily_budget > 0 and self.daily_spend >= self.daily_budget

    @property
    def monthly_exhausted(self) -> bool:
        return self.monthly_budget > 0 and self.monthly_spend >= self.monthly_budget


@dataclass(slots=True)
class QuotaExhaustionInfo:
    """Details about quota exhaustion for routing decisions."""

    provider_id: str
    window: QuotaWindow
    limit_type: str
    exhausted_at: datetime = field(default_factory=lambda: datetime.now(UTC))


__all__ = [
    "GlobalBudgetState",
    "ProviderQuotaConfig",
    "ProviderUsage",
    "QuotaEligibility",
    "QuotaExhaustionInfo",
    "QuotaLimit",
    "QuotaWindow",
]
