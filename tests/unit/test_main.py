"""
Unit tests for main application configuration.
"""

from __future__ import annotations

from ai_news_digest.core.config import Settings
from ai_news_digest.main import create_app


def _get_settings(environment: str = "development", debug: bool = False) -> Settings:
    """Build a Settings instance with overrides."""
    return Settings(
        environment=environment,
        debug=debug,
        jwt_secret_key="a-secure-secret-key-that-is-at-least-32-chars",  # noqa: S106
        email_provider="smtp",
        email_development_mode=False,
        email_base_url="https://example.com",
        smtp_host="smtp.example.com",
    )


def test_create_app_development_docs_enabled() -> None:
    """In development, docs and redoc are enabled."""
    settings = _get_settings(environment="development")
    app = create_app(settings_override=settings)

    assert app.docs_url == "/docs"
    assert app.redoc_url == "/redoc"
    assert app.openapi_url == "/api/v1/openapi.json"


def test_create_app_production_docs_disabled() -> None:
    """In production, docs and redoc are disabled."""
    settings = _get_settings(environment="production")
    app = create_app(settings_override=settings)

    assert app.docs_url is None
    assert app.redoc_url is None
    assert app.openapi_url is None


def test_create_app_testing_docs_enabled() -> None:
    """In testing, docs and redoc are enabled."""
    settings = _get_settings(environment="testing")
    app = create_app(settings_override=settings)

    assert app.docs_url == "/docs"
    assert app.redoc_url == "/redoc"
    assert app.openapi_url == "/api/v1/openapi.json"


def test_create_app_staging_docs_enabled() -> None:
    """In staging, docs and redoc are enabled."""
    settings = _get_settings(environment="staging")
    app = create_app(settings_override=settings)

    assert app.docs_url == "/docs"
    assert app.redoc_url == "/redoc"
    assert app.openapi_url == "/api/v1/openapi.json"
