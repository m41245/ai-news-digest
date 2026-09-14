"""
Unit tests for provider health model and failure classification.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

import pytest

from ai_news_digest.application.ai.errors import (
    AIAuthenticationError,
    AIConfigurationError,
    AIInvalidResponseError,
    AIPermanentProcessingError,
    AIRateLimitError,
    AITimeoutError,
    AITransientError,
    AIUnsupportedProviderError,
)
from ai_news_digest.application.ai.provider_health import (
    CircuitBreakerPolicy,
    CircuitState,
    FailureCategory,
    ProviderHealthState,
    classify_failure,
    counts_toward_circuit,
    utc_now,
)


class TestCircuitState:
    def test_closed_value(self) -> None:
        assert CircuitState.CLOSED.value == "closed"

    def test_open_value(self) -> None:
        assert CircuitState.OPEN.value == "open"

    def test_half_open_value(self) -> None:
        assert CircuitState.HALF_OPEN.value == "half_open"


class TestFailureCategory:
    def test_timeout_value(self) -> None:
        assert FailureCategory.TIMEOUT.value == "timeout"

    def test_rate_limited_value(self) -> None:
        assert FailureCategory.RATE_LIMITED.value == "rate_limited"

    def test_auth_failure_value(self) -> None:
        assert FailureCategory.AUTHENTICATION_FAILURE.value == "auth_failure"


class TestClassifyFailure:
    def test_classify_timeout(self) -> None:
        assert classify_failure(AITimeoutError("timeout")) == FailureCategory.TIMEOUT

    def test_classify_transient(self) -> None:
        assert classify_failure(AITransientError("transient")) == FailureCategory.TEMPORARY_FAILURE

    def test_classify_rate_limit(self) -> None:
        assert classify_failure(AIRateLimitError("rate limit")) == FailureCategory.RATE_LIMITED

    def test_classify_auth_failure(self) -> None:
        assert classify_failure(AIAuthenticationError("auth")) == FailureCategory.AUTHENTICATION_FAILURE

    def test_classify_config_error(self) -> None:
        assert classify_failure(AIConfigurationError("config")) == FailureCategory.CONFIGURATION_ERROR

    def test_classify_invalid_response(self) -> None:
        assert classify_failure(AIInvalidResponseError("invalid")) == FailureCategory.INVALID_RESPONSE

    def test_classify_unsupported(self) -> None:
        assert classify_failure(AIUnsupportedProviderError("unsupported")) == FailureCategory.UNSUPPORTED_CAPABILITY

    def test_classify_permanent(self) -> None:
        assert classify_failure(AIPermanentProcessingError("permanent")) == FailureCategory.PERMANENT_PROCESSING_ERROR

    def test_classify_unknown_exception(self) -> None:
        assert classify_failure(ValueError("unknown")) == FailureCategory.TEMPORARY_FAILURE


class TestCountsTowardCircuit:
    def test_timeout_counts(self) -> None:
        assert counts_toward_circuit(FailureCategory.TIMEOUT) is True

    def test_transient_counts(self) -> None:
        assert counts_toward_circuit(FailureCategory.TEMPORARY_FAILURE) is True

    def test_rate_limited_counts(self) -> None:
        assert counts_toward_circuit(FailureCategory.RATE_LIMITED) is True

    def test_auth_failure_counts(self) -> None:
        assert counts_toward_circuit(FailureCategory.AUTHENTICATION_FAILURE) is True

    def test_invalid_response_counts(self) -> None:
        assert counts_toward_circuit(FailureCategory.INVALID_RESPONSE) is True

    def test_config_error_does_not_count(self) -> None:
        assert counts_toward_circuit(FailureCategory.CONFIGURATION_ERROR) is False

    def test_unsupported_does_not_count(self) -> None:
        assert counts_toward_circuit(FailureCategory.UNSUPPORTED_CAPABILITY) is False

    def test_permanent_does_not_count(self) -> None:
        assert counts_toward_circuit(FailureCategory.PERMANENT_PROCESSING_ERROR) is False


class TestProviderHealthState:
    def test_initial_state_is_closed(self) -> None:
        state = ProviderHealthState(provider_id="openai")
        assert state.state == CircuitState.CLOSED
        assert state.consecutive_failures == 0
        assert state.consecutive_successes == 0

    def test_is_stale_when_open_and_cooldown_expired(self) -> None:
        state = ProviderHealthState(
            provider_id="openai",
            state=CircuitState.OPEN,
            cooldown_until=datetime.now(timezone.utc) - timedelta(seconds=1),
        )
        assert state.is_stale(utc_now()) is True

    def test_is_not_stale_when_open_and_cooldown_not_expired(self) -> None:
        state = ProviderHealthState(
            provider_id="openai",
            state=CircuitState.OPEN,
            cooldown_until=datetime.now(timezone.utc) + timedelta(seconds=30),
        )
        assert state.is_stale(utc_now()) is False

    def test_is_not_stale_when_closed(self) -> None:
        state = ProviderHealthState(provider_id="openai", state=CircuitState.CLOSED)
        assert state.is_stale(utc_now()) is False


class TestCircuitBreakerPolicy:
    def test_default_policy(self) -> None:
        policy = CircuitBreakerPolicy()
        assert policy.failure_threshold == 3
        assert policy.cooldown_seconds == 60.0

    def test_invalid_threshold_raises(self) -> None:
        with pytest.raises(ValueError, match="failure_threshold must be >= 1"):
            CircuitBreakerPolicy(failure_threshold=0)

    def test_negative_cooldown_raises(self) -> None:
        with pytest.raises(ValueError, match="cooldown_seconds must be >= 0"):
            CircuitBreakerPolicy(cooldown_seconds=-1)

    def test_zero_probe_timeout_raises(self) -> None:
        with pytest.raises(ValueError, match="half_open_probe_timeout_seconds must be > 0"):
            CircuitBreakerPolicy(half_open_probe_timeout_seconds=0)


class TestUtcNow:
    def test_returns_aware_datetime(self) -> None:
        now = utc_now()
        assert now.tzinfo is not None
        assert now.tzinfo.utcoffset(now) is not None


__all__ = [
    "TestCircuitBreakerPolicy",
    "TestCircuitState",
    "TestClassifyFailure",
    "TestCountsTowardCircuit",
    "TestFailureCategory",
    "TestProviderHealthState",
    "TestUtcNow",
]
