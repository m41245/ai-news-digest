from __future__ import annotations

import logging
from email.message import EmailMessage

import aiosmtplib

from ai_news_digest.core.config import get_settings
from ai_news_digest.domain.ports.email_sender import EmailSender
from ai_news_digest.infrastructure.email.errors import (
    EmailAuthenticationError,
    EmailConnectionError,
    EmailError,
    EmailInvalidRecipientError,
    EmailPermanentFailureError,
    EmailTimeoutError,
)

logger = logging.getLogger(__name__)


class SMTPSender(EmailSender):
    """SMTP email delivery implementation with provider-error mapping."""

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        username: str | None = None,
        password: str | None = None,
        from_address: str | None = None,
    ) -> None:
        settings = get_settings()
        self._host = host or settings.smtp_host
        self._port = int(port or settings.smtp_port)
        self._username = username or settings.smtp_user
        self._password = password or settings.smtp_password
        self._from_address = from_address or settings.email_from

    async def _send_internal(
        self,
        message: EmailMessage,
        *,
        recipient_count: int = 1,
    ) -> None:
        """Send a pre-built message via SMTP with provider-error mapping."""
        try:
            await aiosmtplib.send(
                message,
                hostname=self._host,
                port=self._port,
                username=self._username,
                password=self._password,
                use_tls=self._port == 465,
                start_tls=self._port != 465,
                timeout=30,
            )
        except aiosmtplib.SMTPAuthenticationError as exc:
            logger.error(
                "SMTP authentication failed",
                extra={"host": self._host, "port": self._port},
            )
            raise EmailAuthenticationError(
                "SMTP authentication failed. Check username and password."
            ) from exc
        except aiosmtplib.SMTPConnectError as exc:
            logger.warning(
                "SMTP connection failed",
                extra={"host": self._host, "port": self._port},
            )
            raise EmailConnectionError(f"SMTP connection failed: {exc}") from exc
        except aiosmtplib.SMTPTimeoutError as exc:
            logger.warning("SMTP timeout")
            raise EmailTimeoutError(f"SMTP timeout: {exc}") from exc
        except aiosmtplib.SMTPServerDisconnected as exc:
            logger.warning("SMTP server disconnected")
            raise EmailConnectionError(f"SMTP server disconnected: {exc}") from exc
        except aiosmtplib.SMTPRecipientsRefused as exc:
            logger.warning(
                "SMTP recipients refused",
                extra={"recipient_count": recipient_count},
            )
            raise EmailInvalidRecipientError(
                f"Recipients were refused by the server: {exc}"
            ) from exc
        except aiosmtplib.SMTPSenderRefused as exc:
            logger.error(
                "SMTP sender refused",
                extra={"sender": self._from_address},
            )
            raise EmailPermanentFailureError(
                f"Sender '{self._from_address}' was refused by the server."
            ) from exc
        except Exception as exc:
            logger.error(
                "Unexpected SMTP error",
                exc_info=True,
            )
            raise EmailError(f"Failed to send email: {exc}") from exc

    async def send(
        self,
        *,
        recipient: str,
        subject: str,
        html: str,
        text: str | None = None,
    ) -> None:
        """Send an email message via SMTP to a single recipient."""
        message = EmailMessage()
        message["From"] = self._from_address
        message["To"] = recipient
        message["Subject"] = subject

        if text:
            message.set_content(text)
        message.add_alternative(html, subtype="html")

        await self._send_internal(message, recipient_count=1)

    async def send_email(
        self,
        *,
        to: list[str],
        subject: str,
        html_body: str,
        text_body: str | None = None,
    ) -> None:
        """Send an email message via SMTP to multiple recipients."""
        message = EmailMessage()
        message["From"] = self._from_address
        message["Bcc"] = ", ".join(to)
        message["Subject"] = subject

        if text_body:
            message.set_content(text_body)
        message.add_alternative(html_body, subtype="html")

        await self._send_internal(message, recipient_count=len(to))


__all__ = ["SMTPSender"]
