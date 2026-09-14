"""
Unit tests for InMemoryProviderHealthRegistry circuit breaker.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from ai_news_digest.application.ai.errors import (
    AIAuthenticationError,
    AIConfigurationError,
    AITimeoutError,
    AITransientError,
)
from ai_news_digest.application.ai.provider_health import (
    CircuitBreakerPolicy,
    CircuitState,
    FailureCategory,
)
from ai_news_digest.infrastructure.health.in_memory_provider_health_registry import (
    InMemoryProviderHealthRegistry,
)


@pytest.fixture
def registry() -> InMemoryProviderHealthRegistry:
    return InMemoryProviderHealthRegistry(policy=CircuitBreakerPolicy(failure_threshold=3, cooldown_seconds=60))


class TestInMemoryProviderHealthRegistryClosed:
    async def test_initial_state_is_closed(self, registry: InMemoryProviderHealthRegistry) -> None:
        state = await registry.get_state("openai")
        assert state.state == CircuitState.CLOSED

    async def test_success_keeps_closed(self, registry: InMemoryProviderHealthRegistry) -> None:
        await registry.record_success("openai")
        state = await registry.get_state("openai")
        assert state.state == CircuitState.CLOSED
        assert state.consecutive_failures == 0

    async def test_non_counting_failure_does_not_increment(self, registry: InMemoryProviderHealthRegistry) -> None:
        await registry.record_failure("openai", FailureCategory.CONFIGURATION_ERROR)
        state = await registry.get_state("openai")
        assert state.state == CircuitState.CLOSED
        assert state.consecutive_failures == 0

    async def test_counting_failure_increments(self, registry: InMemoryProviderHealthRegistry) -> None:
        await registry.record_failure("openai", FailureCategory.TIMEOUT)
        state = await registry.get_state("openai")
        assert state.consecutive_failures == 1
        assert state.state == CircuitState.CLOSED

    async def test_threshold_reached_opens_circuit(self, registry: InMemoryProviderHealthRegistry) -> None:
        for _ in range(3):
            await registry.record_failure("openai", FailureCategory.TIMEOUT)
        state = await registry.get_state("openai")
        assert state.state == CircuitState.OPEN
        assert state.consecutive_failures == 3
        assert state.opened_at is not None
        assert state.cooldown_until is not None

    async def test_open_provider_is_not_eligible(self, registry: InMemoryProviderHealthRegistry) -> None:
        for _ in range(3):
            await registry.record_failure("openai", FailureCategory.TIMEOUT)
        assert await registry.is_eligible("openai") is False

    async def test_closed_provider_is_eligible(self, registry: InMemoryProviderHealthRegistry) -> None:
        assert await registry.is_eligible("openai") is True


class TestInMemoryProviderHealthRegistryOpen:
    async def test_reset_returns_to_closed(self, registry: InMemoryProviderHealthRegistry) -> None:
        for _ in range(3):
            await registry.record_failure("openai", FailureCategory.TIMEOUT)
        state = await registry.reset("openai")
        assert state.state == CircuitState.CLOSED
        assert state.consecutive_failures == 0

    async def test_get_all_states_returns_open(self, registry: InMemoryProviderHealthRegistry) -> None:
        for _ in range(3):
            await registry.record_failure("openai", FailureCategory.TIMEOUT)
        all_states = await registry.get_all_states()
        assert "openai" in all_states
        assert all_states["openai"].state == CircuitState.OPEN


class TestInMemoryProviderHealthRegistryHalfOpen:
    async def test_cooldown_expired_allows_probe_lease(self, registry: InMemoryProviderHealthRegistry) -> None:
        for _ in range(3):
            await registry.record_failure("openai", FailureCategory.TIMEOUT)
        state = await registry.get_state("openai")
        assert state.state == CircuitState.OPEN

        past_cooldown = datetime.now(timezone.utc) - timedelta(seconds=61)
        state.cooldown_until = past_cooldown

        acquired = await registry.try_acquire_probe_lease("openai")
        assert acquired is True
        state = await registry.get_state("openai")
        assert state.state == CircuitState.HALF_OPEN

    async def test_concurrent_probe_lease_prevents_duplicate(self, registry: InMemoryProviderHealthRegistry) -> None:
        for _ in range(3):
            await registry.record_failure("openai", FailureCategory.TIMEOUT)
        past_cooldown = datetime.now(timezone.utc) - timedelta(seconds=61)
        state = await registry.get_state("openai")
        state.cooldown_until = past_cooldown

        acquired1 = await registry.try_acquire_probe_lease("openai")
        acquired2 = await registry.try_acquire_probe_lease("openai")
        assert acquired1 is True
        assert acquired2 is False

    async def test_half_open_success_closes_circuit(self, registry: InMemoryProviderHealthRegistry) -> None:
        for _ in range(3):
            await registry.record_failure("openai", FailureCategory.TIMEOUT)
        past_cooldown = datetime.now(timezone.utc) - timedelta(seconds=61)
        state = await registry.get_state("openai")
        state.cooldown_until = past_cooldown
        await registry.try_acquire_probe_lease("openai")
        await registry.record_success("openai")
        state = await registry.get_state("openai")
        assert state.state == CircuitState.CLOSED
        assert state.consecutive_failures == 0

    async def test_half_open_failure_reopens_circuit(self, registry: InMemoryProviderHealthRegistry) -> None:
        for _ in range(3):
            await registry.record_failure("openai", FailureCategory.TIMEOUT)
        past_cooldown = datetime.now(timezone.utc) - timedelta(seconds=61)
        state = await registry.get_state("openai")
        state.cooldown_until = past_cooldown
        await registry.try_acquire_probe_lease("openai")
        await registry.record_failure("openai", FailureCategory.TIMEOUT)
        state = await registry.get_state("openai")
        assert state.state == CircuitState.OPEN
        assert state.cooldown_until is not None


class TestInMemoryProviderHealthRegistryAuthFailure:
    async def test_auth_failure_opens_circuit(self, registry: InMemoryProviderHealthRegistry) -> None:
        for _ in range(3):
            await registry.record_failure("openai", FailureCategory.AUTHENTICATION_FAILURE)
        state = await registry.get_state("openai")
        assert state.state == CircuitState.OPEN


class TestInMemoryProviderHealthRegistryFallback:
    async def test_half_open_not_eligible_for_normal_routing(self, registry: InMemoryProviderHealthRegistry) -> None:
        for _ in range(3):
            await registry.record_failure("openai", FailureCategory.TIMEOUT)
        past_cooldown = datetime.now(timezone.utc) - timedelta(seconds=61)
        state = await registry.get_state("openai")
        state.cooldown_until = past_cooldown
        await registry.try_acquire_probe_lease("openai")
        assert await registry.is_eligible("openai") is False


__all__ = ["TestInMemoryProviderHealthRegistry"]
