import json
from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _parse_list_env(value: str | list[str]) -> list[str]:
    if isinstance(value, list):
        return value
    if not value or not value.strip():
        return []
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError:
        pass
    return [item.strip() for item in value.split(",") if item.strip()]


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

    # ======================================================================
    # Database
    # ======================================================================

    database_url: str = Field(
        validation_alias="DATABASE_URL",
        description="PostgreSQL connection URL.",
    )

    # ======================================================================
    # Redis
    # ======================================================================

    redis_url: str = Field(
        validation_alias="REDIS_URL",
        description="Redis connection URL.",
    )

    # ======================================================================
    # Celery
    # ======================================================================

    celery_broker_url: str = Field(
        validation_alias="CELERY_BROKER_URL",
        description="Celery broker URL.",
    )

    celery_result_backend: str = Field(
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

    smtp_port: str | int = Field(
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

    cors_origins: str | list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="Allowed CORS origins.",
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

    @field_validator("email_recipients", "cors_origins", mode="before")
    @classmethod
    def parse_list_from_env(cls, value: str | list[str]) -> list[str]:
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

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret(cls, value: str, info: ValidationInfo) -> str:
        """Ensure JWT secret is not a known weak default."""
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
        normalized = value.strip().lower()
        if normalized in weak_defaults:
            raise ValueError(
                "JWT_SECRET_KEY must be set to a secure value. "
                "The provided default is not allowed in any environment."
            )
        if len(value) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters long.")
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return a cached Settings instance.

    The configuration is instantiated once per process,
    avoiding repeated environment parsing.
    """
    return Settings()


settings = get_settings()
