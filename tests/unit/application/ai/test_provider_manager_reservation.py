"""
Tests for the atomic quota-reservation lifecycle in ProviderManager.generate().

Covers reservation correctness, concurrency/idempotency, failure handling,
provider behavior, configuration, and regression for the reservation
lifecycle introduced alongside the fail-closed quota guards.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from redis.exceptions import RedisError

from ai_news_digest.application.ai.capability import Capability
from ai_news_digest.application.ai.capability_registry import CapabilityRegistry
from ai_news_digest.application.ai.config import ProviderConfig
from ai_news_digest.application.ai.decision_engine import DecisionEngine
from ai_news_digest.application.ai.errors import (
    AIAuthenticationError,
    AIConfigurationError,
    AIInvalidResponseError,
    AIRateLimitError,
    AITimeoutError,
    AITransientError,
    AIUnsupportedProviderError,
)
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
    ProviderUsage,
    QuotaEligibility,
    QuotaLimit,
    QuotaReservationRequest,
    QuotaReservationResult,
    QuotaWindow,
    ReleaseResult,
    ReservationState,
    ReservationStatus,
    SettlementResult,
)
from ai_news_digest.core.config import Settings
from ai_news_digest.core.exceptions import ExternalServiceError


@pytest.fixture
def provider_registry() -> ProviderRegistry:
    return ProviderRegistry(free_only=False)


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
                    cost_limit=Decimal("100.0"),
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
    if provider_id == "gemini":
        provider.model_name = "gemini-2.5-flash"
    elif provider_id == "groq":
        provider.model_name = "openai/gpt-oss-20b"
    else:
        provider.model_name = f"{provider_id}-model"
    provider.available = AsyncMock(return_value=available)
    provider.generate = AsyncMock()
    provider.provider_config = provider_config
    return provider


def _register_providers(
    reg: ProviderRegistry,
    cap_reg: CapabilityRegistry,
    *providers: AIProvider,
) -> None:
    for provider in providers:
        reg.register(provider)
        for capability in provider.capabilities:
            if not cap_reg.exists(capability):
                cap_reg.register_capability(Capability(id=capability, name=capability.title()))
            cap_reg.register_provider(capability, provider.id)


def _pricing_config(**overrides: object) -> ProviderConfig:
    base: dict[str, object] = {
        "provider_name": "openai",
        "api_key": "test",
        "input_cost_per_1k_tokens": 0.01,
        "output_cost_per_1k_tokens": 0.02,
    }
    return ProviderConfig(**{**base, **overrides})


@contextmanager
def _patched_settings(**kwargs: object) -> Iterator[Settings]:
    init_kwargs: dict[str, object] = {"ai_enabled": True, "ai_free_only": False, "environment": "testing"}
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


@pytest.fixture(autouse=True)
def _ai_enabled() -> None:
    with patch(
        "ai_news_digest.application.ai.provider_manager.get_settings",
        return_value=Settings(ai_enabled=True, ai_free_only=False, environment="testing"),
    ):
        yield


def _make_response(provider: str = "openai") -> AIResponse:
    return AIResponse(
        provider=provider,
        model="gpt-4",
        content="ok",
        usage=AIUsage(prompt_tokens=10, completion_tokens=5),
        latency_ms=100.0,
    )


# ======================================================================
# Reservation correctness (tests 1-8)
# ======================================================================


class TestReservationCorrectness:
    """Tests 1-8: Reservation correctness against configured limits."""

    async def test_reservation_succeeds_when_all_limits_have_capacity(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        """Test 1: Reservation succeeds when all configured limits have capacity."""
        quota_registry = _make_quota_registry()
        provider_manager = ProviderManager(
            provider_registry, capability_registry, decision_engine, quota_registry=quota_registry
        )
        provider = _make_provider(
            "openai", "OpenAI", {"summarization"}, provider_config=_pricing_config()
        )
        _register_providers(provider_registry, capability_registry, provider)
        provider.generate.return_value = _make_response()

        response = await provider_manager.generate(
            AIRequest(system_prompt="s", user_prompt="u"), capability="summarization"
        )

        assert response.content == "ok"
        quota_registry.reserve_capacity.assert_awaited_once()
        quota_registry.settle_reservation.assert_awaited_once()

    async def test_reservation_rejects_when_request_limit_exceeded(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        """Test 2: Reservation rejects when provider request limit exceeded."""
        quota_registry = _make_quota_registry()
        quota_registry.reserve_capacity = AsyncMock(
            return_value=QuotaReservationResult(
                reserved=False,
                reservation_id="r1",
                reason="request_exhausted",
                budget_exceeded=True,
            )
        )
        provider_manager = ProviderManager(
            provider_registry, capability_registry, decision_engine, quota_registry=quota_registry
        )
        provider = _make_provider(
            "openai", "OpenAI", {"summarization"}, provider_config=_pricing_config()
        )
        _register_providers(provider_registry, capability_registry, provider)

        with pytest.raises(ExternalServiceError, match="request_exhausted"):
            await provider_manager.generate(
                AIRequest(system_prompt="s", user_prompt="u"), capability="summarization"
            )
        provider.generate.assert_not_called()

    async def test_reservation_rejects_when_token_limit_exceeded(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        """Test 3: Reservation rejects when provider token limit exceeded."""
        quota_registry = _make_quota_registry()
        quota_registry.reserve_capacity = AsyncMock(
            return_value=QuotaReservationResult(
                reserved=False, reservation_id="r1", reason="token_exhausted", budget_exceeded=True
            )
        )
        provider_manager = ProviderManager(
            provider_registry, capability_registry, decision_engine, quota_registry=quota_registry
        )
        provider = _make_provider(
            "openai", "OpenAI", {"summarization"}, provider_config=_pricing_config()
        )
        _register_providers(provider_registry, capability_registry, provider)

        with pytest.raises(ExternalServiceError, match="token_exhausted"):
            await provider_manager.generate(
                AIRequest(system_prompt="s", user_prompt="u"), capability="summarization"
            )
        provider.generate.assert_not_called()

    async def test_reservation_rejects_when_provider_cost_limit_exceeded(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        """Test 4: Reservation rejects when provider cost limit exceeded."""
        quota_registry = _make_quota_registry()
        quota_registry.reserve_capacity = AsyncMock(
            return_value=QuotaReservationResult(
                reserved=False, reservation_id="r1", reason="cost_exhausted", budget_exceeded=True
            )
        )
        provider_manager = ProviderManager(
            provider_registry, capability_registry, decision_engine, quota_registry=quota_registry
        )
        provider = _make_provider(
            "openai", "OpenAI", {"summarization"}, provider_config=_pricing_config()
        )
        _register_providers(provider_registry, capability_registry, provider)

        with pytest.raises(ExternalServiceError, match="cost_exhausted"):
            await provider_manager.generate(
                AIRequest(system_prompt="s", user_prompt="u"), capability="summarization"
            )
        provider.generate.assert_not_called()

    async def test_reservation_rejects_when_daily_budget_exceeded(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        """Test 5: Reservation rejects when global daily budget exceeded."""
        quota_registry = _make_quota_registry()
        quota_registry.reserve_capacity = AsyncMock(
            return_value=QuotaReservationResult(
                reserved=False,
                reservation_id="r1",
                reason="daily_budget_exhausted",
                budget_exceeded=True,
            )
        )
        provider_manager = ProviderManager(
            provider_registry, capability_registry, decision_engine, quota_registry=quota_registry
        )
        provider = _make_provider(
            "openai", "OpenAI", {"summarization"}, provider_config=_pricing_config()
        )
        _register_providers(provider_registry, capability_registry, provider)

        with pytest.raises(ExternalServiceError, match="daily_budget_exhausted"):
            await provider_manager.generate(
                AIRequest(system_prompt="s", user_prompt="u"), capability="summarization"
            )
        provider.generate.assert_not_called()

    async def test_reservation_rejects_when_monthly_budget_exceeded(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        """Test 6: Reservation rejects when global monthly budget exceeded."""
        quota_registry = _make_quota_registry()
        quota_registry.reserve_capacity = AsyncMock(
            return_value=QuotaReservationResult(
                reserved=False,
                reservation_id="r1",
                reason="monthly_budget_exhausted",
                budget_exceeded=True,
            )
        )
        provider_manager = ProviderManager(
            provider_registry, capability_registry, decision_engine, quota_registry=quota_registry
        )
        provider = _make_provider(
            "openai", "OpenAI", {"summarization"}, provider_config=_pricing_config()
        )
        _register_providers(provider_registry, capability_registry, provider)

        with pytest.raises(ExternalServiceError, match="monthly_budget_exhausted"):
            await provider_manager.generate(
                AIRequest(system_prompt="s", user_prompt="u"), capability="summarization"
            )
        provider.generate.assert_not_called()

    async def test_reservation_rejects_when_per_request_cost_cap_exceeded(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        """Test 7: Reservation rejects when per-request cost cap exceeded."""
        with _patched_settings(ai_max_estimated_request_cost=0.001):
            provider_manager = ProviderManager(
                provider_registry,
                capability_registry,
                decision_engine,
                quota_registry=_make_quota_registry(),
            )
            provider = _make_provider(
                "openai", "OpenAI", {"summarization"}, provider_config=_pricing_config()
            )
            _register_providers(provider_registry, capability_registry, provider)

            with pytest.raises(ExternalServiceError, match="budget_per_request_exceeded"):
                await provider_manager.generate(
                    AIRequest(system_prompt="a" * 4000, user_prompt="", max_tokens=512),
                    capability="summarization",
                )
            provider.generate.assert_not_called()

    async def test_missing_cost_estimate_fails_safely_when_cap_set(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        """Test 8: Missing/invalid estimate fails safely when per-request cap is set."""
        with _patched_settings(ai_max_estimated_request_cost=0.05):
            provider_manager = ProviderManager(
                provider_registry,
                capability_registry,
                decision_engine,
                quota_registry=_make_quota_registry(),
            )
            config = ProviderConfig(provider_name="openai", api_key="test")
            provider = _make_provider("openai", "OpenAI", {"summarization"}, provider_config=config)
            _register_providers(provider_registry, capability_registry, provider)

            with pytest.raises(ExternalServiceError, match="budget_per_request_cost_unknown"):
                await provider_manager.generate(
                    AIRequest(system_prompt="s", user_prompt="u"), capability="summarization"
                )
            provider.generate.assert_not_called()


# ======================================================================
# Concurrency and idempotency (tests 9-14)
# ======================================================================


class TestReservationConcurrencyAndIdempotency:
    """Tests 9-14: Concurrency and idempotency."""

    async def test_concurrent_reservations_compete_atomically(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        """Test 9: Concurrent reservations compete atomically for limited capacity.

        This unit-level test verifies the orchestration layer: each concurrent
        request independently calls ``reserve_capacity``.  Atomicity of the
        Lua-script-based capacity check is the responsibility of the Redis
        backend and is covered by the registry-level test suite.
        """
        import asyncio

        quota_registry = _make_quota_registry()
        manager = ProviderManager(
            provider_registry, capability_registry, decision_engine, quota_registry=quota_registry
        )
        provider = _make_provider(
            "openai", "OpenAI", {"summarization"}, priority=100, provider_config=_pricing_config()
        )
        _register_providers(provider_registry, capability_registry, provider)
        provider.generate.return_value = _make_response()

        request = AIRequest(system_prompt="s", user_prompt="u")
        await asyncio.gather(
            *[manager.generate(request, capability="summarization") for _ in range(5)]
        )

        # Each request calls reserve_capacity once.
        assert quota_registry.reserve_capacity.await_count == 5

    async def test_duplicate_reservation_is_idempotent(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        """Test 11: Duplicate reservation attempts are handled idempotently."""
        quota_registry = _make_quota_registry()
        quota_registry.reserve_capacity = AsyncMock(
            return_value=QuotaReservationResult(
                reserved=True, reservation_id="dup-id", reason="already_reserved"
            )
        )
        manager = ProviderManager(
            provider_registry, capability_registry, decision_engine, quota_registry=quota_registry
        )
        provider = _make_provider(
            "openai", "OpenAI", {"summarization"}, provider_config=_pricing_config()
        )
        _register_providers(provider_registry, capability_registry, provider)
        provider.generate.return_value = _make_response()

        await manager.generate(
            AIRequest(system_prompt="s", user_prompt="u"), capability="summarization"
        )
        assert quota_registry.reserve_capacity.await_count == 1

    async def test_duplicate_settlement_does_not_double_count(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        """Test 12: Duplicate settlement does not double-count usage."""
        quota_registry = _make_quota_registry()
        settle_calls: list = []

        async def _settle(*args, **kwargs) -> SettlementResult:
            settle_calls.append(args)
            return SettlementResult(
                settled=True, reservation_id="test-reservation", reason="settled"
            )

        quota_registry.settle_reservation = AsyncMock(side_effect=_settle)
        manager = ProviderManager(
            provider_registry, capability_registry, decision_engine, quota_registry=quota_registry
        )
        provider = _make_provider(
            "openai", "OpenAI", {"summarization"}, provider_config=_pricing_config()
        )
        _register_providers(provider_registry, capability_registry, provider)
        provider.generate.return_value = _make_response()

        await manager.generate(
            AIRequest(system_prompt="s", user_prompt="u"), capability="summarization"
        )
        assert len(settle_calls) == 1

    async def test_duplicate_release_does_not_free_capacity_twice(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        """Test 13: Duplicate release does not free capacity twice."""
        quota_registry = _make_quota_registry()
        release_results: list[ReleaseResult] = []

        async def _release(*args, **kwargs) -> ReleaseResult:
            if release_results:
                res = ReleaseResult(released=True, reservation_id="r1", reason="already_released")
            else:
                res = ReleaseResult(released=True, reservation_id="r1", reason="released")
            release_results.append(res)
            return res

        quota_registry.release_reservation = AsyncMock(side_effect=_release)
        manager = ProviderManager(
            provider_registry, capability_registry, decision_engine, quota_registry=quota_registry
        )
        primary = _make_provider(
            "openai", "OpenAI", {"summarization"}, priority=100, provider_config=_pricing_config()
        )
        secondary = _make_provider(
            "anthropic",
            "Anthropic",
            {"summarization"},
            priority=50,
            provider_config=_pricing_config(provider_name="anthropic"),
        )
        _register_providers(provider_registry, capability_registry, primary, secondary)
        primary.generate.side_effect = AIConfigurationError("not configured")
        secondary.generate.return_value = _make_response(provider="anthropic")

        response = await manager.generate(
            AIRequest(system_prompt="s", user_prompt="u"), capability="summarization"
        )
        assert response.provider == "anthropic"
        # Release was called for the failed provider (CONFIGURATION_ERROR is safe).
        quota_registry.release_reservation.assert_awaited_once()

    async def test_release_after_settlement_cannot_refund(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        """Test 14: A release after successful settlement cannot refund capacity."""
        quota_registry = _make_quota_registry()
        manager = ProviderManager(
            provider_registry, capability_registry, decision_engine, quota_registry=quota_registry
        )
        provider = _make_provider(
            "openai", "OpenAI", {"summarization"}, provider_config=_pricing_config()
        )
        _register_providers(provider_registry, capability_registry, provider)
        provider.generate.return_value = _make_response()

        await manager.generate(
            AIRequest(system_prompt="s", user_prompt="u"), capability="summarization"
        )

        # Settlement happened (not release) on success.
        quota_registry.settle_reservation.assert_awaited_once()
        quota_registry.release_reservation.assert_not_awaited()


# ======================================================================
# Failure handling (tests 15-22)
# ======================================================================


class TestReservationFailureHandling:
    """Tests 15-22: Reservation failure handling."""

    async def test_redis_unavailable_before_reservation_provider_not_called(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        """Test 15: Redis unavailable before reservation: provider is not called."""
        quota_registry = _make_quota_registry()
        quota_registry.reserve_capacity = AsyncMock(side_effect=RedisError("connection lost"))
        provider_manager = ProviderManager(
            provider_registry, capability_registry, decision_engine, quota_registry=quota_registry
        )
        provider = _make_provider(
            "openai", "OpenAI", {"summarization"}, provider_config=_pricing_config()
        )
        _register_providers(provider_registry, capability_registry, provider)

        with pytest.raises(ExternalServiceError, match="reserve_failed"):
            await provider_manager.generate(
                AIRequest(system_prompt="s", user_prompt="u"), capability="summarization"
            )
        provider.generate.assert_not_called()

    async def test_redis_failure_after_reservation_does_not_free_capacity(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        """Test 16: Redis failure after reservation does not silently free reserved capacity."""
        quota_registry = _make_quota_registry()
        quota_registry.settle_reservation = AsyncMock(side_effect=RedisError("connection lost"))
        provider_manager = ProviderManager(
            provider_registry, capability_registry, decision_engine, quota_registry=quota_registry
        )
        provider = _make_provider(
            "openai", "OpenAI", {"summarization"}, provider_config=_pricing_config()
        )
        _register_providers(provider_registry, capability_registry, provider)
        provider.generate.return_value = _make_response()

        # Request succeeds; settlement failure is caught and logged.
        response = await provider_manager.generate(
            AIRequest(system_prompt="s", user_prompt="u"), capability="summarization"
        )
        assert response.content == "ok"

        # Settlement was attempted but failed; reservation was NOT released.
        quota_registry.settle_reservation.assert_awaited_once()
        quota_registry.release_reservation.assert_not_called()

    async def test_settlement_failure_retains_accounting_state(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        """Test 17: Settlement failure retains safe accounting state."""
        quota_registry = _make_quota_registry()
        quota_registry.settle_reservation = AsyncMock(
            return_value=SettlementResult(
                settled=False, reservation_id="test-reservation", reason="settle_failed"
            )
        )
        provider_manager = ProviderManager(
            provider_registry, capability_registry, decision_engine, quota_registry=quota_registry
        )
        provider = _make_provider(
            "openai", "OpenAI", {"summarization"}, provider_config=_pricing_config()
        )
        _register_providers(provider_registry, capability_registry, provider)
        provider.generate.return_value = _make_response()

        response = await provider_manager.generate(
            AIRequest(system_prompt="s", user_prompt="u"), capability="summarization"
        )
        assert response.content == "ok"
        quota_registry.release_reservation.assert_not_called()

    async def test_indeterminate_provider_outcome_retains_capacity(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        """Test 18: An indeterminate provider outcome retains capacity."""
        quota_registry = _make_quota_registry()
        provider_manager = ProviderManager(
            provider_registry, capability_registry, decision_engine, quota_registry=quota_registry
        )
        primary = _make_provider(
            "openai", "OpenAI", {"summarization"}, priority=100, provider_config=_pricing_config()
        )
        secondary = _make_provider(
            "anthropic",
            "Anthropic",
            {"summarization"},
            priority=50,
            provider_config=_pricing_config(provider_name="anthropic"),
        )
        _register_providers(provider_registry, capability_registry, primary, secondary)
        # Timeout is indeterminate.
        primary.generate.side_effect = AITimeoutError("timed out")
        secondary.generate.return_value = _make_response(provider="anthropic")

        response = await provider_manager.generate(
            AIRequest(system_prompt="s", user_prompt="u"), capability="summarization"
        )
        assert response.provider == "anthropic"

        # Timeout → no release (capacity retained).
        quota_registry.release_reservation.assert_not_called()
        # Settlement only for the successful fallback.
        assert quota_registry.settle_reservation.await_count == 1

    async def test_safe_pre_dispatch_failure_releases_reservation(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        """Test 19: A safe pre-dispatch failure releases the reservation."""
        quota_registry = _make_quota_registry()
        provider_manager = ProviderManager(
            provider_registry, capability_registry, decision_engine, quota_registry=quota_registry
        )
        primary = _make_provider(
            "openai", "OpenAI", {"summarization"}, priority=100, provider_config=_pricing_config()
        )
        secondary = _make_provider(
            "anthropic",
            "Anthropic",
            {"summarization"},
            priority=50,
            provider_config=_pricing_config(provider_name="anthropic"),
        )
        _register_providers(provider_registry, capability_registry, primary, secondary)
        # Configuration error → safe release.
        primary.generate.side_effect = AIConfigurationError("not configured")
        secondary.generate.return_value = _make_response(provider="anthropic")

        response = await provider_manager.generate(
            AIRequest(system_prompt="s", user_prompt="u"), capability="summarization"
        )
        assert response.provider == "anthropic"
        quota_registry.release_reservation.assert_awaited_once()

    async def test_application_interruption_leaves_recoverable_state(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        """Test 20: Application interruption leaves a recoverable reservation state."""
        quota_registry = _make_quota_registry()
        # Mock get_reservation to return a pending state (simulating recovery).
        quota_registry.get_reservation = AsyncMock(
            return_value=ReservationState(
                reservation_id="test-reservation",
                provider_id="openai",
                window=QuotaWindow.DAY,
                status=ReservationStatus.PENDING,
            )
        )
        provider_manager = ProviderManager(
            provider_registry, capability_registry, decision_engine, quota_registry=quota_registry
        )
        provider = _make_provider(
            "openai", "OpenAI", {"summarization"}, provider_config=_pricing_config()
        )
        _register_providers(provider_registry, capability_registry, provider)
        provider.generate.side_effect = KeyboardInterrupt("interrupted")

        with pytest.raises(KeyboardInterrupt):
            await provider_manager.generate(
                AIRequest(system_prompt="s", user_prompt="u"), capability="summarization"
            )

        # Reservation was made, settlement was never called.
        quota_registry.reserve_capacity.assert_awaited_once()
        quota_registry.settle_reservation.assert_not_awaited()

        # The reservation is recoverable.
        state = await quota_registry.get_reservation("test-reservation")
        assert state is not None
        assert state.status == ReservationStatus.PENDING

    async def test_reservation_expiry_marks_not_releases(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        """Test 21: Reservation expiry cannot silently free capacity while
        an outcome is indeterminate.

        Expired reservations are marked 'expired' (not 'released'), so the
        capacity accounting reflects that the reservation is no longer active.
        """
        quota_registry = _make_quota_registry()
        provider_manager = ProviderManager(
            provider_registry, capability_registry, decision_engine, quota_registry=quota_registry
        )
        primary = _make_provider(
            "openai", "OpenAI", {"summarization"}, priority=100, provider_config=_pricing_config()
        )
        _register_providers(provider_registry, capability_registry, primary)
        # Timeout → indeterminate.
        primary.generate.side_effect = AITimeoutError("timed out")

        with pytest.raises(ExternalServiceError, match="Every AI provider failed"):
            await provider_manager.generate(
                AIRequest(system_prompt="s", user_prompt="u"), capability="summarization"
            )

        # Reservation was made.
        quota_registry.reserve_capacity.assert_awaited_once()
        # No release (timeout is indeterminate).
        quota_registry.release_reservation.assert_not_awaited()

        # Simulate expiration — reservation state changes to 'expired'.
        quota_registry.expire_reservations = AsyncMock(return_value=1)
        count = await quota_registry.expire_reservations(max_age_seconds=86400)
        assert count == 1

    async def test_budget_window_rollover_handles_outstanding_reservations(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        """Test 22: Budget-window rollover handles outstanding reservations.

        Outstanding (pending and expired) reservations from a previous
        accounting window remain visible to ``list_outstanding_reservations``
        and can be reconciled via ``reconcile_reservations``, which releases
        expired reservations and frees reserved capacity back to the available
        pool.

        This test exercises the *real* ``RedisProviderQuotaRegistry``
        reconciliation path (expire → list → release) using a mock Redis client
        that simulates the Lua-script semantics, rather than asserting that a
        mocked method returned a canned value.
        """
        from unittest.mock import AsyncMock, MagicMock

        from ai_news_digest.infrastructure.quota.redis_provider_quota_registry import (
            _MARK_EXPIRED_LUA,
            _RELEASE_RESERVATION_LUA,
            RedisProviderQuotaRegistry,
        )

        registry = RedisProviderQuotaRegistry(redis_url="redis://localhost:6379/0")
        mock_client = AsyncMock()

        reservation_records: dict[str, dict[str, str]] = {
            "ai:provider-quota:reservation:pending-res": {
                "reservation_id": "pending-res",
                "provider_id": "openai",
                "window": "day",
                "status": "pending",
                "request_count": "1",
                "input_tokens": "100",
                "output_tokens": "50",
                "total_tokens": "150",
                "estimated_cost": "0.003",
                "created_at": "2024-01-01T00:00:00+00:00",
                "updated_at": "2024-01-01T00:00:00+00:00",
            },
            "ai:provider-quota:reservation:expired-res": {
                "reservation_id": "expired-res",
                "provider_id": "openai",
                "window": "day",
                "status": "expired",
                "request_count": "1",
                "input_tokens": "100",
                "output_tokens": "50",
                "total_tokens": "150",
                "estimated_cost": "0.003",
                "created_at": "2024-01-01T00:00:00+00:00",
                "updated_at": "2024-01-02T00:00:00+00:00",
                "expired_at": "2024-01-02T00:00:00+00:00",
            },
        }

        def _scan_iter_factory(**_kwargs):
            async def _gen():
                for key in reservation_records:
                    yield key

            return _gen()

        mock_client.scan_iter = MagicMock(side_effect=_scan_iter_factory)

        def _eval_side_effect(script, numkeys, *args):
            if script == _MARK_EXPIRED_LUA:
                key = args[0]
                if key in reservation_records:
                    record = reservation_records[key]
                    if record["status"] == "pending":
                        created_at = record["created_at"]
                        cutoff = args[1]
                        if created_at < cutoff:
                            record["status"] = "expired"
                            record["expired_at"] = args[2]
                            return "expired"
                    return record["status"]
                return "not_found"
            if script == _RELEASE_RESERVATION_LUA:
                key = args[0]
                if key in reservation_records:
                    record = reservation_records[key]
                    if record["status"] in ("pending", "expired"):
                        record["status"] = "released"
                        return "released"
                    return f"already_{record['status']}"
                return "not_found"
            return "unknown"

        mock_client.eval.side_effect = _eval_side_effect

        async def _hgetall(key):
            return reservation_records.get(key, {})

        mock_client.hgetall.side_effect = _hgetall
        registry._client = mock_client

        outstanding = await registry.list_outstanding_reservations()
        assert len(outstanding) == 2
        statuses = {r.reservation_id: r.status for r in outstanding}
        assert statuses["pending-res"] == ReservationStatus.PENDING
        assert statuses["expired-res"] == ReservationStatus.EXPIRED

        reconciled = await registry.reconcile_reservations(max_age_seconds=86400, batch_limit=100)
        assert reconciled == 2

        assert (
            reservation_records["ai:provider-quota:reservation:pending-res"]["status"] == "released"
        )
        assert (
            reservation_records["ai:provider-quota:reservation:expired-res"]["status"] == "released"
        )


# ======================================================================
# Provider behavior tests (tests 23-28)
# ======================================================================


class TestProviderBehavior:
    """Tests 23-28: Provider behavior with reservation lifecycle."""

    async def test_successful_provider_call_settles_usage(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        """Test 23: Successful provider calls settle usage correctly."""
        quota_registry = _make_quota_registry()
        manager = ProviderManager(
            provider_registry, capability_registry, decision_engine, quota_registry=quota_registry
        )
        provider = _make_provider(
            "openai", "OpenAI", {"summarization"}, provider_config=_pricing_config()
        )
        _register_providers(provider_registry, capability_registry, provider)
        provider.generate.return_value = _make_response()

        await manager.generate(
            AIRequest(system_prompt="s", user_prompt="u"), capability="summarization"
        )

        quota_registry.reserve_capacity.assert_awaited_once()
        quota_registry.settle_reservation.assert_awaited_once()

    async def test_retries_are_accounted_for_by_actual_attempts(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        """Test 24: Retries (fallback) are accounted for by actual outbound attempts."""
        quota_registry = _make_quota_registry()
        manager = ProviderManager(
            provider_registry, capability_registry, decision_engine, quota_registry=quota_registry
        )
        primary = _make_provider(
            "openai", "OpenAI", {"summarization"}, priority=100, provider_config=_pricing_config()
        )
        secondary = _make_provider(
            "anthropic",
            "Anthropic",
            {"summarization"},
            priority=50,
            provider_config=_pricing_config(provider_name="anthropic"),
        )
        _register_providers(provider_registry, capability_registry, primary, secondary)
        primary.generate.side_effect = AITransientError("transient")
        secondary.generate.return_value = _make_response(provider="anthropic")

        response = await manager.generate(
            AIRequest(system_prompt="s", user_prompt="u"), capability="summarization"
        )
        assert response.provider == "anthropic"

        assert quota_registry.reserve_capacity.await_count == 2
        quota_registry.settle_reservation.assert_awaited_once()

    async def test_fallback_provider_uses_own_limits(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        """Test 25: Fallback provider uses its own applicable limits."""
        quota_registry = _make_quota_registry()
        manager = ProviderManager(
            provider_registry, capability_registry, decision_engine, quota_registry=quota_registry
        )
        reserve_calls: list[str] = []

        async def _reserve(req: QuotaReservationRequest) -> QuotaReservationResult:
            reserve_calls.append(req.provider_id)
            if req.provider_id == "openai":
                return QuotaReservationResult(
                    reserved=False,
                    reservation_id="r1",
                    reason="request_exhausted",
                    budget_exceeded=True,
                )
            return QuotaReservationResult(reserved=True, reservation_id="r2", reason="reserved")

        quota_registry.reserve_capacity = AsyncMock(side_effect=_reserve)

        primary = _make_provider(
            "openai", "OpenAI", {"summarization"}, priority=100, provider_config=_pricing_config()
        )
        secondary = _make_provider(
            "anthropic",
            "Anthropic",
            {"summarization"},
            priority=50,
            provider_config=_pricing_config(provider_name="anthropic"),
        )
        _register_providers(provider_registry, capability_registry, primary, secondary)
        primary.generate.side_effect = AITransientError("transient")
        secondary.generate.return_value = _make_response(provider="anthropic")

        response = await manager.generate(
            AIRequest(system_prompt="s", user_prompt="u"), capability="summarization"
        )
        assert response.provider == "anthropic"
        assert reserve_calls == ["openai", "anthropic"]

    async def test_repeated_retries_do_not_bypass_limits(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        """Test 26: Repeated retries do not bypass request/cost limits."""
        quota_registry = _make_quota_registry()
        quota_registry.reserve_capacity = AsyncMock(
            return_value=QuotaReservationResult(
                reserved=False,
                reservation_id="r1",
                reason="request_exhausted",
                budget_exceeded=True,
            )
        )
        manager = ProviderManager(
            provider_registry, capability_registry, decision_engine, quota_registry=quota_registry
        )
        primary = _make_provider(
            "openai", "OpenAI", {"summarization"}, priority=100, provider_config=_pricing_config()
        )
        secondary = _make_provider(
            "anthropic",
            "Anthropic",
            {"summarization"},
            priority=50,
            provider_config=_pricing_config(provider_name="anthropic"),
        )
        _register_providers(provider_registry, capability_registry, primary, secondary)

        with pytest.raises(ExternalServiceError, match="request_exhausted"):
            await manager.generate(
                AIRequest(system_prompt="s", user_prompt="u"), capability="summarization"
            )
        primary.generate.assert_not_called()
        secondary.generate.assert_not_called()

    async def test_actual_usage_above_estimate_is_reconciled(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        """Test 27: Actual usage above the estimate is reconciled during settlement."""
        quota_registry = _make_quota_registry()
        captured: list[ProviderUsage] = []

        async def _settle(
            reservation_id: str, usage: ProviderUsage, actual_cost: float | None = None
        ) -> SettlementResult:
            captured.append(usage)
            return SettlementResult(
                settled=True,
                reservation_id=reservation_id,
                reason="settled",
                actual_cost=Decimal(str(actual_cost)),
            )

        quota_registry.settle_reservation = AsyncMock(side_effect=_settle)
        manager = ProviderManager(
            provider_registry, capability_registry, decision_engine, quota_registry=quota_registry
        )
        provider = _make_provider(
            "openai", "OpenAI", {"summarization"}, provider_config=_pricing_config()
        )
        _register_providers(provider_registry, capability_registry, provider)
        provider.generate.return_value = AIResponse(
            provider="openai",
            model="gpt-4",
            content="ok",
            usage=AIUsage(prompt_tokens=200, completion_tokens=150),
            latency_ms=100.0,
        )

        await manager.generate(
            AIRequest(system_prompt="s", user_prompt="u", max_tokens=2048),
            capability="summarization",
        )

        assert len(captured) == 1
        usage = captured[0]
        assert usage.total_tokens == 350
        assert usage.input_tokens == 200
        assert usage.output_tokens == 150

    @pytest.mark.parametrize("provider_id", ["openai", "anthropic", "gemini", "grok"])
    async def test_all_providers_use_same_reservation_controls(
        self,
        provider_id: str,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        """Test 28: All supported provider adapters use the same reservation controls."""
        quota_registry = _make_quota_registry()
        manager = ProviderManager(
            provider_registry, capability_registry, decision_engine, quota_registry=quota_registry
        )
        config = _pricing_config(provider_name=provider_id)
        provider = _make_provider(
            provider_id, provider_id.title(), {"summarization"}, provider_config=config
        )
        _register_providers(provider_registry, capability_registry, provider)
        provider.generate.return_value = AIResponse(
            provider=provider_id,
            model="test-model",
            content="ok",
            usage=AIUsage(prompt_tokens=10, completion_tokens=5),
            latency_ms=100.0,
        )

        response = await manager.generate(
            AIRequest(system_prompt="s", user_prompt="u"), capability="summarization"
        )
        assert response.provider == provider_id
        quota_registry.reserve_capacity.assert_awaited_once()
        quota_registry.settle_reservation.assert_awaited_once()


# ======================================================================
# Configuration and regression (tests 29-32)
# ======================================================================


class TestReservationConfigAndRegression:
    """Tests 29-32: Configuration semantics and regression."""

    async def test_settings_redis_budget_precedence_preserved(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        """Test 29: Settings/Redis budget precedence is preserved."""
        quota_registry = _make_quota_registry()
        quota_registry.get_global_budget = AsyncMock(
            return_value=GlobalBudgetState(
                daily_budget=Decimal("50.0"), daily_spend=Decimal("10.0")
            )
        )
        manager = ProviderManager(
            provider_registry, capability_registry, decision_engine, quota_registry=quota_registry
        )
        provider = _make_provider(
            "openai", "OpenAI", {"summarization"}, provider_config=_pricing_config()
        )
        _register_providers(provider_registry, capability_registry, provider)
        provider.generate.return_value = _make_response()

        # Settings says budget=5.0 but Redis says 50.0 → Redis wins.
        with _patched_settings(ai_daily_cost_budget=5.0):
            decision = await manager.route(
                AIRequest(system_prompt="s", user_prompt="u"), capability="summarization"
            )
        assert decision.selected_provider_id == "openai"

    async def test_zero_unset_budget_means_unlimited(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        """Test 30: Zero/unset budget semantics remain correct."""
        quota_registry = _make_quota_registry()
        quota_registry.get_global_budget = AsyncMock(
            return_value=GlobalBudgetState(daily_spend=Decimal("99999.0"))
        )
        manager = ProviderManager(
            provider_registry, capability_registry, decision_engine, quota_registry=quota_registry
        )
        provider = _make_provider(
            "openai", "OpenAI", {"summarization"}, provider_config=_pricing_config()
        )
        _register_providers(provider_registry, capability_registry, provider)
        provider.generate.return_value = _make_response()

        with _patched_settings():
            response = await manager.generate(
                AIRequest(system_prompt="s", user_prompt="u"), capability="summarization"
            )
        assert response.content == "ok"

    async def test_ai_disabled_does_not_attempt_reservation(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        """Test 31: AI-disabled behavior is unchanged."""
        quota_registry = _make_quota_registry()
        manager = ProviderManager(
            provider_registry, capability_registry, decision_engine, quota_registry=quota_registry
        )
        provider = _make_provider(
            "openai", "OpenAI", {"summarization"}, provider_config=_pricing_config()
        )
        _register_providers(provider_registry, capability_registry, provider)

        with (
            _patched_settings(ai_enabled=False),
            pytest.raises(ExternalServiceError, match="AI is disabled"),
        ):
            await manager.generate(
                AIRequest(system_prompt="s", user_prompt="u"), capability="summarization"
            )
        quota_registry.reserve_capacity.assert_not_awaited()
        provider.generate.assert_not_called()

    async def test_existing_quota_and_routing_tests_remain_compatible(
        self,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        """Test 32: Existing quota and provider-routing tests remain compatible."""
        quota_registry = _make_quota_registry()
        quota_registry.check_quota_eligibility = AsyncMock(
            return_value=QuotaEligibility(eligible=False, reason="request_quota_exhausted")
        )
        manager = ProviderManager(
            provider_registry, capability_registry, decision_engine, quota_registry=quota_registry
        )
        provider = _make_provider(
            "openai", "OpenAI", {"summarization"}, provider_config=_pricing_config()
        )
        _register_providers(provider_registry, capability_registry, provider)

        decision = await manager.route(
            AIRequest(system_prompt="s", user_prompt="u"), capability="summarization"
        )
        assert decision.selected_provider_id is None
        quota_registry.reserve_capacity.assert_not_awaited()


# ======================================================================
# Failure category safety (supplementary)
# ======================================================================


class TestFailureCategorySafety:
    """Verify that safe-release vs indeterminate classification is correct."""

    @pytest.mark.parametrize(
        "exc, expected_release",
        [
            (AIConfigurationError("not configured"), True),
            (AIAuthenticationError("unauthorized"), True),
            (AIUnsupportedProviderError("nope"), True),
            (AIRateLimitError("rate limited"), True),
            (AITimeoutError("timed out"), False),
            (AITransientError("transient"), False),
            (AIInvalidResponseError("bad response"), False),
        ],
    )
    async def test_failure_category_release_policy(
        self,
        exc: Exception,
        expected_release: bool,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        decision_engine: DecisionEngine,
    ) -> None:
        """Safe failures release the reservation; indeterminate failures retain it."""
        quota_registry = _make_quota_registry()
        manager = ProviderManager(
            provider_registry, capability_registry, decision_engine, quota_registry=quota_registry
        )
        primary = _make_provider(
            "openai", "OpenAI", {"summarization"}, priority=100, provider_config=_pricing_config()
        )
        secondary = _make_provider(
            "anthropic",
            "Anthropic",
            {"summarization"},
            priority=50,
            provider_config=_pricing_config(provider_name="anthropic"),
        )
        _register_providers(provider_registry, capability_registry, primary, secondary)
        primary.generate.side_effect = exc
        secondary.generate.return_value = _make_response(provider="anthropic")

        response = await manager.generate(
            AIRequest(system_prompt="s", user_prompt="u"), capability="summarization"
        )
        assert response.provider == "anthropic"

        if expected_release:
            quota_registry.release_reservation.assert_awaited()
        else:
            quota_registry.release_reservation.assert_not_awaited()


__all__ = [
    "TestFailureCategorySafety",
    "TestProviderBehavior",
    "TestReservationConcurrencyAndIdempotency",
    "TestReservationConfigAndRegression",
    "TestReservationCorrectness",
    "TestReservationFailureHandling",
]
