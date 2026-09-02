"""
Unit tests for core logging module.
"""

from __future__ import annotations

import structlog

from ai_news_digest.core.logging import (
    _redact_string,
    add_service_and_environment,
    configure_logging,
    get_logger,
    redact_sensitive_data,
)


def test_configure_logging() -> None:
    configure_logging()

    # Should not raise any exceptions


def test_get_logger() -> None:
    configure_logging()

    logger = get_logger("test_logger")

    assert logger is not None
    assert logger.name == "test_logger"


def test_get_logger_different_names() -> None:
    configure_logging()

    logger1 = get_logger("logger1")
    logger2 = get_logger("logger2")

    assert logger1.name == "logger1"
    assert logger2.name == "logger2"


def test_redact_sensitive_data_redacts_keys() -> None:
    event_dict = {
        "event": "test",
        "password": "secret123",
        "api_key": "key123",
        "normal_field": "safe_value",
    }
    result = redact_sensitive_data(None, None, event_dict)
    assert result["password"] == "***REDACTED***"  # noqa: S105
    assert result["api_key"] == "***REDACTED***"
    assert result["normal_field"] == "safe_value"


def test_redact_sensitive_data_redacts_event_string() -> None:
    event_dict = {"event": "password=secret123 in request"}
    result = redact_sensitive_data(None, None, event_dict)
    assert "secret123" not in result["event"]
    assert "***REDACTED***" in result["event"]


def test_redact_sensitive_data_redacts_authorization_token() -> None:
    event_dict = {
        "event": "api call",
        "Authorization": "Bearer token123",
    }
    result = redact_sensitive_data(None, None, event_dict)
    assert "token123" not in result["Authorization"]
    assert result["Authorization"] == "***REDACTED***"


def test_redact_string_redacts_patterns() -> None:
    assert "secret123" not in _redact_string("password=secret123")
    assert "key123" not in _redact_string("api_key=key123")
    assert "token123" not in _redact_string("Authorization: token123")
    assert "pass123" not in _redact_string("db_password=pass123")
    assert "smtppass" not in _redact_string("smtp_password=smtppass")


def test_redact_string_preserves_safe_text() -> None:
    text = "user logged in successfully"
    assert _redact_string(text) == text


def test_add_service_and_environment_adds_fields() -> None:
    event_dict = {"event": "test"}
    result = add_service_and_environment(None, None, event_dict)
    assert result["service"] == "ai-news-digest"
    assert "environment" in result


def test_add_service_and_environment_does_not_overwrite() -> None:
    event_dict = {"event": "test", "service": "custom", "environment": "prod"}
    result = add_service_and_environment(None, None, event_dict)
    assert result["service"] == "custom"
    assert result["environment"] == "prod"


def test_configure_logging_binds_contextvars() -> None:
    configure_logging()
    structlog.contextvars.bind_contextvars(request_id="test-123")
    try:
        logger = get_logger("test_contextvars")
        logger.info("test_event", key="value")
    finally:
        structlog.contextvars.clear_contextvars()
