from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ai_news_digest.domain.ports.email_sender import EmailSender

if TYPE_CHECKING:
    from ai_news_digest.core.config import Settings

logger = logging.getLogger(__name__)


class ConsoleEmailSender(EmailSender):
    """Email sender that logs messages to console for development mode."""

    def __init__(self, from_address: str | None = None) -> None:
        settings = self._get_settings()
        self._from_address = (
            from_address
            or getattr(settings, "email_from_address", None)
            or getattr(settings, "email_from", "noreply@example.com")
        )

    @staticmethod
    def _get_settings() -> Settings:
        from ai_news_digest.core.config import get_settings
        return get_settings()

    async def send(
        self,
        *,
        recipient: str,
        subject: str,
        html: str,
        text: str | None = None,
    ) -> None:
        logger.info(
            "[CONSOLE EMAIL] To: %s | Subject: %s | From: %s",
            recipient,
            subject,
            self._from_address,
        )
        logger.debug("[CONSOLE EMAIL HTML]\n%s", html)
        if text:
            logger.debug("[CONSOLE EMAIL TEXT]\n%s", text)

    async def send_email(
        self,
        *,
        to: list[str],
        subject: str,
        html_body: str,
        text_body: str | None = None,
    ) -> None:
        logger.info(
            "[CONSOLE EMAIL] To: %s | Subject: %s | From: %s | Count: %d",
            ", ".join(to),
            subject,
            self._from_address,
            len(to),
        )
        logger.debug("[CONSOLE EMAIL HTML]\n%s", html_body)
        if text_body:
            logger.debug("[CONSOLE EMAIL TEXT]\n%s", text_body)


__all__ = ["ConsoleEmailSender"]
