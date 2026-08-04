from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
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

    anthropic_api_key: SecretStr | None = Field(
        default=None,
        validation_alias="ANTHROPIC_API_KEY",
    )

    default_llm_provider: Literal[
        "openai",
        "anthropic",
    ] = "openai"

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


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return a cached Settings instance.

    The configuration is instantiated once per process,
    avoiding repeated environment parsing.
    """
    return Settings()


settings = get_settings()
