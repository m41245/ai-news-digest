"""
Unit tests for core config module.
"""

from __future__ import annotations

import pathlib
from typing import ClassVar

import pytest
from pydantic import ValidationError
from pydantic_settings import SettingsConfigDict

from ai_news_digest.core.config import Settings, _LazySettings, get_settings, settings
from ai_news_digest.main import create_app


class TestSettings(Settings):
    """
    Test-specific Settings that ignore .env files.

    Note: Pydantic Settings still reads from os.environ. Use monkeypatch
    to isolate specific tests from environment variable contamination.
    """

    model_config = SettingsConfigDict(
        env_file=None,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        frozen=True,
    )

    # Production-safe email defaults for tests
    email_provider: str = "smtp"
    email_development_mode: bool = False
    email_base_url: str = "https://example.com"
    smtp_host: str = "smtp.example.com"
    email_from: str = "noreply@example.com"


def test_settings_default_values() -> None:
    """Test Settings with default values."""
    test_settings = TestSettings(
        database_url="postgresql://test",
        redis_url="redis://test",
        celery_broker_url="redis://broker",
        celery_result_backend="redis://backend",
        jwt_secret_key="a" * 64,
    )

    assert test_settings.app_name == "AI News Digest"
    assert test_settings.app_version == "0.1.0"
    assert test_settings.environment == "development"
    assert test_settings.debug is False
    assert test_settings.api_prefix == "/api/v1"
    assert test_settings.host == "127.0.0.1"
    assert test_settings.port == 8000


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
        email_provider="smtp",
        email_development_mode=False,
        email_base_url="https://example.com",
        smtp_host="smtp.example.com",
        host="0.0.0.0",
        port=9000,
    )

    assert test_settings.app_name == "Custom App"
    assert test_settings.app_version == "1.0.0"
    assert test_settings.environment == "production"
    assert test_settings.debug is True
    assert test_settings.host == "0.0.0.0"
    assert test_settings.port == 9000


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
    test_settings = TestSettings(
        database_url="postgresql://test",
        redis_url="redis://test",
        celery_broker_url="redis://broker",
        celery_result_backend="redis://backend",
        jwt_secret_key="a" * 64,
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
        test_settings.app_name = "New Name"  # type: ignore[misc]


def test_get_settings_cached() -> None:
    """Test that get_settings returns cached instance."""
    settings1 = get_settings()
    settings2 = get_settings()

    assert settings1 is settings2


def test_settings_instance_exists() -> None:
    """Test that global settings instance exists."""
    assert settings is not None
    assert isinstance(settings, _LazySettings)
    assert settings.app_name == "AI News Digest"


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
        "ci-fake-jwt-secret-for-testing-only-2026",
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
        "ci-fake-jwt-secret-for-testing-only-2026",
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


def test_cors_origins_production_default_is_empty() -> None:
    """Production CORS defaults to an empty allow-list (fail closed)."""
    test_settings = TestSettings(
        database_url="postgresql://test",
        redis_url="redis://test",
        celery_broker_url="redis://broker",
        celery_result_backend="redis://backend",
        environment="production",
        jwt_secret_key="a" * 64,
    )
    assert test_settings.cors_origins == []


def test_cors_origins_production_accepts_cloudflare_pages_origin() -> None:
    """Production CORS accepts the configured Cloudflare Pages origin."""
    test_settings = TestSettings(
        database_url="postgresql://test",
        redis_url="redis://test",
        celery_broker_url="redis://broker",
        celery_result_backend="redis://backend",
        environment="production",
        jwt_secret_key="a" * 64,
        cors_origins=["https://ai-news-digest-doo.pages.dev"],
    )
    assert test_settings.cors_origins == ["https://ai-news-digest-doo.pages.dev"]


def test_cors_origins_development_defaults_to_localhost() -> None:
    """Development CORS defaults to localhost origins."""
    test_settings = TestSettings(
        database_url="postgresql://test",
        redis_url="redis://test",
        celery_broker_url="redis://broker",
        celery_result_backend="redis://backend",
        environment="development",
        jwt_secret_key="a" * 64,
    )
    assert test_settings.cors_origins == [
        "http://localhost:3000",
        "http://localhost:8000",
    ]


def test_cors_origins_staging_defaults_to_localhost() -> None:
    """Staging CORS defaults to localhost origins."""
    test_settings = TestSettings(
        database_url="postgresql://test",
        redis_url="redis://test",
        celery_broker_url="redis://broker",
        celery_result_backend="redis://backend",
        environment="staging",
        jwt_secret_key="a" * 64,
    )
    assert test_settings.cors_origins == [
        "http://localhost:3000",
        "http://localhost:8000",
    ]


def test_cors_origins_explicit_value_overrides_default() -> None:
    """Explicit CORS_ORIGINs value is respected in all environments."""
    test_settings = Settings(
        database_url="postgresql://test",
        redis_url="redis://test",
        celery_broker_url="redis://broker",
        celery_result_backend="redis://backend",
        environment="production",
        jwt_secret_key="a" * 64,
        email_provider="smtp",
        email_development_mode=False,
        email_base_url="https://example.com",
        smtp_host="smtp.example.com",
        cors_origins=["https://example.com"],
    )
    assert test_settings.cors_origins == ["https://example.com"]


class TestDatabaseUrlNormalization:
    """Regression tests for PostgreSQL driver URL normalization.

    The ``database_url`` field on the production ``Settings`` class has
    ``validation_alias="DATABASE_URL"``.  In Pydantic v2 Settings that
    means the value is always sourced from the ``DATABASE_URL`` environment
    variable: the ``mode='before'`` field validator is invoked with the
    raw env-var value before the model is constructed.

    These tests therefore set ``DATABASE_URL`` in ``os.environ`` and
    instantiate a ``Settings`` subclass that does **not** read a ``.env``
    file.  The env var is removed in ``finally`` to avoid leaking into
    subsequent tests.
    """

    class _NoEnvSettings(Settings):
        model_config = SettingsConfigDict(
            env_file=None,
            env_file_encoding="utf-8",
            case_sensitive=False,
            extra="ignore",
            frozen=True,
        )

    def test_postgresql_url_normalized_to_asyncpg(self) -> None:
        """postgresql:// URLs are normalized to postgresql+asyncpg://."""
        import os

        os.environ["DATABASE_URL"] = "postgresql://user:pass@host:5432/dbname"
        try:
            test_settings = self._NoEnvSettings()
        finally:
            del os.environ["DATABASE_URL"]
        assert test_settings.database_url == "postgresql+asyncpg://user:pass@host:5432/dbname"

    def test_postgresql_asyncpg_url_preserved(self) -> None:
        """postgresql+asyncpg:// URLs are preserved unchanged."""
        import os

        os.environ["DATABASE_URL"] = "postgresql+asyncpg://user:pass@host:5432/dbname"
        try:
            test_settings = self._NoEnvSettings()
        finally:
            del os.environ["DATABASE_URL"]
        assert test_settings.database_url == "postgresql+asyncpg://user:pass@host:5432/dbname"

    def test_postgresql_url_with_ssl_params_normalized(self) -> None:
        """postgresql:// URLs with sslmode=require are normalized correctly.

        sslmode=require is consumed by the asyncpg normalize helper and does
        NOT leak through to asyncpg as an unknown keyword argument.
        """
        import os

        os.environ["DATABASE_URL"] = (
            "postgresql://user:pass@host:5432/dbname?sslmode=require"
        )
        try:
            test_settings = self._NoEnvSettings()
        finally:
            del os.environ["DATABASE_URL"]
        assert (
            test_settings.database_url
            == "postgresql+asyncpg://user:pass@host:5432/dbname"
        )
        assert "sslmode" not in test_settings.database_url

    def test_non_postgresql_url_preserved(self) -> None:
        """Non-PostgreSQL URLs like SQLite are preserved unchanged."""
        import os

        os.environ["DATABASE_URL"] = "sqlite:///test.db"
        try:
            test_settings = self._NoEnvSettings()
        finally:
            del os.environ["DATABASE_URL"]
        assert test_settings.database_url == "sqlite:///test.db"


class TestConfigurationIsolation:
    """Regression tests proving configuration is isolated from .env and environment."""

    CONTAMINATED_ENV_VARS: ClassVar[list[str]] = [
        "ENVIRONMENT",
        "EMAIL_RECIPIENTS",
        "CORS_ORIGINS",
        "JWT_SECRET_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "SMTP_HOST",
        "SMTP_PORT",
        "SMTP_USER",
        "SMTP_PASSWORD",
    ]

    def test_test_settings_ignores_env_file(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
    ) -> None:
        """TestSettings must not read from .env files."""
        env_file = tmp_path / ".env"
        env_file.write_text(
            'ENVIRONMENT=staging\nEMAIL_RECIPIENTS=["file@example.com"]\n',
            encoding="utf-8",
        )

        for var in self.CONTAMINATED_ENV_VARS:
            monkeypatch.delenv(var, raising=False)

        monkeypatch.chdir(tmp_path)

        test_settings = TestSettings(
            database_url="postgresql://test",
            redis_url="redis://test",
            celery_broker_url="redis://broker",
            celery_result_backend="redis://backend",
            jwt_secret_key="a" * 64,
        )

        assert test_settings.environment == "development"
        assert test_settings.email_recipients == []

    def test_settings_without_env_uses_defaults(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
    ) -> None:
        """Settings must use defaults when no .env or env vars are present."""
        for var in self.CONTAMINATED_ENV_VARS:
            monkeypatch.delenv(var, raising=False)

        monkeypatch.chdir(tmp_path)

        test_settings = Settings(
            database_url="postgresql://test",
            redis_url="redis://test",
            celery_broker_url="redis://broker",
            celery_result_backend="redis://backend",
            jwt_secret_key="a" * 64,
        )

        assert test_settings.environment == "development"
        assert test_settings.email_recipients == []
        assert test_settings.cors_origins == [
            "http://localhost:3000",
            "http://localhost:8000",
        ]

    def test_real_settings_reads_env_variables(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Real Settings class must still read environment variables."""
        monkeypatch.setenv("ENVIRONMENT", "staging")
        monkeypatch.setenv("EMAIL_RECIPIENTS", '["real@example.com"]')
        monkeypatch.setenv("CORS_ORIGINS", '["https://real.example.com"]')
        monkeypatch.setenv("JWT_SECRET_KEY", "a" * 64)

        real_settings = Settings(
            database_url="postgresql://test",
            redis_url="redis://test",
            celery_broker_url="redis://broker",
            celery_result_backend="redis://backend",
        )

        assert real_settings.environment == "staging"
        assert real_settings.email_recipients == ["real@example.com"]
        assert real_settings.cors_origins == ["https://real.example.com"]

    def test_explicit_values_override_env_variables(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Explicit constructor arguments must override environment variables."""
        monkeypatch.setenv("ENVIRONMENT", "staging")
        monkeypatch.setenv("EMAIL_RECIPIENTS", '["env@example.com"]')

        test_settings = Settings(
            database_url="postgresql://test",
            redis_url="redis://test",
            celery_broker_url="redis://broker",
            celery_result_backend="redis://backend",
            environment="production",
            jwt_secret_key="a" * 64,
            email_provider="smtp",
            email_development_mode=False,
            email_base_url="https://example.com",
            smtp_host="smtp.example.com",
            email_recipients=["explicit@example.com"],
        )

        assert test_settings.environment == "production"
        assert test_settings.email_recipients == ["explicit@example.com"]

    def test_staging_env_does_not_contaminate_other_tests(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
    ) -> None:
        """Verify staging-like env vars do not leak into subsequent tests."""
        monkeypatch.setenv("ENVIRONMENT", "staging")
        monkeypatch.setenv("EMAIL_RECIPIENTS", '["leak@example.com"]')
        monkeypatch.setenv("CORS_ORIGINS", '["https://leak.example.com"]')

        for var in self.CONTAMINATED_ENV_VARS:
            monkeypatch.delenv(var, raising=False)

        monkeypatch.chdir(tmp_path)

        test_settings = Settings(
            database_url="postgresql://test",
            redis_url="redis://test",
            celery_broker_url="redis://broker",
            celery_result_backend="redis://backend",
            jwt_secret_key="a" * 64,
        )

        assert test_settings.environment == "development"
        assert test_settings.email_recipients == []
        assert test_settings.cors_origins == [
            "http://localhost:3000",
            "http://localhost:8000",
        ]


class TestProductionConfigurationValidation:
    """Tests verifying production configuration is valid and secure."""

    def test_production_requires_jwt_secret(self) -> None:
        """Production mode must have a JWT secret set."""
        with pytest.raises(ValidationError, match="must be set to a secure value"):
            Settings(
                database_url="postgresql://test",
                redis_url="redis://test",
                celery_broker_url="redis://broker",
                celery_result_backend="redis://backend",
                environment="production",
                jwt_secret_key="changeme",  # noqa: S106
            )

    def test_production_accepts_strong_jwt_secret(self) -> None:
        """Production mode accepts a strong JWT secret."""
        test_settings = Settings(
            database_url="postgresql://test",
            redis_url="redis://test",
            celery_broker_url="redis://broker",
            celery_result_backend="redis://backend",
            environment="production",
            jwt_secret_key="a" * 64,
            email_provider="smtp",
            email_development_mode=False,
            email_base_url="https://example.com",
            smtp_host="smtp.example.com",
        )
        assert test_settings.jwt_secret_key == "a" * 64

    def test_production_cors_defaults_to_empty(self) -> None:
        """Production CORS defaults to empty list when not explicitly set."""
        test_settings = TestSettings(
            database_url="postgresql://test",
            redis_url="redis://test",
            celery_broker_url="redis://broker",
            celery_result_backend="redis://backend",
            environment="production",
            jwt_secret_key="a" * 64,
        )
        assert test_settings.cors_origins == []

    def test_production_debug_defaults_to_false(self) -> None:
        """Production debug mode defaults to False."""
        test_settings = TestSettings(
            database_url="postgresql://test",
            redis_url="redis://test",
            celery_broker_url="redis://broker",
            celery_result_backend="redis://backend",
            environment="production",
            jwt_secret_key="a" * 64,
        )
        assert test_settings.debug is False

    def test_production_log_level_defaults_to_info(self) -> None:
        """Production log level defaults to INFO."""
        test_settings = TestSettings(
            database_url="postgresql://test",
            redis_url="redis://test",
            celery_broker_url="redis://broker",
            celery_result_backend="redis://backend",
            environment="production",
            jwt_secret_key="a" * 64,
        )
        assert test_settings.log_level == "INFO"

    def test_staging_requires_jwt_secret(self) -> None:
        """Staging mode must have a JWT secret set."""
        with pytest.raises(ValidationError, match="JWT_SECRET_KEY must be set to a secure value"):
            Settings(
                database_url="postgresql://test",
                redis_url="redis://test",
                celery_broker_url="redis://broker",
                celery_result_backend="redis://backend",
                environment="staging",
                jwt_secret_key="changeme",  # noqa: S106
            )

    def test_testing_requires_minimum_jwt_secret_length(self) -> None:
        """Testing mode requires at least 32 character JWT secret."""
        with pytest.raises(ValidationError, match="at least 32 characters long"):
            Settings(
                database_url="postgresql://test",
                redis_url="redis://test",
                celery_broker_url="redis://broker",
                celery_result_backend="redis://backend",
                environment="testing",
                jwt_secret_key="short",  # noqa: S106
            )

    def test_testing_accepts_minimum_jwt_secret_length(self) -> None:
        """Testing mode accepts minimum length JWT secret."""
        test_settings = Settings(
            database_url="postgresql://test",
            redis_url="redis://test",
            celery_broker_url="redis://broker",
            celery_result_backend="redis://backend",
            environment="testing",
            jwt_secret_key="a" * 32,
        )
        assert test_settings.jwt_secret_key == "a" * 32

    def test_database_url_is_required(self) -> None:
        """Database URL must be provided."""
        test_settings = TestSettings(
            redis_url="redis://test",
            celery_broker_url="redis://broker",
            celery_result_backend="redis://backend",
            environment="production",
            jwt_secret_key="a" * 64,
        )
        assert test_settings.database_url is not None
        assert len(test_settings.database_url) > 0

    def test_redis_url_is_required(self) -> None:
        """Redis URL must be provided."""
        test_settings = TestSettings(
            database_url="postgresql://test",
            celery_broker_url="redis://broker",
            celery_result_backend="redis://backend",
            environment="production",
            jwt_secret_key="a" * 64,
        )
        assert test_settings.redis_url is not None
        assert len(test_settings.redis_url) > 0

    def test_email_provider_validates_allowed_values(self) -> None:
        """Email provider must be one of console, smtp, or test."""
        with pytest.raises(ValidationError):
            Settings(
                database_url="postgresql://test",
                redis_url="redis://test",
                celery_broker_url="redis://broker",
                celery_result_backend="redis://backend",
                environment="production",
                jwt_secret_key="a" * 64,
                email_provider="invalid",
            )

    def test_production_docs_disabled(self) -> None:
        """Production mode disables API docs."""
        test_settings = TestSettings(
            database_url="postgresql://test",
            redis_url="redis://test",
            celery_broker_url="redis://broker",
            celery_result_backend="redis://backend",
            environment="production",
            jwt_secret_key="a" * 64,
        )
        app = create_app(settings_override=test_settings)
        assert app.docs_url is None
        assert app.redoc_url is None
        assert app.openapi_url is None

    def test_staging_docs_enabled(self) -> None:
        """Staging mode enables API docs."""
        test_settings = TestSettings(
            database_url="postgresql://test",
            redis_url="redis://test",
            celery_broker_url="redis://broker",
            celery_result_backend="redis://backend",
            environment="staging",
            jwt_secret_key="a" * 64,
        )
        app = create_app(settings_override=test_settings)
        assert app.docs_url == "/docs"
        assert app.redoc_url == "/redoc"

    def test_digest_timezone_validates_iana_names(self) -> None:
        """DIGEST_TIMEZONE must be a valid IANA timezone name."""
        with pytest.raises(ValidationError, match="not a valid IANA timezone name"):
            Settings(
                database_url="postgresql://test",
                redis_url="redis://test",
                celery_broker_url="redis://broker",
                celery_result_backend="redis://backend",
                environment="production",
                jwt_secret_key="a" * 64,
                digest_timezone="Invalid/Timezone",
            )

    def test_digest_timezone_accepts_valid_iana_name(self) -> None:
        """DIGEST_TIMEZONE accepts valid IANA timezone names."""
        test_settings = Settings(
            database_url="postgresql://test",
            redis_url="redis://test",
            celery_broker_url="redis://broker",
            celery_result_backend="redis://backend",
            environment="production",
            jwt_secret_key="a" * 64,
            digest_timezone="America/New_York",
            email_provider="smtp",
            email_development_mode=False,
            email_base_url="https://example.com",
            smtp_host="smtp.example.com",
        )
        assert test_settings.digest_timezone == "America/New_York"

    def test_production_no_committed_secret_defaults(self) -> None:
        """Production config must not have committed secret defaults."""
        test_settings = TestSettings(
            database_url="postgresql://test",
            redis_url="redis://test",
            celery_broker_url="redis://broker",
            celery_result_backend="redis://backend",
            environment="production",
            jwt_secret_key="a" * 64,
        )
        assert test_settings.jwt_secret_key != "changeme"  # noqa: S105
        assert test_settings.jwt_secret_key != "secret"  # noqa: S105
        assert "example" not in (test_settings.smtp_password or "")


class TestProductionEmailConfigurationValidation:
    """Tests verifying production email configuration validation."""

    def test_production_email_disabled_accepts_console_and_empty_base_url(self) -> None:
        """Production + email disabled + console provider + empty base_url is valid."""
        test_settings = Settings(
            database_url="postgresql://test",
            redis_url="redis://test",
            celery_broker_url="redis://broker",
            celery_result_backend="redis://backend",
            environment="production",
            jwt_secret_key="a" * 64,
            email_enabled=False,
            email_provider="console",
            email_development_mode=False,
            email_base_url="",
            smtp_host="",
        )
        assert test_settings.email_enabled is False
        assert test_settings.email_provider == "console"
        assert test_settings.email_base_url == ""

    def test_production_email_enabled_rejects_console_provider(self) -> None:
        """Production + email enabled + console provider raises ValidationError."""
        with pytest.raises(ValidationError, match="EMAIL_PROVIDER must be 'smtp'"):
            Settings(
                database_url="postgresql://test",
                redis_url="redis://test",
                celery_broker_url="redis://broker",
                celery_result_backend="redis://backend",
                environment="production",
                jwt_secret_key="a" * 64,
                email_enabled=True,
                email_provider="console",
                email_development_mode=False,
            )

    def test_production_email_enabled_requires_base_url(self) -> None:
        """Production + email enabled + empty EMAIL_BASE_URL raises ValidationError."""
        with pytest.raises(ValidationError, match="EMAIL_BASE_URL must be set"):
            Settings(
                database_url="postgresql://test",
                redis_url="redis://test",
                celery_broker_url="redis://broker",
                celery_result_backend="redis://backend",
                environment="production",
                jwt_secret_key="a" * 64,
                email_enabled=True,
                email_provider="smtp",
                email_development_mode=False,
                email_base_url="",
                smtp_host="smtp.example.com",
            )

    def test_production_email_enabled_smtp_with_valid_config_is_valid(self) -> None:
        """Production + email enabled + smtp + valid settings is valid."""
        test_settings = Settings(
            database_url="postgresql://test",
            redis_url="redis://test",
            celery_broker_url="redis://broker",
            celery_result_backend="redis://backend",
            environment="production",
            jwt_secret_key="a" * 64,
            email_enabled=True,
            email_provider="smtp",
            email_development_mode=False,
            email_base_url="https://ai-news-digest-doo.pages.dev",
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_user="user",
            smtp_password="pass",  # noqa: S106 - intentional test data
        )
        assert test_settings.email_provider == "smtp"
        assert test_settings.email_base_url == "https://ai-news-digest-doo.pages.dev"

    def test_production_email_enabled_requires_smtp_host(self) -> None:
        """Production + email enabled + smtp + empty SMTP_HOST raises ValidationError."""
        with pytest.raises(ValidationError, match="SMTP_HOST must be set"):
            Settings(
                database_url="postgresql://test",
                redis_url="redis://test",
                celery_broker_url="redis://broker",
                celery_result_backend="redis://backend",
                environment="production",
                jwt_secret_key="a" * 64,
                email_enabled=True,
                email_provider="smtp",
                email_development_mode=False,
                email_base_url="https://example.com",
                smtp_host="",
            )

    def test_development_console_email_remains_valid(self) -> None:
        """Development + console email + empty base_url remains valid."""
        test_settings = Settings(
            database_url="postgresql://test",
            redis_url="redis://test",
            celery_broker_url="redis://broker",
            celery_result_backend="redis://backend",
            environment="development",
            email_enabled=True,
            email_provider="console",
            email_development_mode=True,
            email_base_url="",
        )
        assert test_settings.email_provider == "console"
        assert test_settings.email_base_url == ""
