from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime

from ai_news_digest.domain.ports.email_sender import EmailSender

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SentEmailRecord:
    """Record of an email sent through TestEmailSender."""

    to: list[str]
    subject: str
    html_body: str
    text_body: str | None
    sent_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class TestEmailSender(EmailSender):
    """Email sender that records emails in memory for testing."""

    def __init__(self) -> None:
        self._sent_emails: list[SentEmailRecord] = []

    @property
    def sent_emails(self) -> list[SentEmailRecord]:
        return list(self._sent_emails)

    def clear(self) -> None:
        self._sent_emails.clear()

    async def send(
        self,
        *,
        recipient: str,
        subject: str,
        html: str,
        text: str | None = None,
    ) -> None:
        record = SentEmailRecord(
            to=[recipient],
            subject=subject,
            html_body=html,
            text_body=text,
        )
        self._sent_emails.append(record)

    async def send_email(
        self,
        *,
        to: list[str],
        subject: str,
        html_body: str,
        text_body: str | None = None,
    ) -> None:
        record = SentEmailRecord(
            to=list(to),
            subject=subject,
            html_body=html_body,
            text_body=text_body,
        )
        self._sent_emails.append(record)


__all__ = ["SentEmailRecord", "TestEmailSender"]
