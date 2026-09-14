"""
Unit tests for M79 quota-aware provider routing.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

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
from ai_news_digest.application.ai.provider_manager import ProviderManager
from ai_news_digest.application.ai.provider_quota_registry import ProviderQuotaRegistry
from ai_news_digest.application.ai.provider_registry import ProviderRegistry
from ai_news_digest.application.ai.providers.base import AIProvider
from ai_news_digest.application.ai.quota import (
    GlobalBudgetState,
    ProviderQuotaConfig,
    QuotaEligibility,
    QuotaLimit,
    QuotaWindow,
)
from ai_news_digest.core.config import Settings


@pytest.fixture
def provider_registry() -> ProviderRegistry:
    return ProviderRegistry()


@pytest.fixture
def capability_registry() -> CapabilityRegistry:
    registry = CapabilityRegistry()
    registry.register_capability(
        Capability(id="summarization", name="Summarization")
    )
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
            "openai", "OpenAI", {"summarization"}, priority=100,
            provider_config=ProviderConfig(provider_name="openai", api_key="test"),
        )
        available = _make_provider(
            "anthropic", "Anthropic", {"summarization"}, priority=50,
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
            "openai", "OpenAI", {"summarization"}, priority=100,
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
            "openai", "OpenAI", {"summarization"}, priority=100,
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
            "openai", "OpenAI", {"summarization"}, priority=100,
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

        quota_registry.record_usage.assert_called()
        quota_registry.update_global_budget.assert_called()

    async def test_generate_releases_reservation_on_failure(
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
            "openai", "OpenAI", {"summarization"}, priority=100,
            provider_config=ProviderConfig(provider_name="openai", api_key="test"),
        )
        succeeding = _make_provider(
            "anthropic", "Anthropic", {"summarization"}, priority=50,
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
        await provider_manager.generate(request, capability="summarization")

        quota_registry.reset_provider_quota.assert_called_with("openai")

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
            "openai", "OpenAI", {"summarization"}, priority=100,
            provider_config=ProviderConfig(provider_name="openai", api_key="test"),
        )
        _register_providers(provider_registry, capability_registry, exhausted)

        request = AIRequest(system_prompt="s", user_prompt="u")
        decision = await provider_manager.route(request, capability="summarization")

        assert decision.selected_provider_id is None
        assert len(decision.quota_exclusions) == 1
        assert decision.quota_exclusions[0] == ("openai", "token_quota_exhausted")


__all__ = ["TestProviderManagerQuotaRouting"]
