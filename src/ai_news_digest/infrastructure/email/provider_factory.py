from __future__ import annotations

from typing import TYPE_CHECKING

from ai_news_digest.core.config import get_settings
from ai_news_digest.domain.ports.email_sender import EmailSender
from ai_news_digest.infrastructure.email.development_sender import ConsoleEmailSender
from ai_news_digest.infrastructure.email.smtp_sender import SMTPSender
from ai_news_digest.infrastructure.email.test_sender import TestEmailSender

if TYPE_CHECKING:
    from ai_news_digest.core.config import Settings


def create_email_sender(settings_obj: Settings | None = None) -> EmailSender:
    """Return the appropriate email sender based on configuration.

    Selection order:
    1. If ``email_enabled`` is False, return ``ConsoleEmailSender`` (silent).
    2. If ``email_development_mode`` is True, return ``ConsoleEmailSender``.
    3. If ``email_provider`` is ``smtp``, return ``SMTPSender``.
    4. If ``email_provider`` is ``test``, return ``TestEmailSender``.
    5. Default to ``ConsoleEmailSender``.
    """
    if settings_obj is None:
        settings_obj = get_settings()

    if not settings_obj.email_enabled or settings_obj.email_development_mode:
        return ConsoleEmailSender(from_address=settings_obj.email_from_address)

    provider = settings_obj.email_provider
    if provider == "smtp":
        return SMTPSender(
            host=settings_obj.smtp_host,
            port=settings_obj.smtp_port,
            username=settings_obj.smtp_user,
            password=settings_obj.smtp_password,
            from_address=settings_obj.email_from_address,
        )
    if provider == "test":
        return TestEmailSender()

    return ConsoleEmailSender(from_address=settings_obj.email_from_address)


__all__ = ["create_email_sender"]
