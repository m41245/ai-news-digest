from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class CircuitState(StrEnum):
    """Provider circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class FailureCategory(StrEnum):
    """Categories of provider failures for circuit breaker policy."""

    TIMEOUT = "timeout"
    TEMPORARY_FAILURE = "temporary_failure"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    RATE_LIMITED = "rate_limited"
    AUTHENTICATION_FAILURE = "auth_failure"
    INVALID_RESPONSE = "invalid_response"
    CONFIGURATION_ERROR = "configuration_error"
    UNSUPPORTED_CAPABILITY = "unsupported_capability"
    PERMANENT_PROCESSING_ERROR = "permanent_processing_error"
    INVALID_REQUEST = "invalid_request"


@dataclass(slots=True)
class ProviderHealthState:
    """Runtime health state for a single AI provider."""

    provider_id: str
    state: CircuitState = CircuitState.CLOSED
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    last_failure_at: datetime | None = None
    last_success_at: datetime | None = None
    opened_at: datetime | None = None
    cooldown_until: datetime | None = None
    next_probe_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_stale(self, now: datetime) -> bool:
        """Return True if the state has exceeded its maximum allowed age."""
        if self.state == CircuitState.OPEN and self.cooldown_until is not None:
            return now > self.cooldown_until
        return False


@dataclass(slots=True)
class CircuitBreakerPolicy:
    """Configuration for circuit breaker behavior."""

    failure_threshold: int = 3
    cooldown_seconds: float = 60.0
    half_open_probe_timeout_seconds: float = 30.0
    auth_failure_immediate_open: bool = True
    success_threshold_to_close: int = 1

    def __post_init__(self) -> None:
        if self.failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        if self.cooldown_seconds < 0:
            raise ValueError("cooldown_seconds must be >= 0")
        if self.half_open_probe_timeout_seconds <= 0:
            raise ValueError("half_open_probe_timeout_seconds must be > 0")
        if self.success_threshold_to_close < 1:
            raise ValueError("success_threshold_to_close must be >= 1")


def utc_now() -> datetime:
    """Return the current UTC time with timezone info."""
    return datetime.now(UTC)


def classify_failure(exc: BaseException) -> FailureCategory:
    """Classify an exception into a circuit-breaker-relevant failure category."""
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

    if isinstance(exc, AITimeoutError):
        return FailureCategory.TIMEOUT
    if isinstance(exc, AITransientError):
        return FailureCategory.TEMPORARY_FAILURE
    if isinstance(exc, AIRateLimitError):
        return FailureCategory.RATE_LIMITED
    if isinstance(exc, AIAuthenticationError):
        return FailureCategory.AUTHENTICATION_FAILURE
    if isinstance(exc, AIConfigurationError):
        return FailureCategory.CONFIGURATION_ERROR
    if isinstance(exc, AIInvalidResponseError):
        return FailureCategory.INVALID_RESPONSE
    if isinstance(exc, AIUnsupportedProviderError):
        return FailureCategory.UNSUPPORTED_CAPABILITY
    if isinstance(exc, AIPermanentProcessingError):
        return FailureCategory.PERMANENT_PROCESSING_ERROR
    return FailureCategory.TEMPORARY_FAILURE


def counts_toward_circuit(category: FailureCategory) -> bool:
    """Return True if the failure category should count toward opening the circuit."""
    return category not in {
        FailureCategory.CONFIGURATION_ERROR,
        FailureCategory.UNSUPPORTED_CAPABILITY,
        FailureCategory.PERMANENT_PROCESSING_ERROR,
        FailureCategory.INVALID_REQUEST,
    }


def allows_fallback(category: FailureCategory) -> bool:
    """Return True if the failure category should trigger fallback to another provider."""
    return True


__all__ = [
    "CircuitBreakerPolicy",
    "CircuitState",
    "FailureCategory",
    "ProviderHealthState",
    "classify_failure",
    "counts_toward_circuit",
    "utc_now",
]
