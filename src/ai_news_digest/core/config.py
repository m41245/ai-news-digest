import json
from functools import lru_cache
from typing import Any, Literal

from pydantic import Field, SecretStr, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central application configuration.

    Configuration is loaded in the following order:

    1. Environment variables
    2. .env file
    3. Default values

    Environment variables always take precedence.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        frozen=True,
    )

    # ======================================================================
    # Application
    # ======================================================================

    app_name: str = "AI News Digest"

    app_version: str = "0.1.0"

    environment: Literal[
        "development",
        "testing",
        "staging",
        "production",
    ] = "development"

    debug: bool = False

    api_prefix: str = "/api/v1"

    app_startup_time: float | None = Field(
        default=None,
        description="Unix timestamp when the application finished startup.",
    )

    # ======================================================================
    # Database
    # ======================================================================

    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/ai_news_digest",
        validation_alias="DATABASE_URL",
        description="PostgreSQL connection URL.",
    )

    database_pool_size: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Database connection pool size.",
    )

    database_max_overflow: int = Field(
        default=10,
        ge=0,
        le=100,
        description="Database connection pool max overflow.",
    )

    database_pool_timeout: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Database connection pool timeout in seconds.",
    )

    database_pool_recycle: int = Field(
        default=1800,
        ge=60,
        le=86400,
        description="Database connection pool recycle time in seconds.",
    )

    database_statement_timeout: int = Field(
        default=30000,
        ge=1000,
        le=300000,
        description="Database statement timeout in milliseconds.",
    )

    # ======================================================================
    # Redis
    # ======================================================================

    redis_url: str = Field(
        default="redis://localhost:6379/0",
        validation_alias="REDIS_URL",
        description="Redis connection URL.",
    )

    redis_socket_connect_timeout: int = Field(
        default=5,
        ge=1,
        le=60,
        description="Redis socket connect timeout in seconds.",
    )

    redis_socket_timeout: int = Field(
        default=5,
        ge=1,
        le=60,
        description="Redis socket timeout in seconds.",
    )

    redis_max_connections: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Redis maximum connection pool size.",
    )

    redis_retry_on_timeout: bool = Field(
        default=True,
        description="Retry Redis operations on timeout.",
    )

    redis_retry_on_connection_error: bool = Field(
        default=True,
        description="Retry Redis operations on connection error.",
    )

    # ======================================================================
    # Celery
    # ======================================================================

    celery_broker_url: str = Field(
        default="redis://localhost:6379/1",
        validation_alias="CELERY_BROKER_URL",
        description="Celery broker URL.",
    )

    celery_result_backend: str = Field(
        default="redis://localhost:6379/2",
        validation_alias="CELERY_RESULT_BACKEND",
        description="Celery result backend.",
    )

    # ======================================================================
    # LLM Providers
    # ======================================================================

    openai_api_key: SecretStr | None = Field(
        default=None,
        validation_alias="OPENAI_API_KEY",
    )

    openai_enabled: bool = Field(
        default=True,
        validation_alias="OPENAI_ENABLED",
    )

    openai_model: str = Field(
        default="gpt-4",
        validation_alias="OPENAI_MODEL",
    )

    openai_priority: int = Field(
        default=1,
        ge=1,
        validation_alias="OPENAI_PRIORITY",
    )

    openai_timeout: int = Field(
        default=30,
        ge=1,
        validation_alias="OPENAI_TIMEOUT",
    )

    openai_max_retries: int = Field(
        default=3,
        ge=0,
        validation_alias="OPENAI_MAX_RETRIES",
    )

    anthropic_api_key: SecretStr | None = Field(
        default=None,
        validation_alias="ANTHROPIC_API_KEY",
    )

    anthropic_enabled: bool = Field(
        default=False,
        validation_alias="ANTHROPIC_ENABLED",
    )

    anthropic_model: str = Field(
        default="claude-3-opus-20240229",
        validation_alias="ANTHROPIC_MODEL",
    )

    anthropic_priority: int = Field(
        default=2,
        ge=1,
        validation_alias="ANTHROPIC_PRIORITY",
    )

    anthropic_timeout: int = Field(
        default=30,
        ge=1,
        validation_alias="ANTHROPIC_TIMEOUT",
    )

    anthropic_max_retries: int = Field(
        default=3,
        ge=0,
        validation_alias="ANTHROPIC_MAX_RETRIES",
    )

    default_llm_provider: Literal[
        "openai",
        "anthropic",
    ] = "openai"

    # ==================================================================
    # AI Processing
    # ==================================================================

    ai_max_content_length: int = Field(
        default=8000,
        ge=500,
        le=200000,
        description="Maximum article content characters sent to a provider.",
    )

    ai_summarization_max_tokens: int = Field(
        default=512,
        ge=64,
        le=4096,
        description="Maximum output tokens for summarization.",
    )

    ai_summarization_temperature: float = Field(
        default=0.2,
        ge=0.0,
        le=2.0,
        description="Generation temperature for summarization.",
    )

    ai_categorization_max_tokens: int = Field(
        default=64,
        ge=16,
        le=512,
        description="Maximum output tokens for categorization.",
    )

    ai_categorization_temperature: float = Field(
        default=0.1,
        ge=0.0,
        le=2.0,
        description="Generation temperature for categorization.",
    )

    ai_retry_max_attempts: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum retry attempts for transient provider failures.",
    )

    ai_retry_base_delay: float = Field(
        default=1.0,
        ge=0.0,
        le=60.0,
        description="Base delay in seconds for exponential backoff.",
    )

    ai_retry_max_delay: float = Field(
        default=10.0,
        ge=0.0,
        le=300.0,
        description="Maximum delay in seconds for exponential backoff.",
    )

    # ======================================================================
    # RSS
    # ======================================================================

    rss_request_timeout: int = Field(
        default=20,
        ge=1,
        le=120,
    )

    rss_max_articles_per_feed: int = Field(
        default=50,
        ge=1,
        le=500,
    )

    rss_max_response_bytes: int = Field(
        default=5_000_000,
        ge=1_000,
        le=100_000_000,
        description=(
            "Maximum accepted RSS/Atom feed response body size in bytes. "
            "Larger responses are rejected to bound memory usage."
        ),
    )

    # ======================================================================
    # Digest
    # ======================================================================

    digest_timezone: str = "UTC"

    digest_schedule_hour: int = Field(
        default=8,
        ge=0,
        le=23,
    )

    digest_schedule_minute: int = Field(
        default=0,
        ge=0,
        le=59,
    )

    digest_max_articles: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Maximum number of articles included in a single digest.",
    )

    # ======================================================================
    # Email / SMTP
    # ======================================================================

    @field_validator("smtp_port", mode="before")
    @classmethod
    def parse_smtp_port(cls, value: str | int) -> int:
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return 587
            return int(stripped)
        return value

    smtp_host: str = Field(
        default="localhost",
        description="SMTP server hostname.",
    )

    smtp_port: int = Field(
        default=587,
        ge=1,
        le=65535,
        description="SMTP server port.",
    )

    smtp_user: str | None = Field(
        default=None,
        description="SMTP username.",
    )

    smtp_password: str | None = Field(
        default=None,
        description="SMTP password.",
    )

    email_from: str = Field(
        default="noreply@ai-news-digest.com",
        description="From address for outgoing emails.",
    )

    email_recipients: str | list[str] = Field(
        default_factory=list,
        description="List of email recipients for digests.",
    )

    # ======================================================================
    # Logging
    # ======================================================================

    log_level: Literal[
        "DEBUG",
        "INFO",
        "WARNING",
        "ERROR",
        "CRITICAL",
    ] = "INFO"

    # ======================================================================
    # Authentication
    # ======================================================================

    jwt_secret_key: str = Field(
        default="ci-fake-jwt-secret-for-testing-only-2026",
        description="Secret key for signing JWT tokens.",
    )

    jwt_algorithm: str = Field(
        default="HS256",
        description="Algorithm used for JWT signing.",
    )

    jwt_expiration_minutes: int = Field(
        default=60,
        ge=1,
        description="Access token expiration time in minutes.",
    )

    bcrypt_rounds: int = Field(
        default=12,
        ge=4,
        le=31,
        description="Cost factor (rounds) for bcrypt password hashing.",
    )

    # ======================================================================
    # Authentication Tradeoffs
    # ======================================================================
    #
    # This application uses stateless JWT access tokens without refresh tokens
    # or a revocation blacklist. The security tradeoff is that a compromised
    # token remains valid until its expiration time (default: 60 minutes).
    # For the current architecture (no refresh tokens, short-lived access
    # tokens), this is an acceptable risk. If the architecture evolves to
    # include refresh tokens or longer-lived sessions, a token revocation
    # mechanism should be implemented.
    #

    cors_origins: str | list[str] | None = Field(
        default=None,
        description=(
            "Allowed CORS origins. Defaults to localhost in development "
            "and an empty list in production."
        ),
    )

    rate_limit: int = Field(
        default=60,
        ge=1,
        le=10000,
        description="Maximum requests per rate limit window.",
    )

    rate_limit_window: int = Field(
        default=60,
        ge=1,
        le=3600,
        description="Rate limit window in seconds.",
    )

    auth_rate_limit: int = Field(
        default=10,
        ge=1,
        le=10000,
        description="Maximum auth-endpoint requests per rate limit window.",
    )

    auth_rate_limit_window: int = Field(
        default=60,
        ge=1,
        le=3600,
        description="Auth-endpoint rate limit window in seconds.",
    )

    auth_max_failed_attempts: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Maximum failed login attempts before account lockout.",
    )

    auth_lockout_seconds: int = Field(
        default=300,
        ge=30,
        le=86400,
        description="Base lockout duration in seconds after too many failed logins.",
    )

    max_request_size_bytes: int = Field(
        default=1_048_576,
        ge=1024,
        le=50_000_000,
        description="Maximum allowed HTTP request body size in bytes.",
    )

    metrics_allowed_ips: str | list[str] = Field(
        default_factory=list,
        description=(
            "Optional list of client IP addresses permitted to access the "
            "/metrics endpoint. When empty, access is governed solely by the "
            "admin authentication requirement. In production this should be "
            "restricted to monitoring/metrics scrapers."
        ),
    )

    @field_validator(
        "email_recipients",
        "cors_origins",
        "metrics_allowed_ips",
        mode="before",
    )
    @classmethod
    def parse_list_from_env(cls, value: str | list[str] | None) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return []
            try:
                parsed = json.loads(stripped)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                pass
            return [item.strip() for item in stripped.split(",") if item.strip()]
        return value

    @field_validator("jwt_algorithm")
    @classmethod
    def validate_jwt_algorithm(cls, value: str) -> str:
        """Reject the 'none' algorithm to prevent algorithm-confusion attacks."""
        if value.strip().lower() == "none":
            raise ValueError("JWT algorithm 'none' is not allowed.")
        return value

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret(cls, value: str, info: ValidationInfo) -> str:
        """Ensure JWT secret is not a known weak default.

        Placeholder secrets are only rejected in non-development environments.
        In development mode, any non-empty value is accepted so that the
        example configuration and quick-starts work out of the box.
        In testing mode, weak secrets are accepted but must still meet
        minimum length requirements.
        """
        environment = info.data.get("environment", "development")
        if environment == "development":
            return value
        if environment == "testing":
            if len(value.strip()) < 32:
                raise ValueError("JWT_SECRET_KEY must be at least 32 characters long.")
            return value
        weak_defaults = {
            "change-me",
            "changeme",
            "secret",
            "dev-secret-key-change-me-in-production",
            "replace-me-with-a-secure-random-string-at-least-32-chars",
            "your-secret-key-here",
            "insecure",
            "password",
            "12345678901234567890123456789012",
        }
        weak_patterns = (
            "change_me",
            "changeme",
            "change-me",
            "replace-me",
            "replace_me",
            "please-replace",
            "your-openssl-rand",
            "test-secret",
            "test_secret",
            "placeholder",
            "your-secret",
            "your_secret",
            "dev-secret",
            "dev_secret",
            "do-not-use",
            "not-for-production",
            "not_for_production",
            "local-prod",
            "local_dev",
            "fake-key",
            "fake_key",
        )
        normalized = value.strip().lower()
        if normalized in weak_defaults:
            raise ValueError(
                "JWT_SECRET_KEY must be set to a secure value. "
                "The provided default is not allowed in any environment."
            )
        if any(pattern in normalized for pattern in weak_patterns):
            raise ValueError(
                "JWT_SECRET_KEY must be set to a secure value. "
                "The provided value resembles a placeholder."
            )
        if all(c in "0123456789abcdef" for c in normalized) and (
            "0123456789abcdef" in normalized or "abcdef0123456789" in normalized
        ):
            raise ValueError(
                "JWT_SECRET_KEY must be set to a cryptographically secure value. "
                "The provided value appears to be a sequential hex pattern."
            )
        if len(value) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters long.")
        return value

    @field_validator("cors_origins", mode="before")
    @classmethod
    def validate_cors_origins(
        cls,
        value: str | list[str] | None,
        info: ValidationInfo,
    ) -> list[str]:
        """Set CORS defaults based on environment.

        Development and staging default to localhost origins.
        Production defaults to an empty list (fail closed).
        """
        if value is None or (isinstance(value, str) and not value.strip()):
            environment = info.data.get("environment", "development")
            if environment == "production":
                return []
            return ["http://localhost:3000", "http://localhost:8000"]
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return []
            try:
                parsed = json.loads(stripped)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                pass
            return [item.strip() for item in stripped.split(",") if item.strip()]
        return value


class _LazySettingsMeta(type):
    def __instancecheck__(cls, instance: object) -> bool:
        if isinstance(instance, _LazySettings):
            return True
        return super().__instancecheck__(instance)


class _LazySettings(metaclass=_LazySettingsMeta):
    def __init__(self) -> None:
        self._loaded = False

    def _load(self) -> Settings:
        if not self._loaded:
            self._settings = get_settings()
            self._loaded = True
        return self._settings

    def __getattr__(self, name: str) -> Any:
        return getattr(self._load(), name)

    def __repr__(self) -> str:
        return repr(self._load())

    def __str__(self) -> str:
        return str(self._load())


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return a cached Settings instance.

    The configuration is instantiated once per process,
    avoiding repeated environment parsing.
    """
    return Settings()


settings = _LazySettings()
