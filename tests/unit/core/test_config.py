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
        jwt_secret_key="a" * 64,
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


def test_jwt_secret_rejects_weak_defaults() -> None:
    """Test that JWT secret rejects known weak defaults in production."""
    weak_secrets = [
        "change-me",
        "changeme",
        "secret",
        "dev-secret-key-change-me-in-production",
        "replace-me-with-a-secure-random-string-at-least-32-chars",
        "your-secret-key-here",
        "insecure",
        "password",
        "12345678901234567890123456789012",
    ]
    for weak_secret in weak_secrets:
        with pytest.raises(ValidationError, match="JWT_SECRET_KEY must be set to a secure value"):
            Settings(
                database_url="postgresql://test",
                redis_url="redis://test",
                celery_broker_url="redis://broker",
                celery_result_backend="redis://backend",
                environment="production",
                jwt_secret_key=weak_secret,
            )


def test_jwt_secret_rejects_placeholder_patterns() -> None:
    """Test that JWT secret rejects placeholder patterns in production."""
    placeholder_secrets = [
        "change_me_to_a_secure_random_key_at_least_32_chars",
        "changeme_to_a_secure_random_key_at_least_32_chars",
        "change-me-to-a-secure-random-key-at-least-32-chars",
        "replace-me-with-a-secure-random-key-at-least-32-chars",
        "replace_me_with_a_secure_random_key_at_least_32_chars",
        "please-replace-with-openssl-rand-hex-32-in-production",
        "please-replace-with-openssl-rand-hex-32",
        "test-secret-key-for-local-verification-only",
        "test_secret_key_for_local_verification_only",
        "placeholder-jwt-secret-key-for-testing-purposes",
        "your-secret-key-here-for-production",
        "your_secret_key_here_for_production",
        "dev-secret-key-for-testing-only",
        "dev_secret_key_for_testing_only",
        "please-replace-with-a-secure-random-string-at-least-32-chars",
        "do-not-use-in-production-key-1234567890123456789012",
        "local-prod-verification-key-123456789012345678901234",
        "local-dev-fake-key-not-for-production-use-only-1234567890",
        "fake-key-for-testing-not-secure-enough-at-all-yes",
    ]
    for placeholder in placeholder_secrets:
        with pytest.raises(ValidationError, match="JWT_SECRET_KEY must be set to a secure value"):
            Settings(
                database_url="postgresql://test",
                redis_url="redis://test",
                celery_broker_url="redis://broker",
                celery_result_backend="redis://backend",
                environment="production",
                jwt_secret_key=placeholder,
            )


def test_jwt_secret_rejects_short_values() -> None:
    """Test that JWT secret rejects values shorter than 32 characters in production."""
    with pytest.raises(ValidationError, match="at least 32 characters long"):
        Settings(
            database_url="postgresql://test",
            redis_url="redis://test",
            celery_broker_url="redis://broker",
            celery_result_backend="redis://backend",
            environment="production",
            jwt_secret_key="short-secret-key",  # noqa: S106 - intentional weak secret for test
        )


def test_jwt_secret_accepts_placeholder_in_development() -> None:
    """Placeholder secrets are accepted in development mode for convenience."""
    dev_secrets = [
        "REPLACE_ME_WITH_A_SECURE_RANDOM_KEY_AT_LEAST_32_CHARS",
        "replace_me_with_a_secure_random_key_at_least_32_chars",
        "change-me",
        "please-replace-with-openssl-rand-hex-32-in-production",
        "please-replace-with-openssl-rand-hex-32",
        "short",
    ]
    for dev_secret in dev_secrets:
        test_settings = Settings(
            database_url="postgresql://test",
            redis_url="redis://test",
            celery_broker_url="redis://broker",
            celery_result_backend="redis://backend",
            environment="development",
            jwt_secret_key=dev_secret,
        )
        assert test_settings.jwt_secret_key == dev_secret


def test_jwt_secret_rejects_env_example_placeholder_in_production() -> None:
    """The .env.example placeholder must be rejected in production/staging/testing."""
    env_example_placeholders = [
        "please-replace-with-openssl-rand-hex-32-in-production",
        "please-replace-with-openssl-rand-hex-32",
    ]
    for placeholder in env_example_placeholders:
        with pytest.raises(ValidationError, match="JWT_SECRET_KEY must be set to a secure value"):
            Settings(
                database_url="postgresql://test",
                redis_url="redis://test",
                celery_broker_url="redis://broker",
                celery_result_backend="redis://backend",
                environment="production",
                jwt_secret_key=placeholder,
            )


def test_jwt_secret_accepts_strong_random_value() -> None:
    """Test that JWT secret accepts a strong random value."""
    strong_secret = "a" * 64
    test_settings = Settings(
        database_url="postgresql://test",
        redis_url="redis://test",
        jwt_secret_key=strong_secret,
    )
    assert test_settings.jwt_secret_key == strong_secret
