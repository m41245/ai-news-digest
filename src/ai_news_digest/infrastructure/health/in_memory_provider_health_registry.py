from __future__ import annotations

import threading
from datetime import datetime, timedelta

from ai_news_digest.application.ai.provider_health import (
    CircuitBreakerPolicy,
    CircuitState,
    FailureCategory,
    ProviderHealthState,
    counts_toward_circuit,
    utc_now,
)
from ai_news_digest.application.ai.provider_health_registry import (
    ProviderHealthRegistry,
)
from ai_news_digest.core.logging import get_logger

logger = get_logger(__name__)


class InMemoryProviderHealthRegistry(ProviderHealthRegistry):
    """In-memory provider health registry for testing and fallback."""

    def __init__(self, policy: CircuitBreakerPolicy | None = None) -> None:
        self._policy = policy or CircuitBreakerPolicy()
        self._states: dict[str, ProviderHealthState] = {}
        self._lock = threading.Lock()

    def _get_or_create(self, provider_id: str) -> ProviderHealthState:
        if provider_id not in self._states:
            self._states[provider_id] = ProviderHealthState(provider_id=provider_id)
        return self._states[provider_id]

    def _apply_failure(
        self, state: ProviderHealthState, category: FailureCategory, now: datetime
    ) -> None:
        counts = counts_toward_circuit(category)
        if not counts:
            return

        if state.state == CircuitState.HALF_OPEN:
            state.state = CircuitState.OPEN
            state.opened_at = now
            state.cooldown_until = now + timedelta(seconds=self._policy.cooldown_seconds)
            state.consecutive_failures += 1
            state.last_failure_at = now
            state.consecutive_successes = 0
            logger.warning(
                "Provider circuit reopened",
                provider_id=state.provider_id,
                failure_category=category.value,
                consecutive_failures=state.consecutive_failures,
            )
            return

        state.consecutive_failures += 1
        state.last_failure_at = now

        if state.consecutive_failures >= self._policy.failure_threshold:
            state.state = CircuitState.OPEN
            state.opened_at = now
            state.cooldown_until = now + timedelta(seconds=self._policy.cooldown_seconds)
            logger.warning(
                "Provider circuit opened",
                provider_id=state.provider_id,
                failure_category=category.value,
                consecutive_failures=state.consecutive_failures,
            )

    def _apply_success(self, state: ProviderHealthState, now: datetime) -> None:
        state.last_success_at = now
        state.consecutive_successes += 1

        if state.state == CircuitState.HALF_OPEN:
            if state.consecutive_successes >= self._policy.success_threshold_to_close:
                state.state = CircuitState.CLOSED
                state.consecutive_failures = 0
                state.consecutive_successes = 0
                state.opened_at = None
                state.cooldown_until = None
                state.next_probe_at = None
                logger.info(
                    "Provider circuit closed",
                    provider_id=state.provider_id,
                    consecutive_successes=state.consecutive_successes,
                )
        else:
            state.consecutive_failures = 0

    async def get_state(self, provider_id: str) -> ProviderHealthState:
        with self._lock:
            return self._get_or_create(provider_id)

    async def record_success(self, provider_id: str) -> ProviderHealthState:
        with self._lock:
            state = self._get_or_create(provider_id)
            now = utc_now()
            self._apply_success(state, now)
            return state

    async def record_failure(
        self,
        provider_id: str,
        category: str | FailureCategory,
    ) -> ProviderHealthState:
        cat = category if isinstance(category, FailureCategory) else FailureCategory(category)
        with self._lock:
            state = self._get_or_create(provider_id)
            now = utc_now()
            self._apply_failure(state, cat, now)
            return state

    async def is_eligible(self, provider_id: str) -> bool:
        with self._lock:
            state = self._get_or_create(provider_id)
            if state.state == CircuitState.CLOSED:
                return True
            if state.state == CircuitState.HALF_OPEN:
                return False
            if state.state == CircuitState.OPEN:
                now = utc_now()
                if state.cooldown_until is not None and now >= state.cooldown_until:
                    return False
                return False
            raise AssertionError(f"Unknown circuit state: {state.state}")

    async def try_acquire_probe_lease(self, provider_id: str) -> bool:
        with self._lock:
            state = self._get_or_create(provider_id)
            now = utc_now()

            if state.state != CircuitState.OPEN:
                return False
            if state.cooldown_until is not None and now < state.cooldown_until:
                return False

            state.state = CircuitState.HALF_OPEN
            state.next_probe_at = now
            logger.info("Acquired half-open probe lease (in-memory)", provider_id=provider_id)
            return True

    async def release_probe_lease(self, provider_id: str) -> None:
        pass

    async def reset(self, provider_id: str) -> ProviderHealthState:
        with self._lock:
            now = utc_now()
            state = ProviderHealthState(
                provider_id=provider_id,
                state=CircuitState.CLOSED,
                last_success_at=now,
            )
            self._states[provider_id] = state
            logger.info("Provider circuit reset (in-memory)", provider_id=provider_id)
            return state

    async def get_all_states(self) -> dict[str, ProviderHealthState]:
        with self._lock:
            return dict(self._states)


__all__ = ["InMemoryProviderHealthRegistry"]
