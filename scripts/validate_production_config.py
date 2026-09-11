#!/usr/bin/env python3
"""Production configuration validator.

Validates that all required production configuration is present and secure.
Exits with code 0 if valid, non-zero if invalid.
"""

from __future__ import annotations

import os
import sys

from ai_news_digest.core.config import get_settings


class ProductionConfigError(Exception):
    """Raised when production configuration is invalid."""


def _check_env_var(name: str, value: str | None, required: bool = True) -> str | None:
    """Check an environment variable. Returns value or None if missing/empty."""
    if value is None or (isinstance(value, str) and not value.strip()):
        if required:
            raise ProductionConfigError(f"{name} is required but not set.")
        return None
    return value.strip()


def validate_production_config() -> list[str]:
    """Validate production configuration. Returns list of warnings/errors."""
    errors: list[str] = []
    warnings: list[str] = []

    env = os.environ.get("ENVIRONMENT", "development")

    if env != "production":
        errors.append(f"ENVIRONMENT must be 'production', got '{env}'")

    debug = os.environ.get("DEBUG", "false").lower()
    if debug == "true":
        errors.append("DEBUG must be 'false' in production")

    jwt_secret = os.environ.get("JWT_SECRET_KEY", "")
    if not jwt_secret or len(jwt_secret.strip()) < 32:
        errors.append("JWT_SECRET_KEY must be at least 32 characters")
    elif any(pattern in jwt_secret.lower() for pattern in (
        "change-me", "changeme", "replace-me", "please-replace",
        "your-secret", "test-secret", "placeholder", "dev-secret",
        "local-prod", "local-dev", "fake-key", "ci-fake", "testing-only",
    )):
        errors.append("JWT_SECRET_KEY must not be a known placeholder value")

    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url:
        errors.append("DATABASE_URL is required")
    elif "postgresql" not in database_url and "postgres" not in database_url:
        errors.append("DATABASE_URL must point to a PostgreSQL database")

    redis_url = os.environ.get("REDIS_URL", "")
    if not redis_url:
        errors.append("REDIS_URL is required")
    elif "redis" not in redis_url:
        errors.append("REDIS_URL must point to a Redis instance")

    celery_broker_url = os.environ.get("CELERY_BROKER_URL", "")
    if not celery_broker_url:
        errors.append("CELERY_BROKER_URL is required")

    celery_result_backend = os.environ.get("CELERY_RESULT_BACKEND", "")
    if not celery_result_backend:
        errors.append("CELERY_RESULT_BACKEND is required")

    cors_origins = os.environ.get("CORS_ORIGINS", "")
    if not cors_origins or cors_origins in ("[]", "null", "None", ""):
        errors.append("CORS_ORIGINS must be set to real production origins")

    email_development_mode = os.environ.get("EMAIL_DEVELOPMENT_MODE", "true").lower()
    if email_development_mode == "true":
        errors.append("EMAIL_DEVELOPMENT_MODE must be 'false' in production")

    email_enabled = os.environ.get("EMAIL_ENABLED", "false").lower()
    if email_enabled == "true":
        smtp_host = os.environ.get("SMTP_HOST", "")
        if not smtp_host:
            errors.append("SMTP_HOST is required when EMAIL_ENABLED=true")

        email_base_url = os.environ.get("EMAIL_BASE_URL", "")
        if not email_base_url:
            errors.append("EMAIL_BASE_URL is required when EMAIL_ENABLED=true")

        email_provider = os.environ.get("EMAIL_PROVIDER", "console")
        if email_provider != "smtp":
            errors.append("EMAIL_PROVIDER must be 'smtp' when EMAIL_ENABLED=true in production")
    else:
        if os.environ.get("EMAIL_PROVIDER", "console") == "smtp":
            warnings.append(
                "EMAIL_PROVIDER=smtp but EMAIL_ENABLED=false - "
                "SMTP settings will be ignored"
            )

    smtp_host = os.environ.get("SMTP_HOST", "")
    if not smtp_host:
        warnings.append("SMTP_HOST is not set - email delivery will use console sender")

    email_from = os.environ.get("EMAIL_FROM", "")
    if not email_from:
        warnings.append("EMAIL_FROM is not set")

    return errors + [f"WARNING: {w}" for w in warnings]


def main() -> int:
    """Main entry point."""
    print("Production Configuration Validator")
    print("=" * 50)

    try:
        settings = get_settings()
        print(f"Environment: {settings.environment}")
        print(f"Debug: {settings.debug}")
        print(f"App: {settings.app_name} v{settings.app_version}")
    except Exception as exc:
        print(f"ERROR: Failed to load configuration: {exc}")
        return 1

    issues = validate_production_config()

    if issues:
        print("\nValidation Issues:")
        for issue in issues:
            print(f"  - {issue}")
        if any(not issue.startswith("WARNING:") for issue in issues):
            print("\nRESULT: FAILED - Production configuration has errors")
            return 1
        print("\nRESULT: PASSED with warnings")
        return 0

    print("\nRESULT: PASSED - Production configuration is valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
