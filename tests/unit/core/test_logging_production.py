"""
Unit tests for production logging configuration.
"""

from __future__ import annotations

from unittest.mock import patch

from ai_news_digest.core.config import Settings
from ai_news_digest.core.logging import configure_logging, get_logger


class TestProductionLogging:
    """Tests for production logging configuration."""

    def test_production_uses_json_renderer(self) -> None:
        """Production environment should configure logging without errors."""
        settings = Settings(
            environment="production",
            database_url="postgresql://test",
            redis_url="redis://test",
            celery_broker_url="redis://broker",
            celery_result_backend="redis://backend",
            jwt_secret_key="a-secure-secret-key-that-is-at-least-32-chars",  # noqa: S106
            email_provider="smtp",
            email_development_mode=False,
            email_base_url="https://example.com",
            smtp_host="smtp.example.com",
        )

        with patch("ai_news_digest.core.logging.settings", settings):
            configure_logging()

        logger = get_logger("test_production")
        logger.info("test_event", key="value")

    def test_development_uses_console_renderer(self) -> None:
        """Development environment should configure logging without errors."""
        settings = Settings(
            environment="development",
            database_url="postgresql://test",
            redis_url="redis://test",
            celery_broker_url="redis://broker",
            celery_result_backend="redis://backend",
            jwt_secret_key="a-secure-secret-key-that-is-at-least-32-chars",  # noqa: S106
        )

        with patch("ai_news_digest.core.logging.settings", settings):
            configure_logging()

        logger = get_logger("test_development")
        logger.info("test_event", key="value")

    def test_testing_uses_console_renderer(self) -> None:
        """Testing environment should configure logging without errors."""
        settings = Settings(
            environment="testing",
            database_url="postgresql://test",
            redis_url="redis://test",
            celery_broker_url="redis://broker",
            celery_result_backend="redis://backend",
            jwt_secret_key="a-secure-secret-key-that-is-at-least-32-chars",  # noqa: S106
        )

        with patch("ai_news_digest.core.logging.settings", settings):
            configure_logging()

        logger = get_logger("test_testing")
        logger.info("test_event", key="value")

    def test_staging_uses_console_renderer(self) -> None:
        """Staging environment should configure logging without errors."""
        settings = Settings(
            environment="staging",
            database_url="postgresql://test",
            redis_url="redis://test",
            celery_broker_url="redis://broker",
            celery_result_backend="redis://backend",
            jwt_secret_key="a-secure-secret-key-that-is-at-least-32-chars",  # noqa: S106
        )

        with patch("ai_news_digest.core.logging.settings", settings):
            configure_logging()

        logger = get_logger("test_staging")
        logger.info("test_event", key="value")


__all__ = ["TestProductionLogging"]
