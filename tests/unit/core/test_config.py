"""
Unit tests for core config module.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ai_news_digest.core.config import Settings, get_settings, settings


def test_settings_default_values() -> None:
    """Test Settings with default values."""
    test_settings = Settings(
        database_url="postgresql://test",
        redis_url="redis://test",
        celery_broker_url="redis://broker",
        celery_result_backend="redis://backend",
    )

    assert test_settings.app_name == "AI News Digest"
    assert test_settings.app_version == "0.1.0"
    assert test_settings.environment == "development"
    assert test_settings.debug is False
    assert test_settings.api_prefix == "/api/v1"


def test_settings_custom_values() -> None:
    """Test Settings with custom values."""
    test_settings = Settings(
        database_url="postgresql://test",
        redis_url="redis://test",
        celery_broker_url="redis://broker",
        celery_result_backend="redis://backend",
        app_name="Custom App",
        app_version="1.0.0",
        environment="production",
        debug=True,
    )

    assert test_settings.app_name == "Custom App"
    assert test_settings.app_version == "1.0.0"
    assert test_settings.environment == "production"
    assert test_settings.debug is True


def test_settings_environment_validation() -> None:
    """Test that environment must be a valid literal."""
    with pytest.raises(ValidationError):
        Settings(
            database_url="postgresql://test",
            redis_url="redis://test",
            celery_broker_url="redis://broker",
            celery_result_backend="redis://backend",
            environment="invalid",
        )


def test_settings_rss_timeout_validation() -> None:
    """Test RSS timeout validation."""
    with pytest.raises(ValidationError):
        Settings(
            database_url="postgresql://test",
            redis_url="redis://test",
            celery_broker_url="redis://broker",
            celery_result_backend="redis://backend",
            rss_request_timeout=0,  # Must be >= 1
        )


def test_settings_rss_timeout_max_validation() -> None:
    """Test RSS timeout max validation."""
    with pytest.raises(ValidationError):
        Settings(
            database_url="postgresql://test",
            redis_url="redis://test",
            celery_broker_url="redis://broker",
            celery_result_backend="redis://backend",
            rss_request_timeout=121,  # Must be <= 120
        )


def test_settings_digest_schedule_hour_validation() -> None:
    """Test digest schedule hour validation."""
    with pytest.raises(ValidationError):
        Settings(
            database_url="postgresql://test",
            redis_url="redis://test",
            celery_broker_url="redis://broker",
            celery_result_backend="redis://backend",
            digest_schedule_hour=24,  # Must be <= 23
        )


def test_settings_digest_schedule_minute_validation() -> None:
    """Test digest schedule minute validation."""
    with pytest.raises(ValidationError):
        Settings(
            database_url="postgresql://test",
            redis_url="redis://test",
            celery_broker_url="redis://broker",
            celery_result_backend="redis://backend",
            digest_schedule_minute=60,  # Must be <= 59
        )


def test_settings_smtp_port_validation() -> None:
    """Test SMTP port validation."""
    with pytest.raises(ValidationError):
        Settings(
            database_url="postgresql://test",
            redis_url="redis://test",
            celery_broker_url="redis://broker",
            celery_result_backend="redis://backend",
            smtp_port=0,  # Must be >= 1
        )


def test_settings_log_level_validation() -> None:
    """Test log level validation."""
    with pytest.raises(ValidationError):
        Settings(
            database_url="postgresql://test",
            redis_url="redis://test",
            celery_broker_url="redis://broker",
            celery_result_backend="redis://backend",
            log_level="INVALID",
        )


def test_settings_default_llm_provider_validation() -> None:
    """Test default LLM provider validation."""
    with pytest.raises(ValidationError):
        Settings(
            database_url="postgresql://test",
            redis_url="redis://test",
            celery_broker_url="redis://broker",
            celery_result_backend="redis://backend",
            default_llm_provider="invalid",
        )


def test_settings_email_recipients_default_factory() -> None:
    """Test email recipients default factory."""
    test_settings = Settings(
        database_url="postgresql://test",
        redis_url="redis://test",
        celery_broker_url="redis://broker",
        celery_result_backend="redis://backend",
    )

    assert test_settings.email_recipients == []


def test_settings_email_recipients_custom() -> None:
    """Test email recipients with custom values."""
    test_settings = Settings(
        database_url="postgresql://test",
        redis_url="redis://test",
        celery_broker_url="redis://broker",
        celery_result_backend="redis://backend",
        email_recipients=["test@example.com", "test2@example.com"],
    )

    assert len(test_settings.email_recipients) == 2
    assert "test@example.com" in test_settings.email_recipients


def test_settings_frozen() -> None:
    """Test that Settings is frozen (immutable)."""
    test_settings = Settings(
        database_url="postgresql://test",
        redis_url="redis://test",
        celery_broker_url="redis://broker",
        celery_result_backend="redis://backend",
    )

    with pytest.raises(ValidationError):  # FrozenInstanceError
        test_settings.app_name = "New Name"


def test_get_settings_cached() -> None:
    """Test that get_settings returns cached instance."""
    settings1 = get_settings()
    settings2 = get_settings()

    assert settings1 is settings2


def test_settings_instance_exists() -> None:
    """Test that global settings instance exists."""
    assert settings is not None
    assert isinstance(settings, Settings)
