"""
Unit tests for M79 quota models.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from ai_news_digest.application.ai.quota import (
    GlobalBudgetState,
    ProviderQuotaConfig,
    ProviderUsage,
    QuotaEligibility,
    QuotaLimit,
    QuotaWindow,
)


class TestQuotaWindow:
    """Tests for QuotaWindow enum."""

    def test_minute_window_seconds(self) -> None:
        assert QuotaWindow.MINUTE.window_seconds() == 60

    def test_hour_window_seconds(self) -> None:
        assert QuotaWindow.HOUR.window_seconds() == 3600

    def test_day_window_seconds(self) -> None:
        assert QuotaWindow.DAY.window_seconds() == 86400

    def test_month_window_seconds(self) -> None:
        assert QuotaWindow.MONTH.window_seconds() == 2592000

    def test_unknown_window_raises(self) -> None:
        with pytest.raises(ValueError):
            QuotaWindow("year")


class TestQuotaLimit:
    """Tests for QuotaLimit dataclass."""

    def test_valid_limit_with_all_fields(self) -> None:
        limit = QuotaLimit(
            window=QuotaWindow.DAY,
            request_limit=100,
            token_limit=10000,
            cost_limit=Decimal("5.0"),
        )
        assert limit.window == QuotaWindow.DAY
        assert limit.request_limit == 100
        assert limit.token_limit == 10000
        assert limit.cost_limit == Decimal("5.0")

    def test_valid_limit_with_only_requests(self) -> None:
        limit = QuotaLimit(window=QuotaWindow.DAY, request_limit=50)
        assert limit.request_limit == 50
        assert limit.token_limit is None
        assert limit.cost_limit is None

    def test_valid_limit_with_only_tokens(self) -> None:
        limit = QuotaLimit(window=QuotaWindow.HOUR, token_limit=5000)
        assert limit.request_limit is None
        assert limit.token_limit == 5000

    def test_valid_limit_with_only_cost(self) -> None:
        limit = QuotaLimit(window=QuotaWindow.MONTH, cost_limit=Decimal("10.0"))
        assert limit.request_limit is None
        assert limit.token_limit is None
        assert limit.cost_limit == Decimal("10.0")

    def test_no_limits_raises(self) -> None:
        with pytest.raises(ValueError, match="At least one"):
            QuotaLimit(window=QuotaWindow.DAY)

    def test_negative_request_limit_raises(self) -> None:
        with pytest.raises(ValueError, match="request_limit must be >= 0"):
            QuotaLimit(window=QuotaWindow.DAY, request_limit=-1)

    def test_negative_token_limit_raises(self) -> None:
        with pytest.raises(ValueError, match="token_limit must be >= 0"):
            QuotaLimit(window=QuotaWindow.DAY, token_limit=-1)

    def test_negative_cost_limit_raises(self) -> None:
        with pytest.raises(ValueError, match="cost_limit must be >= 0"):
            QuotaLimit(window=QuotaWindow.DAY, cost_limit=Decimal("-1.0"))


class TestProviderQuotaConfig:
    """Tests for ProviderQuotaConfig dataclass."""

    def test_empty_limits(self) -> None:
        config = ProviderQuotaConfig(provider_id="openai")
        assert config.provider_id == "openai"
        assert config.limits == []

    def test_limit_for_existing_window(self) -> None:
        limit = QuotaLimit(window=QuotaWindow.DAY, request_limit=100)
        config = ProviderQuotaConfig(provider_id="openai", limits=[limit])
        assert config.limit_for(QuotaWindow.DAY) == limit

    def test_limit_for_missing_window(self) -> None:
        config = ProviderQuotaConfig(provider_id="openai")
        assert config.limit_for(QuotaWindow.DAY) is None

    def test_has_limit(self) -> None:
        limit = QuotaLimit(window=QuotaWindow.DAY, request_limit=100)
        config = ProviderQuotaConfig(provider_id="openai", limits=[limit])
        assert config.has_limit(QuotaWindow.DAY) is True
        assert config.has_limit(QuotaWindow.HOUR) is False


class TestProviderUsage:
    """Tests for ProviderUsage dataclass."""

    def test_default_values(self) -> None:
        usage = ProviderUsage(provider_id="openai")
        assert usage.provider_id == "openai"
        assert usage.request_count == 1
        assert usage.total_tokens == 0
        assert usage.estimated_cost == Decimal("0")
        assert usage.usage_known is False
        assert usage.cost_known is False

    def test_total_tokens_auto_calculated(self) -> None:
        usage = ProviderUsage(
            provider_id="openai",
            input_tokens=100,
            output_tokens=50,
        )
        assert usage.total_tokens == 150

    def test_usage_known_with_zero_tokens(self) -> None:
        usage = ProviderUsage(provider_id="openai", usage_known=True)
        assert usage.total_tokens == 0


class TestQuotaEligibility:
    """Tests for QuotaEligibility dataclass."""

    def test_eligible_result(self) -> None:
        result = QuotaEligibility(eligible=True, reason="eligible")
        assert result.eligible is True
        assert result.reason == "eligible"

    def test_ineligible_result(self) -> None:
        result = QuotaEligibility(eligible=False, reason="request_exhausted")
        assert result.eligible is False
        assert result.reason == "request_exhausted"


class TestGlobalBudgetState:
    """Tests for GlobalBudgetState dataclass."""

    def test_no_budget_configured(self) -> None:
        state = GlobalBudgetState()
        assert state.daily_budget == Decimal("0")
        assert state.monthly_budget == Decimal("0")
        assert state.daily_exhausted is False
        assert state.monthly_exhausted is False
        assert state.daily_remaining == Decimal("0")
        assert state.monthly_remaining == Decimal("0")

    def test_budget_within_limit(self) -> None:
        state = GlobalBudgetState(daily_budget=Decimal("10.0"), daily_spend=Decimal("5.0"))
        assert state.daily_exhausted is False
        assert state.daily_remaining == Decimal("5.0")

    def test_budget_exhausted(self) -> None:
        state = GlobalBudgetState(daily_budget=Decimal("10.0"), daily_spend=Decimal("10.0"))
        assert state.daily_exhausted is True
        assert state.daily_remaining == Decimal("0")

    def test_budget_over_limit(self) -> None:
        state = GlobalBudgetState(daily_budget=Decimal("10.0"), daily_spend=Decimal("15.0"))
        assert state.daily_exhausted is True
        assert state.daily_remaining == Decimal("0")

    def test_monthly_budget_exhausted(self) -> None:
        state = GlobalBudgetState(monthly_budget=Decimal("100.0"), monthly_spend=Decimal("100.0"))
        assert state.monthly_exhausted is True


__all__ = [
    "TestGlobalBudgetState",
    "TestProviderQuotaConfig",
    "TestProviderUsage",
    "TestQuotaEligibility",
    "TestQuotaLimit",
    "TestQuotaWindow",
]
