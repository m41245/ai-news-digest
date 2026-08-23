"""Unit tests for email error hierarchy."""

from __future__ import annotations

import pytest

from ai_news_digest.core.exceptions import ExternalServiceError
from ai_news_digest.infrastructure.email.errors import (
    EmailAuthenticationError,
    EmailConfigurationError,
    EmailConnectionError,
    EmailError,
    EmailInvalidRecipientError,
    EmailPermanentFailureError,
    EmailRateLimitError,
    EmailTimeoutError,
)


def test_email_error_is_external_service_error() -> None:
    exc = EmailError("test")
    assert isinstance(exc, ExternalServiceError)


def test_email_authentication_error() -> None:
    exc = EmailAuthenticationError("bad creds")
    assert isinstance(exc, EmailError)
    assert str(exc) == "bad creds"


def test_email_configuration_error() -> None:
    exc = EmailConfigurationError("missing host")
    assert isinstance(exc, EmailError)
    assert str(exc) == "missing host"


def test_email_connection_error() -> None:
    exc = EmailConnectionError("connection reset")
    assert isinstance(exc, EmailError)
    assert str(exc) == "connection reset"


def test_email_timeout_error() -> None:
    exc = EmailTimeoutError("timed out")
    assert isinstance(exc, EmailError)
    assert str(exc) == "timed out"


def test_email_rate_limit_error() -> None:
    exc = EmailRateLimitError("rate limited")
    assert isinstance(exc, EmailError)
    assert str(exc) == "rate limited"


def test_email_invalid_recipient_error() -> None:
    exc = EmailInvalidRecipientError("bad address")
    assert isinstance(exc, EmailError)
    assert str(exc) == "bad address"


def test_email_permanent_failure_error() -> None:
    exc = EmailPermanentFailureError("permanent reject")
    assert isinstance(exc, EmailError)
    assert str(exc) == "permanent reject"


def test_email_error_catch_as_external_service_error() -> None:
    with pytest.raises(ExternalServiceError):
        raise EmailConnectionError("boom")


def test_email_error_catch_as_email_error() -> None:
    with pytest.raises(EmailError):
        raise EmailInvalidRecipientError("boom")


def test_email_errors_are_distinct() -> None:
    errors = [
        EmailAuthenticationError,
        EmailConfigurationError,
        EmailConnectionError,
        EmailTimeoutError,
        EmailRateLimitError,
        EmailInvalidRecipientError,
        EmailPermanentFailureError,
    ]
    assert len(set(errors)) == len(errors)


__all__ = [
    "test_email_authentication_error",
    "test_email_configuration_error",
    "test_email_connection_error",
    "test_email_error_catch_as_email_error",
    "test_email_error_catch_as_external_service_error",
    "test_email_error_is_external_service_error",
    "test_email_errors_are_distinct",
    "test_email_invalid_recipient_error",
    "test_email_permanent_failure_error",
    "test_email_rate_limit_error",
    "test_email_timeout_error",
]
