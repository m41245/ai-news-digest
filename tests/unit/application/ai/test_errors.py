"""
Unit tests for the AI error model.
"""

from __future__ import annotations

import pytest

from ai_news_digest.application.ai.errors import (
    AIAuthenticationError,
    AIConfigurationError,
    AIError,
    AIInvalidResponseError,
    AIPermanentProcessingError,
    AIRateLimitError,
    AITimeoutError,
    AITransientError,
    AIUnsupportedProviderError,
)
from ai_news_digest.core.exceptions import ExternalServiceError


def test_ai_error_inherits_from_external_service_error() -> None:
    """AI errors remain catchable as ExternalServiceError for backward compat."""
    assert issubclass(AIError, ExternalServiceError)


@pytest.mark.parametrize(
    "error_class",
    [
        AIError,
        AIConfigurationError,
        AIAuthenticationError,
        AIRateLimitError,
        AITimeoutError,
        AITransientError,
        AIInvalidResponseError,
        AIUnsupportedProviderError,
        AIPermanentProcessingError,
    ],
)
def test_all_ai_errors_inherit_from_ai_error(error_class: type) -> None:
    """Every concrete AI error is a subclass of AIError."""
    assert issubclass(error_class, AIError)


def test_errors_preserve_message() -> None:
    """The error message is preserved."""
    err = AIRateLimitError("rate limited")
    assert err.message == "rate limited"
    assert str(err) == "rate limited"


def test_errors_support_details() -> None:
    """Errors support structured details."""
    err = AIConfigurationError("bad config", details={"field": "api_key"})
    assert err.details == {"field": "api_key"}


def test_transient_error_is_retriable_classification() -> None:
    """AITransientError is the only class marked for retry."""
    from ai_news_digest.application.ai.retry import _is_transient

    assert _is_transient(AITransientError("boom")) is True
    assert _is_transient(AIAuthenticationError("boom")) is False
    assert _is_transient(AIRateLimitError("boom")) is False
    assert _is_transient(AITimeoutError("boom")) is False
    assert _is_transient(AIInvalidResponseError("boom")) is False
    assert _is_transient(AIConfigurationError("boom")) is False
    assert _is_transient(AIPermanentProcessingError("boom")) is False
    assert _is_transient(RuntimeError("boom")) is False
