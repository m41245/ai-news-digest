"""
One-time admin bootstrap script.

Idempotently ensures an admin user exists. If the email already exists, the
user is promoted to admin and activated. If it does not exist, a new admin
user is created.

Environment variables:
    ADMIN_EMAIL       — email address for the admin user (required)
    ADMIN_PASSWORD    — plaintext password for the admin user (required)

Never logs passwords or password hashes.
"""

from __future__ import annotations

import os
import sys

from ai_news_digest.bootstrap.container import Container
from ai_news_digest.core.config import get_settings
from ai_news_digest.core.logging import configure_logging, get_logger
from ai_news_digest.domain.models.user import User
from ai_news_digest.infrastructure.auth.password import hash_password
from ai_news_digest.infrastructure.database.session import get_db_session

configure_logging()
logger = get_logger(__name__)


def _require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        logger.error("Missing required environment variable", variable=name)
        sys.exit(1)
    return value


async def _bootstrap() -> int:
    email = _require_env("ADMIN_EMAIL")
    password = _require_env("ADMIN_PASSWORD")

    settings = get_settings()
    if settings.environment == "production" and len(password) < 8:
        logger.error("Admin password must be at least 8 characters in production")
        sys.exit(1)

    async for session in get_db_session():
        container = Container(session)

        existing = await container.user_repository.get_by_email(email)

        if existing is not None:
            existing.is_admin = True
            existing.is_active = True
            existing.hashed_password = hash_password(password)
            await container.user_repository.update(existing)
            logger.info("Admin user promoted", email=email)
            print(f"Admin user ensured: {email}")
            return 0

        user = User.create(
            email=email,
            hashed_password=hash_password(password),
            is_active=True,
            is_admin=True,
        )
        await container.user_repository.create(user)
        logger.info("Admin user created", email=email)
        print(f"Admin user created: {email}")
        return 0


def main() -> int:
    try:
        import asyncio

        return asyncio.run(_bootstrap())
    except Exception as exc:
        logger.error("Admin bootstrap failed", error=str(exc), exc_info=True)
        print(f"Admin bootstrap failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
