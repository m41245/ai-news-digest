"""
Unit tests for M79 quota-aware provider routing.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError
from redis.exceptions import RedisError

from ai_news_digest.application.ai.capability import Capability
from ai_news_digest.application.ai.capability_registry import CapabilityRegistry
from ai_news_digest.application.ai.config import ProviderConfig
from ai_news_digest.application.ai.decision_engine import DecisionEngine
from ai_news_digest.application.ai.errors import AITransientError
from ai_news_digest.application.ai.models import (
    AIRequest,
    AIResponse,
    AIUsage,
)
from ai_news_digest.application.ai.provider_manager import (
    ProviderManager,
    build_quota_config_from_provider_config,
)
from ai_news_digest.application.ai.provider_quota_registry import ProviderQuotaRegistry
from ai_news_digest.application.ai.provider_registry import ProviderRegistry
from ai_news_digest.application.ai.providers.base import AIProvider
from ai_news_digest.application.ai.quota import (
    GlobalBudgetState,
    ProviderQuotaConfig,
    QuotaEligibility,
    QuotaLimit,
    QuotaReservationResult,
    QuotaWindow,
    ReleaseResult,
    SettlementResult,
)
from ai_news_digest.core.config import Settings


@pytest.fixture
def provider_registry() -> ProviderRegistry:
    return ProviderRegistry()


@pytest.fixture
def capability_registry() -> CapabilityRegistry:
    registry = CapabilityRegistry()
    registry.register_capability(Capability(id="summarization", name="Summarization"))
    return registry


@pytest.fixture
def decision_engine(
    provider_registry: ProviderRegistry,
    capability_registry: CapabilityRegistry,
) -> DecisionEngine:
    return DecisionEngine(provider_registry, capability_registry)


def _make_quota_registry() -> MagicMock:
    registry = MagicMock(spec=ProviderQuotaRegistry)
    registry.get_global_budget = AsyncMock(return_value=GlobalBudgetState())
    registry.get_provider_quota = AsyncMock(
        return_value=ProviderQuotaConfig(
            provider_id="default",
            limits=[
                QuotaLimit(
                    window=QuotaWindow.DAY,
                    request_limit=1000,
                    token_limit=100000,
                    cost_limit=Decimal("10.0"),
                )
            ],
        )
    )
    registry.check_quota_eligibility = AsyncMock(
        return_value=QuotaEligibility(eligible=True, reason="eligible")
    )
    registry.record_usage = AsyncMock()
    registry.update_global_budget = AsyncMock()
    registry.reset_provider_quota = AsyncMock()
    registry.reserve_capacity = AsyncMock(
        return_value=QuotaReservationResult(
            reserved=True,
            reservation_id="test-reservation",
            reason="reserved",
        )
    )
    registry.settle_reservation = AsyncMock(
        return_value=SettlementResult(
            settled=True,
            reservation_id="test-reservation",
            reason="settled",
        )
    )
    registry.release_reservation = AsyncMock(
        return_value=ReleaseResult(
            released=True,
            reservation_id="test-reservation",
            reason="released",
        )
    )
    registry.get_reservation = AsyncMock(return_value=None)
    registry.list_outstanding_reservations = AsyncMock(return_value=[])
    registry.expire_reservations = AsyncMock(return_value=0)
    registry.reconcile_reservations = AsyncMock(return_value=0)
    return registry


def _make_provider(
    provider_id: str,
    name: str,
    capabilities: set[str],
    enabled: bool = True,
    priority: int = 50,
    available: bool = True,
    provider_config: ProviderConfig | None = None,
) -> MagicMock:
    provider = MagicMock(spec=AIProvider)
    provider.id = provider_id
    provider.name = name
    provider.enabled = enabled
    provider.priority = MagicMock(return_value=priority)
    provider.capabilities = capabilities
    provider.provider_name = name.lower().replace(" ", "_")
    provider.model_name = f"{provider_id}-model"
    provider.available = AsyncMock(return_value=available)
    provider.generate = AsyncMock()
    provider.provider_config = provider_config
    return provider


def _register_providers(
    provider_registry: ProviderRegistry,
    capability_registry: CapabilityRegistry,
    *providers: AIProvider,
) -> None:
    for provider in providers:
        provider_registry.register(provider)
        for capability in provider.capabilities:
            if not capability_registry.exists(capability):
                capability_registry.register_capability(
                    Capability(id=capability, name=capability.title())
                )
            capability_registry.register_provider(capability, provider.id)


@pytest.fixture(autouse=True)
def _ai_enabled() -> None:
    with patch(
        "ai_news_digest.application.ai.provider_manager.get_settings",
        return_value=Settings(ai_enabled=True),
    ):
        yield


class TestProviderManagerQuotaRouting:
    """Tests for M79 quota-aware routing in ProviderManager."""

    async def test_route_quota_exhausted_provider_excluded(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        quota_registry = _make_quota_registry()

        def _quota_config(provider_id: str) -> ProviderQuotaConfig | None:
            if provider_id == "openai":
                return ProviderQuotaConfig(
                    provider_id="openai",
                    limits=[
                        QuotaLimit(
                            window=QuotaWindow.DAY,
                            request_limit=0,
                            token_limit=0,
                            cost_limit=Decimal("0"),
                        )
                    ],
                )
            return None

        quota_registry.get_provider_quota = AsyncMock(side_effect=_quota_config)

        async def _check_quota(provider_id: str, window: QuotaWindow, **kwargs) -> QuotaEligibility:
            if provider_id == "openai":
                return QuotaEligibility(eligible=False, reason="request_quota_exhausted")
            return QuotaEligibility(eligible=True, reason="eligible")

        quota_registry.check_quota_eligibility = AsyncMock(side_effect=_check_quota)
        provider_manager = ProviderManager(
            provider_registry,
            capability_registry,
            decision_engine,
            quota_registry=quota_registry,
        )

        exhausted = _make_provider(
            "openai",
            "OpenAI",
            {"summarization"},
            priority=100,
            provider_config=ProviderConfig(provider_name="openai", api_key="test"),
        )
        available = _make_provider(
            "anthropic",
            "Anthropic",
            {"summarization"},
            priority=50,
            provider_config=ProviderConfig(provider_name="anthropic", api_key="test"),
        )
        _register_providers(provider_registry, capability_registry, exhausted, available)

        request = AIRequest(system_prompt="s", user_prompt="u")
        decision = await provider_manager.route(request, capability="summarization")

        assert decision.selected_provider_id == "anthropic"
        assert any(
            pid == "openai" and reason == "request_quota_exhausted"
            for pid, reason in decision.quota_exclusions
        )

    async def test_route_budget_exhausted_skips_all(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        quota_registry = _make_quota_registry()
        quota_registry.get_global_budget = AsyncMock(
            return_value=GlobalBudgetState(
                daily_budget=Decimal("10.0"), daily_spend=Decimal("10.0")
            )
        )
        provider_manager = ProviderManager(
            provider_registry,
            capability_registry,
            decision_engine,
            quota_registry=quota_registry,
        )

        provider = _make_provider(
            "openai",
            "OpenAI",
            {"summarization"},
            priority=100,
            provider_config=ProviderConfig(provider_name="openai", api_key="test"),
        )
        _register_providers(provider_registry, capability_registry, provider)

        request = AIRequest(system_prompt="s", user_prompt="u")
        decision = await provider_manager.route(request, capability="summarization")

        assert decision.selected_provider_id is None
        assert decision.budget_excluded is True

    async def test_route_quota_registry_none_allows_all(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        provider_manager = ProviderManager(
            provider_registry,
            capability_registry,
            decision_engine,
            quota_registry=None,
        )

        provider = _make_provider(
            "openai",
            "OpenAI",
            {"summarization"},
            priority=100,
            provider_config=ProviderConfig(provider_name="openai", api_key="test"),
        )
        _register_providers(provider_registry, capability_registry, provider)

        request = AIRequest(system_prompt="s", user_prompt="u")
        decision = await provider_manager.route(request, capability="summarization")

        assert decision.selected_provider_id == "openai"

    async def test_generate_records_usage_on_success(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        quota_registry = _make_quota_registry()
        provider_manager = ProviderManager(
            provider_registry,
            capability_registry,
            decision_engine,
            quota_registry=quota_registry,
        )

        provider = _make_provider(
            "openai",
            "OpenAI",
            {"summarization"},
            priority=100,
            provider_config=ProviderConfig(provider_name="openai", api_key="test"),
        )
        _register_providers(provider_registry, capability_registry, provider)
        provider.generate.return_value = AIResponse(
            provider="openai",
            model="gpt-4",
            content="summary",
            usage=AIUsage(prompt_tokens=10, completion_tokens=5),
            latency_ms=100.0,
        )

        request = AIRequest(system_prompt="s", user_prompt="u")
        await provider_manager.generate(request, capability="summarization")

        quota_registry.reserve_capacity.assert_awaited()
        quota_registry.settle_reservation.assert_awaited()

    async def test_generate_does_not_reset_quota_on_failure(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        quota_registry = _make_quota_registry()
        provider_manager = ProviderManager(
            provider_registry,
            capability_registry,
            decision_engine,
            quota_registry=quota_registry,
        )

        failing = _make_provider(
            "openai",
            "OpenAI",
            {"summarization"},
            priority=100,
            provider_config=ProviderConfig(provider_name="openai", api_key="test"),
        )
        succeeding = _make_provider(
            "anthropic",
            "Anthropic",
            {"summarization"},
            priority=50,
            provider_config=ProviderConfig(provider_name="anthropic", api_key="test"),
        )
        _register_providers(provider_registry, capability_registry, failing, succeeding)
        failing.generate.side_effect = AITransientError("failure")
        succeeding.generate.return_value = AIResponse(
            provider="anthropic",
            model="claude",
            content="summary",
            usage=AIUsage(),
            latency_ms=100.0,
        )

        request = AIRequest(system_prompt="s", user_prompt="u")
        response = await provider_manager.generate(request, capability="summarization")

        assert response.provider == "anthropic"
        # reset_provider_quota must NOT be called on provider failure --
        # deleting usage counters would allow subsequent requests to
        # silently bypass configured per-provider limits.
        quota_registry.reset_provider_quota.assert_not_called()

    async def test_route_quota_exclusion_in_decision(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        quota_registry = _make_quota_registry()
        quota_registry.check_quota_eligibility = AsyncMock(
            return_value=QuotaEligibility(eligible=False, reason="token_quota_exhausted")
        )
        provider_manager = ProviderManager(
            provider_registry,
            capability_registry,
            decision_engine,
            quota_registry=quota_registry,
        )

        exhausted = _make_provider(
            "openai",
            "OpenAI",
            {"summarization"},
            priority=100,
            provider_config=ProviderConfig(provider_name="openai", api_key="test"),
        )
        _register_providers(provider_registry, capability_registry, exhausted)

        request = AIRequest(system_prompt="s", user_prompt="u")
        decision = await provider_manager.route(request, capability="summarization")

        assert decision.selected_provider_id is None
        assert len(decision.quota_exclusions) == 1
        assert decision.quota_exclusions[0] == ("openai", "token_quota_exhausted")


@contextmanager
def _patched_settings(**kwargs: object) -> Iterator[Settings]:
    """Patch get_settings with a Settings instance that has the given values.

    pydantic-settings v2 ignores init-kwargs for fields that declare a
    ``validation_alias``.  We work around this by mapping each keyword to its
    alias (when one exists) so the value is accepted by the constructor.
    """
    init_kwargs: dict[str, object] = {"ai_enabled": True}
    for key, value in kwargs.items():
        field = Settings.model_fields.get(key)
        if field and field.validation_alias and isinstance(field.validation_alias, str):
            init_kwargs[field.validation_alias] = value
        else:
            init_kwargs[key] = value
    custom = Settings(**init_kwargs)
    with patch(
        "ai_news_digest.application.ai.provider_manager.get_settings",
        return_value=custom,
    ):
        yield custom


class TestProviderManagerSettingsEnforcement:
    """Tests that settings-defined limits reach runtime enforcement."""

    @staticmethod
    def _pricing_config(**overrides: object) -> ProviderConfig:
        base = {
            "provider_name": "openai",
            "api_key": "test",
            "input_cost_per_1k_tokens": 0.01,
            "output_cost_per_1k_tokens": 0.02,
        }
        return ProviderConfig(**{**base, **overrides})

    @staticmethod
    def _costly_request() -> AIRequest:
        # 4000 chars of input -> 1000 tokens; 0 output tokens;
        # estimated_cost = 1000/1000 * 0.01 = 0.01
        return AIRequest(system_prompt="a" * 4000, user_prompt="", max_tokens=0)

    async def test_per_request_cap_rejects_over_cap_without_registry(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        with _patched_settings(ai_max_estimated_request_cost=0.005):
            manager = ProviderManager(provider_registry, capability_registry, decision_engine)
            provider = _make_provider(
                "openai",
                "OpenAI",
                {"summarization"},
                provider_config=self._pricing_config(),
            )
            _register_providers(provider_registry, capability_registry, provider)

            request = self._costly_request()
            decision = await manager.route(request, capability="summarization")

        assert decision.selected_provider_id is None
        assert any(
            pid == "openai" and "budget_per_request_exceeded" in reason
            for pid, reason in decision.quota_exclusions
        )

    async def test_per_request_cap_boundary_at_cap_is_eligible(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        with _patched_settings(ai_max_estimated_request_cost=0.01):
            manager = ProviderManager(provider_registry, capability_registry, decision_engine)
            provider = _make_provider(
                "openai",
                "OpenAI",
                {"summarization"},
                provider_config=self._pricing_config(),
            )
            _register_providers(provider_registry, capability_registry, provider)

            decision = await manager.route(self._costly_request(), capability="summarization")

        assert decision.selected_provider_id == "openai"

    async def test_per_request_cap_below_cap_is_eligible(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        with _patched_settings(ai_max_estimated_request_cost=0.02):
            manager = ProviderManager(provider_registry, capability_registry, decision_engine)
            provider = _make_provider(
                "openai",
                "OpenAI",
                {"summarization"},
                provider_config=self._pricing_config(),
            )
            _register_providers(provider_registry, capability_registry, provider)

            decision = await manager.route(self._costly_request(), capability="summarization")

        assert decision.selected_provider_id == "openai"

    async def test_settings_request_limit_enforced(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        quota_registry = _make_quota_registry()
        quota_registry.get_provider_quota = AsyncMock(return_value=None)

        captured: list[QuotaLimit | None] = []

        async def _check(
            provider_id: str,
            window: QuotaWindow,
            estimated_tokens: int = 0,
            estimated_cost: float = 0.0,
            limit: QuotaLimit | None = None,
        ) -> QuotaEligibility:
            captured.append(limit)
            return QuotaEligibility(eligible=False, reason="request_quota_exhausted")

        quota_registry.check_quota_eligibility = AsyncMock(side_effect=_check)
        manager = ProviderManager(
            provider_registry,
            capability_registry,
            decision_engine,
            quota_registry=quota_registry,
        )
        config = ProviderConfig(provider_name="openai", api_key="test", request_limit=5)
        provider = _make_provider("openai", "OpenAI", {"summarization"}, provider_config=config)
        _register_providers(provider_registry, capability_registry, provider)

        decision = await manager.route(
            AIRequest(system_prompt="s", user_prompt="u"), capability="summarization"
        )

        assert decision.selected_provider_id is None
        assert captured
        assert captured[0] is not None
        assert captured[0].request_limit == 5
        assert captured[0].token_limit is None
        assert captured[0].cost_limit is None
        assert captured[0].window == QuotaWindow.DAY

    async def test_settings_token_limit_enforced(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        quota_registry = _make_quota_registry()
        quota_registry.get_provider_quota = AsyncMock(return_value=None)

        captured: list[QuotaLimit | None] = []

        async def _check(
            provider_id: str,
            window: QuotaWindow,
            estimated_tokens: int = 0,
            estimated_cost: float = 0.0,
            limit: QuotaLimit | None = None,
        ) -> QuotaEligibility:
            captured.append(limit)
            return QuotaEligibility(eligible=False, reason="token_quota_exhausted")

        quota_registry.check_quota_eligibility = AsyncMock(side_effect=_check)
        manager = ProviderManager(
            provider_registry,
            capability_registry,
            decision_engine,
            quota_registry=quota_registry,
        )
        config = ProviderConfig(provider_name="openai", api_key="test", token_limit=4000)
        provider = _make_provider("openai", "OpenAI", {"summarization"}, provider_config=config)
        _register_providers(provider_registry, capability_registry, provider)

        decision = await manager.route(
            AIRequest(system_prompt="s", user_prompt="u"), capability="summarization"
        )

        assert decision.selected_provider_id is None
        assert captured[0] is not None
        assert captured[0].token_limit == 4000
        assert captured[0].request_limit is None
        assert captured[0].cost_limit is None

    async def test_settings_cost_limit_enforced(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        quota_registry = _make_quota_registry()
        quota_registry.get_provider_quota = AsyncMock(return_value=None)

        captured: list[QuotaLimit | None] = []

        async def _check(
            provider_id: str,
            window: QuotaWindow,
            estimated_tokens: int = 0,
            estimated_cost: float = 0.0,
            limit: QuotaLimit | None = None,
        ) -> QuotaEligibility:
            captured.append(limit)
            return QuotaEligibility(eligible=False, reason="cost_quota_exhausted")

        quota_registry.check_quota_eligibility = AsyncMock(side_effect=_check)
        manager = ProviderManager(
            provider_registry,
            capability_registry,
            decision_engine,
            quota_registry=quota_registry,
        )
        config = ProviderConfig(provider_name="openai", api_key="test", cost_limit=5.0)
        provider = _make_provider("openai", "OpenAI", {"summarization"}, provider_config=config)
        _register_providers(provider_registry, capability_registry, provider)

        decision = await manager.route(
            AIRequest(system_prompt="s", user_prompt="u"), capability="summarization"
        )

        assert decision.selected_provider_id is None
        assert captured[0] is not None
        assert captured[0].cost_limit == Decimal("5.0")
        assert captured[0].request_limit is None
        assert captured[0].token_limit is None

    @pytest.mark.parametrize("provider_id", ["openai", "anthropic", "gemini", "grok"])
    async def test_settings_limits_apply_to_all_providers(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
        provider_id: str,
    ) -> None:
        quota_registry = _make_quota_registry()
        quota_registry.get_provider_quota = AsyncMock(return_value=None)

        captured: list[str] = []

        async def _check(
            pid: str,
            window: QuotaWindow,
            estimated_tokens: int = 0,
            estimated_cost: float = 0.0,
            limit: QuotaLimit | None = None,
        ) -> QuotaEligibility:
            captured.append(pid)
            if limit is not None and limit.request_limit == 3:
                return QuotaEligibility(eligible=False, reason="request_quota_exhausted")
            return QuotaEligibility(eligible=True, reason="eligible")

        quota_registry.check_quota_eligibility = AsyncMock(side_effect=_check)
        manager = ProviderManager(
            provider_registry,
            capability_registry,
            decision_engine,
            quota_registry=quota_registry,
        )
        config = ProviderConfig(provider_name=provider_id, api_key="test", request_limit=3)
        provider = _make_provider(
            provider_id, provider_id.title(), {"summarization"}, provider_config=config
        )
        _register_providers(provider_registry, capability_registry, provider)

        decision = await manager.route(
            AIRequest(system_prompt="s", user_prompt="u"), capability="summarization"
        )

        assert decision.selected_provider_id is None
        assert captured and captured[0] == provider_id
        assert decision.quota_exclusions[0] == (provider_id, "request_quota_exhausted")

    async def test_daily_budget_enforced_from_settings(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        quota_registry = _make_quota_registry()
        quota_registry.get_global_budget = AsyncMock(
            return_value=GlobalBudgetState(daily_spend=Decimal("10.0"))
        )
        manager = ProviderManager(
            provider_registry,
            capability_registry,
            decision_engine,
            quota_registry=quota_registry,
        )
        provider = _make_provider(
            "openai",
            "OpenAI",
            {"summarization"},
            provider_config=ProviderConfig(provider_name="openai", api_key="test"),
        )
        _register_providers(provider_registry, capability_registry, provider)

        with _patched_settings(ai_daily_cost_budget=5.0):
            decision = await manager.route(
                AIRequest(system_prompt="s", user_prompt="u"), capability="summarization"
            )

        assert decision.selected_provider_id is None
        assert decision.budget_excluded is True

    async def test_monthly_budget_enforced_from_settings(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        quota_registry = _make_quota_registry()
        quota_registry.get_global_budget = AsyncMock(
            return_value=GlobalBudgetState(monthly_spend=Decimal("10.0"))
        )
        manager = ProviderManager(
            provider_registry,
            capability_registry,
            decision_engine,
            quota_registry=quota_registry,
        )
        provider = _make_provider(
            "openai",
            "OpenAI",
            {"summarization"},
            provider_config=ProviderConfig(provider_name="openai", api_key="test"),
        )
        _register_providers(provider_registry, capability_registry, provider)

        with _patched_settings(ai_monthly_cost_budget=5.0):
            decision = await manager.route(
                AIRequest(system_prompt="s", user_prompt="u"), capability="summarization"
            )

        assert decision.selected_provider_id is None
        assert decision.budget_excluded is True

    async def test_budget_under_limit_is_eligible(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        quota_registry = _make_quota_registry()
        quota_registry.get_global_budget = AsyncMock(
            return_value=GlobalBudgetState(daily_spend=Decimal("3.0"))
        )
        manager = ProviderManager(
            provider_registry,
            capability_registry,
            decision_engine,
            quota_registry=quota_registry,
        )
        provider = _make_provider(
            "openai",
            "OpenAI",
            {"summarization"},
            provider_config=ProviderConfig(provider_name="openai", api_key="test"),
        )
        _register_providers(provider_registry, capability_registry, provider)

        with _patched_settings(ai_daily_cost_budget=5.0):
            decision = await manager.route(
                AIRequest(system_prompt="s", user_prompt="u"), capability="summarization"
            )

        assert decision.selected_provider_id == "openai"

    async def test_admin_redis_budget_overrides_settings(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        quota_registry = _make_quota_registry()
        quota_registry.get_global_budget = AsyncMock(
            return_value=GlobalBudgetState(
                daily_budget=Decimal("50.0"), daily_spend=Decimal("10.0")
            )
        )
        manager = ProviderManager(
            provider_registry,
            capability_registry,
            decision_engine,
            quota_registry=quota_registry,
        )
        provider = _make_provider(
            "openai",
            "OpenAI",
            {"summarization"},
            provider_config=ProviderConfig(provider_name="openai", api_key="test"),
        )
        _register_providers(provider_registry, capability_registry, provider)

        with _patched_settings(ai_daily_cost_budget=5.0):
            decision = await manager.route(
                AIRequest(system_prompt="s", user_prompt="u"), capability="summarization"
            )

        assert decision.selected_provider_id == "openai"

    async def test_admin_redis_quota_overrides_settings_limits(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        quota_registry = _make_quota_registry()
        admin_config = ProviderQuotaConfig(
            provider_id="openai",
            limits=[
                QuotaLimit(
                    window=QuotaWindow.DAY,
                    request_limit=1000,
                    token_limit=100000,
                    cost_limit=Decimal("10.0"),
                )
            ],
        )
        quota_registry.get_provider_quota = AsyncMock(return_value=admin_config)

        captured: list[QuotaLimit | None] = []

        async def _check(
            provider_id: str,
            window: QuotaWindow,
            estimated_tokens: int = 0,
            estimated_cost: float = 0.0,
            limit: QuotaLimit | None = None,
        ) -> QuotaEligibility:
            captured.append(limit)
            return QuotaEligibility(eligible=True, reason="eligible")

        quota_registry.check_quota_eligibility = AsyncMock(side_effect=_check)
        manager = ProviderManager(
            provider_registry,
            capability_registry,
            decision_engine,
            quota_registry=quota_registry,
        )
        # Settings-derived limit (3) must NOT be used; admin (1000) takes over.
        settings_config = ProviderConfig(provider_name="openai", api_key="test", request_limit=3)
        provider = _make_provider(
            "openai", "OpenAI", {"summarization"}, provider_config=settings_config
        )
        _register_providers(provider_registry, capability_registry, provider)

        decision = await manager.route(
            AIRequest(system_prompt="s", user_prompt="u"), capability="summarization"
        )

        assert decision.selected_provider_id == "openai"
        assert captured[0] is not None
        assert captured[0].request_limit == 1000

    async def test_missing_quota_state_is_eligible(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        quota_registry = _make_quota_registry()
        quota_registry.get_provider_quota = AsyncMock(return_value=None)

        async def _check(
            provider_id: str,
            window: QuotaWindow,
            estimated_tokens: int = 0,
            estimated_cost: float = 0.0,
            limit: QuotaLimit | None = None,
        ) -> QuotaEligibility:
            # No limits configured on the provider config -> limit should be None.
            assert limit is None
            return QuotaEligibility(eligible=True, reason="eligible")

        quota_registry.check_quota_eligibility = AsyncMock(side_effect=_check)
        manager = ProviderManager(
            provider_registry,
            capability_registry,
            decision_engine,
            quota_registry=quota_registry,
        )
        provider = _make_provider(
            "openai",
            "OpenAI",
            {"summarization"},
            provider_config=ProviderConfig(provider_name="openai", api_key="test"),
        )
        _register_providers(provider_registry, capability_registry, provider)

        decision = await manager.route(
            AIRequest(system_prompt="s", user_prompt="u"), capability="summarization"
        )

        assert decision.selected_provider_id == "openai"
        assert quota_registry.check_quota_eligibility.call_count == 0

    async def test_redis_error_get_provider_quota_falls_back_to_settings(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        quota_registry = _make_quota_registry()

        async def _raise(*args: object, **kwargs: object) -> ProviderQuotaConfig:
            raise RedisError("connection lost")

        quota_registry.get_provider_quota = AsyncMock(side_effect=_raise)

        captured: list[QuotaLimit | None] = []

        async def _check(
            provider_id: str,
            window: QuotaWindow,
            estimated_tokens: int = 0,
            estimated_cost: float = 0.0,
            limit: QuotaLimit | None = None,
        ) -> QuotaEligibility:
            captured.append(limit)
            return QuotaEligibility(eligible=True, reason="eligible")

        quota_registry.check_quota_eligibility = AsyncMock(side_effect=_check)
        manager = ProviderManager(
            provider_registry,
            capability_registry,
            decision_engine,
            quota_registry=quota_registry,
        )
        config = ProviderConfig(provider_name="openai", api_key="test", request_limit=7)
        provider = _make_provider("openai", "OpenAI", {"summarization"}, provider_config=config)
        _register_providers(provider_registry, capability_registry, provider)

        decision = await manager.route(
            AIRequest(system_prompt="s", user_prompt="u"), capability="summarization"
        )

        assert decision.selected_provider_id == "openai"
        assert captured[0] is not None
        assert captured[0].request_limit == 7

    async def test_per_request_cap_enforced_when_registry_fails(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        from ai_news_digest.infrastructure.quota.redis_provider_quota_registry import (
            RedisProviderQuotaRegistry,
        )

        registry = RedisProviderQuotaRegistry(redis_url="redis://localhost:6379/0")
        mock_client = AsyncMock()
        mock_client.hgetall.return_value = {}
        mock_client.eval = AsyncMock(side_effect=RedisError("connection lost"))
        registry._client = mock_client

        manager = ProviderManager(
            provider_registry,
            capability_registry,
            decision_engine,
            quota_registry=registry,
        )
        provider = _make_provider(
            "openai",
            "OpenAI",
            {"summarization"},
            provider_config=self._pricing_config(request_limit=0),
        )
        _register_providers(provider_registry, capability_registry, provider)

        with _patched_settings(ai_max_estimated_request_cost=0.005):
            decision = await manager.route(self._costly_request(), capability="summarization")

        assert decision.selected_provider_id is None
        assert any(
            "budget_per_request_exceeded" in reason for _, reason in decision.quota_exclusions
        )

    async def test_redis_error_fail_closed_for_usage_check(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        from ai_news_digest.infrastructure.quota.redis_provider_quota_registry import (
            RedisProviderQuotaRegistry,
        )

        registry = RedisProviderQuotaRegistry(redis_url="redis://localhost:6379/0")
        mock_client = AsyncMock()
        mock_client.hgetall.return_value = {}
        mock_client.eval = AsyncMock(side_effect=RedisError("connection lost"))
        registry._client = mock_client

        manager = ProviderManager(
            provider_registry,
            capability_registry,
            decision_engine,
            quota_registry=registry,
        )
        config = ProviderConfig(provider_name="openai", api_key="test", request_limit=5)
        provider = _make_provider("openai", "OpenAI", {"summarization"}, provider_config=config)
        _register_providers(provider_registry, capability_registry, provider)

        decision = await manager.route(
            AIRequest(system_prompt="s", user_prompt="u"), capability="summarization"
        )

        # When Redis is unavailable and a per-provider limit is configured
        # (from settings), the request must fail closed because the limit
        # cannot be verified against live usage.
        assert decision.selected_provider_id is None
        assert any(
            pid == "openai" and reason == "budget_quota_check_failed"
            for pid, reason in decision.quota_exclusions
        )


class TestBuildQuotaConfigFromProviderConfig:
    """Tests for the settings-to-quota-config conversion helper."""

    def test_no_limits_returns_none(self) -> None:
        config = ProviderConfig(provider_name="openai", api_key="test")
        assert build_quota_config_from_provider_config("openai", config) is None

    def test_zero_limits_are_unlimited(self) -> None:
        config = ProviderConfig(
            provider_name="openai",
            api_key="test",
            request_limit=0,
            token_limit=0,
            cost_limit=0.0,
        )
        assert build_quota_config_from_provider_config("openai", config) is None

    def test_request_limit_becomes_quota_limit(self) -> None:
        config = ProviderConfig(provider_name="openai", api_key="test", request_limit=100)
        result = build_quota_config_from_provider_config("openai", config)
        assert result is not None
        assert result.provider_id == "openai"
        assert len(result.limits) == 1
        limit = result.limits[0]
        assert limit.window == QuotaWindow.DAY
        assert limit.request_limit == 100
        assert limit.token_limit is None
        assert limit.cost_limit is None

    def test_all_limits_become_quota_limit(self) -> None:
        config = ProviderConfig(
            provider_name="anthropic",
            api_key="test",
            request_limit=50,
            token_limit=100000,
            cost_limit=25.0,
        )
        result = build_quota_config_from_provider_config("anthropic", config)
        assert result is not None
        limit = result.limits[0]
        assert limit.request_limit == 50
        assert limit.token_limit == 100000
        assert limit.cost_limit == Decimal("25.0")

    def test_negative_request_limit_rejected(self) -> None:
        with pytest.raises(ValueError, match="request_limit"):
            QuotaLimit(window=QuotaWindow.DAY, request_limit=-1)

    def test_negative_cost_limit_rejected(self) -> None:
        with pytest.raises(ValueError, match="cost_limit"):
            QuotaLimit(window=QuotaWindow.DAY, cost_limit=Decimal("-1"))

    def test_negative_settings_rejected_by_validation(self) -> None:
        env = {"AI_MONTHLY_COST_BUDGET": "-1.0"}
        with patch.dict(os.environ, env), pytest.raises(ValidationError):
            Settings(
                database_url="postgresql://test",
                redis_url="redis://test",
                celery_broker_url="redis://broker",
                celery_result_backend="redis://backend",
                jwt_secret_key="a" * 64,
            )


class TestAiDisabledBehavior:
    """AI-disabled routing must be unchanged."""

    async def test_ai_disabled_returns_no_provider(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        with patch(
            "ai_news_digest.application.ai.provider_manager.get_settings",
            return_value=Settings(ai_enabled=False),
        ):
            manager = ProviderManager(provider_registry, capability_registry, decision_engine)
            provider = _make_provider(
                "openai",
                "OpenAI",
                {"summarization"},
                provider_config=ProviderConfig(provider_name="openai", api_key="test"),
            )
            _register_providers(provider_registry, capability_registry, provider)

            decision = await manager.route(
                AIRequest(system_prompt="s", user_prompt="u"), capability="summarization"
            )

        assert decision.selected_provider_id is None
        assert decision.reason == "AI is disabled"


class TestRedisFailureSafetyGuards:
    """Tests for safety-critical behavior when the quota Redis is unavailable.

    Audit A findings:
    - Per-request cost cap is settings-based and enforced independently of Redis.
    - Per-provider limits rely on Redis for usage accounting; when Redis is
      down the limit cannot be verified, so requests must fail closed.
    - Global budget spend accounting relies on Redis; when Redis is down and
      a budget is configured, requests must fail closed.
    """

    async def test_quota_check_raises_exception_fails_closed(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        """When check_quota_eligibility raises, the provider is excluded."""
        quota_registry = _make_quota_registry()
        quota_registry.get_provider_quota = AsyncMock(return_value=None)
        quota_registry.check_quota_eligibility = AsyncMock(
            side_effect=RuntimeError("connection lost")
        )
        manager = ProviderManager(
            provider_registry,
            capability_registry,
            decision_engine,
            quota_registry=quota_registry,
        )
        config = ProviderConfig(provider_name="openai", api_key="test", request_limit=5)
        provider = _make_provider("openai", "OpenAI", {"summarization"}, provider_config=config)
        _register_providers(provider_registry, capability_registry, provider)

        decision = await manager.route(
            AIRequest(system_prompt="s", user_prompt="u"), capability="summarization"
        )

        assert decision.selected_provider_id is None
        assert any(
            pid == "openai" and reason == "budget_quota_check_failed"
            for pid, reason in decision.quota_exclusions
        )

    async def test_quota_check_redis_error_fails_closed(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        """When check_quota_eligibility returns quota_check_failed reason,
        the provider is excluded (fail-closed)."""
        quota_registry = _make_quota_registry()
        quota_registry.get_provider_quota = AsyncMock(return_value=None)
        quota_registry.check_quota_eligibility = AsyncMock(
            return_value=QuotaEligibility(eligible=True, reason="quota_check_failed")
        )
        manager = ProviderManager(
            provider_registry,
            capability_registry,
            decision_engine,
            quota_registry=quota_registry,
        )
        config = ProviderConfig(provider_name="openai", api_key="test", request_limit=5)
        provider = _make_provider("openai", "OpenAI", {"summarization"}, provider_config=config)
        _register_providers(provider_registry, capability_registry, provider)

        decision = await manager.route(
            AIRequest(system_prompt="s", user_prompt="u"), capability="summarization"
        )

        assert decision.selected_provider_id is None
        assert any(
            pid == "openai" and reason == "budget_quota_check_failed"
            for pid, reason in decision.quota_exclusions
        )

    async def test_quota_check_unknown_result_fails_closed(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        """When check_quota_eligibility returns unknown_check_result, fail closed."""
        quota_registry = _make_quota_registry()
        quota_registry.get_provider_quota = AsyncMock(return_value=None)
        quota_registry.check_quota_eligibility = AsyncMock(
            return_value=QuotaEligibility(eligible=True, reason="unknown_check_result")
        )
        manager = ProviderManager(
            provider_registry,
            capability_registry,
            decision_engine,
            quota_registry=quota_registry,
        )
        config = ProviderConfig(provider_name="openai", api_key="test", request_limit=5)
        provider = _make_provider("openai", "OpenAI", {"summarization"}, provider_config=config)
        _register_providers(provider_registry, capability_registry, provider)

        decision = await manager.route(
            AIRequest(system_prompt="s", user_prompt="u"), capability="summarization"
        )

        assert decision.selected_provider_id is None

    async def test_global_budget_read_failure_fails_closed_with_budget(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        """When get_global_budget fails and a budget is configured in settings,
        routing must fail closed."""
        quota_registry = _make_quota_registry()
        quota_registry.get_global_budget = AsyncMock(side_effect=RuntimeError("redis down"))
        manager = ProviderManager(
            provider_registry,
            capability_registry,
            decision_engine,
            quota_registry=quota_registry,
        )
        provider = _make_provider(
            "openai",
            "OpenAI",
            {"summarization"},
            provider_config=ProviderConfig(provider_name="openai", api_key="test"),
        )
        _register_providers(provider_registry, capability_registry, provider)

        with _patched_settings(ai_daily_cost_budget=5.0):
            decision = await manager.route(
                AIRequest(system_prompt="s", user_prompt="u"), capability="summarization"
            )

        assert decision.selected_provider_id is None
        assert decision.reason == "Global AI budget unavailable (quota store failure)"
        assert decision.budget_excluded is True

    async def test_global_budget_read_failure_allows_when_no_budget(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        """When get_global_budget fails and no budget is configured, requests may proceed."""
        quota_registry = _make_quota_registry()
        quota_registry.get_global_budget = AsyncMock(side_effect=RuntimeError("redis down"))
        manager = ProviderManager(
            provider_registry,
            capability_registry,
            decision_engine,
            quota_registry=quota_registry,
        )
        provider = _make_provider(
            "openai",
            "OpenAI",
            {"summarization"},
            provider_config=ProviderConfig(provider_name="openai", api_key="test"),
        )
        _register_providers(provider_registry, capability_registry, provider)

        with _patched_settings():
            decision = await manager.route(
                AIRequest(system_prompt="s", user_prompt="u"), capability="summarization"
            )

        assert decision.selected_provider_id == "openai"

    async def test_spend_accounting_failure_does_not_block_request(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        """When settlement fails, the request still succeeds.

        Settlement failure is logged; the reservation stays pending (capacity
        is retained) rather than being freed back to the available pool.
        """
        quota_registry = _make_quota_registry()
        quota_registry.settle_reservation = AsyncMock(side_effect=RuntimeError("write failed"))
        provider_manager = ProviderManager(
            provider_registry,
            capability_registry,
            decision_engine,
            quota_registry=quota_registry,
        )
        provider = _make_provider(
            "openai",
            "OpenAI",
            {"summarization"},
            priority=100,
            provider_config=ProviderConfig(
                provider_name="openai",
                api_key="test",
                input_cost_per_1k_tokens=0.01,
                output_cost_per_1k_tokens=0.02,
            ),
        )
        _register_providers(provider_registry, capability_registry, provider)
        provider.generate.return_value = AIResponse(
            provider="openai",
            model="gpt-4",
            content="ok",
            usage=AIUsage(prompt_tokens=10, completion_tokens=5),
            latency_ms=100.0,
        )

        request = AIRequest(system_prompt="s", user_prompt="u")
        response = await provider_manager.generate(request, capability="summarization")

        assert response.content == "ok"


class TestBudgetBoundarySemantics:
    """Tests for daily and monthly budget boundary behaviour (Audit B)."""

    async def test_daily_budget_exactly_exhausted_blocks(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        quota_registry = _make_quota_registry()
        quota_registry.get_global_budget = AsyncMock(
            return_value=GlobalBudgetState(
                daily_budget=Decimal("10.0"),
                daily_spend=Decimal("10.0"),
            )
        )
        manager = ProviderManager(
            provider_registry,
            capability_registry,
            decision_engine,
            quota_registry=quota_registry,
        )
        provider = _make_provider(
            "openai",
            "OpenAI",
            {"summarization"},
            provider_config=ProviderConfig(provider_name="openai", api_key="test"),
        )
        _register_providers(provider_registry, capability_registry, provider)

        with _patched_settings(ai_daily_cost_budget=10.0):
            decision = await manager.route(
                AIRequest(system_prompt="s", user_prompt="u"), capability="summarization"
            )

        assert decision.selected_provider_id is None
        assert decision.reason == "Global AI budget exhausted"
        assert decision.budget_excluded is True

    async def test_daily_budget_just_below_eligible(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        quota_registry = _make_quota_registry()
        quota_registry.get_global_budget = AsyncMock(
            return_value=GlobalBudgetState(
                daily_budget=Decimal("10.0"),
                daily_spend=Decimal("9.99"),
            )
        )
        manager = ProviderManager(
            provider_registry,
            capability_registry,
            decision_engine,
            quota_registry=quota_registry,
        )
        provider = _make_provider(
            "openai",
            "OpenAI",
            {"summarization"},
            provider_config=ProviderConfig(provider_name="openai", api_key="test"),
        )
        _register_providers(provider_registry, capability_registry, provider)

        with _patched_settings(ai_daily_cost_budget=10.0):
            decision = await manager.route(
                AIRequest(system_prompt="s", user_prompt="u"), capability="summarization"
            )

        assert decision.selected_provider_id == "openai"

    async def test_daily_budget_above_exhausted_blocks(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        quota_registry = _make_quota_registry()
        quota_registry.get_global_budget = AsyncMock(
            return_value=GlobalBudgetState(
                daily_budget=Decimal("10.0"),
                daily_spend=Decimal("15.0"),
            )
        )
        manager = ProviderManager(
            provider_registry,
            capability_registry,
            decision_engine,
            quota_registry=quota_registry,
        )
        provider = _make_provider(
            "openai",
            "OpenAI",
            {"summarization"},
            provider_config=ProviderConfig(provider_name="openai", api_key="test"),
        )
        _register_providers(provider_registry, capability_registry, provider)

        with _patched_settings(ai_daily_cost_budget=10.0):
            decision = await manager.route(
                AIRequest(system_prompt="s", user_prompt="u"), capability="summarization"
            )

        assert decision.selected_provider_id is None
        assert decision.budget_excluded is True

    async def test_monthly_budget_exactly_exhausted_blocks(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        quota_registry = _make_quota_registry()
        quota_registry.get_global_budget = AsyncMock(
            return_value=GlobalBudgetState(
                monthly_budget=Decimal("100.0"),
                monthly_spend=Decimal("100.0"),
            )
        )
        manager = ProviderManager(
            provider_registry,
            capability_registry,
            decision_engine,
            quota_registry=quota_registry,
        )
        provider = _make_provider(
            "openai",
            "OpenAI",
            {"summarization"},
            provider_config=ProviderConfig(provider_name="openai", api_key="test"),
        )
        _register_providers(provider_registry, capability_registry, provider)

        with _patched_settings(ai_monthly_cost_budget=100.0):
            decision = await manager.route(
                AIRequest(system_prompt="s", user_prompt="u"), capability="summarization"
            )

        assert decision.selected_provider_id is None
        assert decision.reason == "Global AI budget exhausted"
        assert decision.budget_excluded is True

    async def test_monthly_budget_just_below_eligible(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        quota_registry = _make_quota_registry()
        quota_registry.get_global_budget = AsyncMock(
            return_value=GlobalBudgetState(
                monthly_budget=Decimal("100.0"),
                monthly_spend=Decimal("99.99"),
            )
        )
        manager = ProviderManager(
            provider_registry,
            capability_registry,
            decision_engine,
            quota_registry=quota_registry,
        )
        provider = _make_provider(
            "openai",
            "OpenAI",
            {"summarization"},
            provider_config=ProviderConfig(provider_name="openai", api_key="test"),
        )
        _register_providers(provider_registry, capability_registry, provider)

        with _patched_settings(ai_monthly_cost_budget=100.0):
            decision = await manager.route(
                AIRequest(system_prompt="s", user_prompt="u"), capability="summarization"
            )

        assert decision.selected_provider_id == "openai"

    async def test_zero_budget_means_unlimited(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        """Zero budget setting means unlimited -- no budget enforcement."""
        quota_registry = _make_quota_registry()
        quota_registry.get_global_budget = AsyncMock(
            return_value=GlobalBudgetState(daily_spend=Decimal("99999.0"))
        )
        manager = ProviderManager(
            provider_registry,
            capability_registry,
            decision_engine,
            quota_registry=quota_registry,
        )
        provider = _make_provider(
            "openai",
            "OpenAI",
            {"summarization"},
            provider_config=ProviderConfig(provider_name="openai", api_key="test"),
        )
        _register_providers(provider_registry, capability_registry, provider)

        with _patched_settings():
            decision = await manager.route(
                AIRequest(system_prompt="s", user_prompt="u"), capability="summarization"
            )

        assert decision.selected_provider_id == "openai"

    async def test_redis_budget_zero_falls_back_to_settings(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        """Redis budget=0 (unset) falls back to settings budget."""
        quota_registry = _make_quota_registry()
        quota_registry.get_global_budget = AsyncMock(
            return_value=GlobalBudgetState(
                daily_budget=Decimal("0"),  # Redis budget unset
                daily_spend=Decimal("6.0"),
            )
        )
        manager = ProviderManager(
            provider_registry,
            capability_registry,
            decision_engine,
            quota_registry=quota_registry,
        )
        provider = _make_provider(
            "openai",
            "OpenAI",
            {"summarization"},
            provider_config=ProviderConfig(provider_name="openai", api_key="test"),
        )
        _register_providers(provider_registry, capability_registry, provider)

        with _patched_settings(ai_daily_cost_budget=5.0):
            decision = await manager.route(
                AIRequest(system_prompt="s", user_prompt="u"), capability="summarization"
            )

        # Settings budget=5.0, Redis spend=6.0 > 5.0 -> exhausted
        assert decision.selected_provider_id is None
        assert decision.budget_excluded is True

    async def test_redis_budget_nonzero_overrides_settings(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        """A non-zero Redis budget takes precedence over settings budget."""
        quota_registry = _make_quota_registry()
        quota_registry.get_global_budget = AsyncMock(
            return_value=GlobalBudgetState(
                daily_budget=Decimal("20.0"),  # Redis override
                daily_spend=Decimal("5.0"),
            )
        )
        manager = ProviderManager(
            provider_registry,
            capability_registry,
            decision_engine,
            quota_registry=quota_registry,
        )
        provider = _make_provider(
            "openai",
            "OpenAI",
            {"summarization"},
            provider_config=ProviderConfig(provider_name="openai", api_key="test"),
        )
        _register_providers(provider_registry, capability_registry, provider)

        # Settings says budget=5.0 but Redis says 20.0 -- Redis wins.
        with _patched_settings(ai_daily_cost_budget=5.0):
            decision = await manager.route(
                AIRequest(system_prompt="s", user_prompt="u"), capability="summarization"
            )

        # spend=5.0, Redis budget=20.0 -> NOT exhausted
        assert decision.selected_provider_id == "openai"


class TestPerRequestCostCapUnknownPricing:
    """Tests for per-request cost cap when pricing is unknown (Audit E)."""

    async def test_unknown_pricing_with_cap_fails_closed(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        """When a per-request cap is configured but pricing is unknown,
        the request must fail closed rather than bypass the cap."""
        manager = ProviderManager(provider_registry, capability_registry, decision_engine)
        # ProviderConfig without pricing (input_cost/output_cost are 0)
        config = ProviderConfig(provider_name="openai", api_key="test")
        provider = _make_provider("openai", "OpenAI", {"summarization"}, provider_config=config)
        _register_providers(provider_registry, capability_registry, provider)

        with _patched_settings(ai_max_estimated_request_cost=0.05):
            decision = await manager.route(
                AIRequest(system_prompt="s", user_prompt="u"), capability="summarization"
            )

        assert decision.selected_provider_id is None
        assert any(
            pid == "openai" and reason == "budget_per_request_cost_unknown"
            for pid, reason in decision.quota_exclusions
        )

    async def test_unknown_pricing_without_cap_allows(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        """When no per-request cap is configured and pricing is unknown,
        the request may proceed (no hard cap to enforce)."""
        manager = ProviderManager(provider_registry, capability_registry, decision_engine)
        config = ProviderConfig(provider_name="openai", api_key="test")
        provider = _make_provider("openai", "OpenAI", {"summarization"}, provider_config=config)
        _register_providers(provider_registry, capability_registry, provider)

        with _patched_settings():
            decision = await manager.route(
                AIRequest(system_prompt="s", user_prompt="u"), capability="summarization"
            )

        assert decision.selected_provider_id == "openai"

    async def test_known_pricing_at_exact_cap_is_eligible(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        """Estimated cost exactly at the cap is eligible (<= comparison)."""
        manager = ProviderManager(provider_registry, capability_registry, decision_engine)
        config = ProviderConfig(
            provider_name="openai",
            api_key="test",
            input_cost_per_1k_tokens=0.01,
            output_cost_per_1k_tokens=0.02,
        )
        provider = _make_provider("openai", "OpenAI", {"summarization"}, provider_config=config)
        _register_providers(provider_registry, capability_registry, provider)

        # 4000 chars -> 1000 tokens; cost = 1000/1000 * 0.01 = 0.01
        request = AIRequest(system_prompt="a" * 4000, user_prompt="", max_tokens=0)
        with _patched_settings(ai_max_estimated_request_cost=0.01):
            decision = await manager.route(request, capability="summarization")

        assert decision.selected_provider_id == "openai"

    async def test_known_pricing_above_cap_exceeds(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        """Estimated cost above the cap is rejected."""
        manager = ProviderManager(provider_registry, capability_registry, decision_engine)
        config = ProviderConfig(
            provider_name="openai",
            api_key="test",
            input_cost_per_1k_tokens=0.01,
            output_cost_per_1k_tokens=0.02,
        )
        provider = _make_provider("openai", "OpenAI", {"summarization"}, provider_config=config)
        _register_providers(provider_registry, capability_registry, provider)

        # cost = 0.01; cap = 0.005
        request = AIRequest(system_prompt="a" * 4000, user_prompt="", max_tokens=0)
        with _patched_settings(ai_max_estimated_request_cost=0.005):
            decision = await manager.route(request, capability="summarization")

        assert decision.selected_provider_id is None
        assert any(
            pid == "openai" and "budget_per_request" in reason
            for pid, reason in decision.quota_exclusions
        )


class TestProviderLimitsReachQuotaCheck:
    """Verify settings-defined provider limits are forwarded to the quota check."""

    @pytest.mark.parametrize(
        "provider_id,name",
        [
            ("openai", "OpenAI"),
            ("anthropic", "Anthropic"),
            ("gemini", "Gemini"),
            ("grok", "xAI"),
        ],
    )
    async def test_settings_limits_passed_for_all_providers(
        self,
        provider_id,
        name,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        quota_registry = _make_quota_registry()
        quota_registry.get_provider_quota = AsyncMock(return_value=None)

        captured: list[QuotaLimit | None] = []

        async def _check(
            pid: str,
            window: QuotaWindow,
            **kwargs: object,
        ) -> QuotaEligibility:
            captured.append(kwargs.get("limit"))
            return QuotaEligibility(eligible=True, reason="eligible")

        quota_registry.check_quota_eligibility = AsyncMock(side_effect=_check)
        manager = ProviderManager(
            provider_registry,
            capability_registry,
            decision_engine,
            quota_registry=quota_registry,
        )

        limits_map = {
            "openai": (100, 100000, 5.0),
            "anthropic": (50, 200000, 10.0),
            "gemini": (200, 50000, 3.0),
            "grok": (75, 150000, 7.0),
        }
        req_limit, tok_limit, cost_limit = limits_map[provider_id]
        config = ProviderConfig(
            provider_name=provider_id,
            api_key="test",
            request_limit=req_limit,
            token_limit=tok_limit,
            cost_limit=cost_limit,
        )
        provider = _make_provider(provider_id, name, {"summarization"}, provider_config=config)
        _register_providers(provider_registry, capability_registry, provider)

        await manager.route(
            AIRequest(system_prompt="s", user_prompt="u"), capability="summarization"
        )

        assert captured
        limit = captured[0]
        assert limit is not None
        assert limit.request_limit == req_limit
        assert limit.token_limit == tok_limit
        assert limit.cost_limit == Decimal(str(cost_limit))


class TestConcurrentQuotaChecks:
    """Tests for concurrent quota checking and reservation.

    The reservation flow separates the eligibility *check* (in ``route()``,
    via ``check_quota_eligibility``) from the atomic *reserve* (in
    ``generate()``, via ``reserve_capacity``).  This preserves the read
    pre-filter while making the actual capacity commitment atomic in the
    Redis Lua-script layer.
    """

    async def test_check_and_reserve_are_sequential_per_request(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        """Verify that check_quota_eligibility (in route) and reserve_capacity
        (in generate) are distinct calls, with the check preceding the reserve
        for each individual request."""
        quota_registry = _make_quota_registry()
        manager = ProviderManager(
            provider_registry,
            capability_registry,
            decision_engine,
            quota_registry=quota_registry,
        )
        provider = _make_provider(
            "openai",
            "OpenAI",
            {"summarization"},
            priority=100,
            provider_config=ProviderConfig(
                provider_name="openai",
                api_key="test",
                input_cost_per_1k_tokens=0.01,
                output_cost_per_1k_tokens=0.02,
            ),
        )
        _register_providers(provider_registry, capability_registry, provider)
        provider.generate.return_value = AIResponse(
            provider="openai",
            model="gpt-4",
            content="ok",
            usage=AIUsage(prompt_tokens=10, completion_tokens=5),
            latency_ms=100.0,
        )

        request = AIRequest(system_prompt="s", user_prompt="u")
        await manager.generate(request, capability="summarization")

        check_count = quota_registry.check_quota_eligibility.await_count
        reserve_count = quota_registry.reserve_capacity.await_count
        assert check_count == 1
        assert reserve_count == 1

    async def test_concurrent_requests_compete_via_reservation(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        """Concurrent requests each go through route() (check) and generate()
        (reserve), with the reservation being the atomic gatekeeper in the
        Redis Lua-script layer."""
        import asyncio

        quota_registry = _make_quota_registry()

        check_calls: list[int] = []
        reserve_calls: list[int] = []
        settle_calls: list[int] = []

        async def _check(*args: object, **kwargs: object) -> QuotaEligibility:
            check_calls.append(len(reserve_calls))
            return QuotaEligibility(eligible=True, reason="eligible")

        async def _reserve(*args: object, **kwargs: object) -> QuotaReservationResult:
            reserve_calls.append(len(settle_calls))
            return QuotaReservationResult(
                reserved=True,
                reservation_id="test-reservation",
                reason="reserved",
            )

        async def _settle(*args: object, **kwargs: object) -> SettlementResult:
            settle_calls.append(1)
            return SettlementResult(
                settled=True,
                reservation_id="test-reservation",
                reason="settled",
            )

        quota_registry.check_quota_eligibility = AsyncMock(side_effect=_check)
        quota_registry.reserve_capacity = AsyncMock(side_effect=_reserve)
        quota_registry.settle_reservation = AsyncMock(side_effect=_settle)

        manager = ProviderManager(
            provider_registry,
            capability_registry,
            decision_engine,
            quota_registry=quota_registry,
        )
        provider = _make_provider(
            "openai",
            "OpenAI",
            {"summarization"},
            priority=100,
            provider_config=ProviderConfig(
                provider_name="openai",
                api_key="test",
                input_cost_per_1k_tokens=0.01,
                output_cost_per_1k_tokens=0.02,
            ),
        )
        _register_providers(provider_registry, capability_registry, provider)
        provider.generate.return_value = AIResponse(
            provider="openai",
            model="gpt-4",
            content="ok",
            usage=AIUsage(prompt_tokens=10, completion_tokens=5),
            latency_ms=100.0,
        )

        request = AIRequest(system_prompt="s", user_prompt="u")
        await asyncio.gather(
            *[manager.generate(request, capability="summarization") for _ in range(5)]
        )

        assert len(check_calls) == 5
        assert len(reserve_calls) == 5
        assert len(settle_calls) == 5

    async def test_provider_retry_does_not_bypass_quota_guard(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        """Retries happen inside provider.generate(); the quota guard in
        route() is not re-evaluated on retry, so it cannot be bypassed."""
        quota_registry = _make_quota_registry()
        manager = ProviderManager(
            provider_registry,
            capability_registry,
            decision_engine,
            quota_registry=quota_registry,
        )
        provider = _make_provider(
            "openai",
            "OpenAI",
            {"summarization"},
            priority=100,
            provider_config=ProviderConfig(
                provider_name="openai",
                api_key="test",
                input_cost_per_1k_tokens=0.01,
                output_cost_per_1k_tokens=0.02,
            ),
        )
        _register_providers(provider_registry, capability_registry, provider)
        provider.generate.return_value = AIResponse(
            provider="openai",
            model="gpt-4",
            content="ok",
            usage=AIUsage(prompt_tokens=10, completion_tokens=5),
            latency_ms=100.0,
        )

        request = AIRequest(system_prompt="s", user_prompt="u")
        await manager.generate(request, capability="summarization")

        # Quota check is called once (in route()), not once per retry.
        assert quota_registry.check_quota_eligibility.await_count == 1
        # Reservation is also called once per generate() (atomic gatekeeper).
        assert quota_registry.reserve_capacity.await_count == 1


__all__ = [
    "TestAiDisabledBehavior",
    "TestBudgetBoundarySemantics",
    "TestBuildQuotaConfigFromProviderConfig",
    "TestConcurrentQuotaChecks",
    "TestPerRequestCostCapUnknownPricing",
    "TestProviderLimitsReachQuotaCheck",
    "TestProviderManagerQuotaRouting",
    "TestProviderManagerSettingsEnforcement",
    "TestRedisFailureSafetyGuards",
]
