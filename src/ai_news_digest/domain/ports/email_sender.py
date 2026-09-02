from __future__ import annotations

from abc import ABC, abstractmethod


class EmailSender(ABC):
    """
    Email delivery interface.
    """

    @abstractmethod
    async def send(
        self,
        *,
        recipient: str,
        subject: str,
        html: str,
        text: str | None = None,
    ) -> None:
        """
        Send an email message to a single recipient.
        """
        raise NotImplementedError

    @abstractmethod
    async def send_email(
        self,
        *,
        to: list[str],
        subject: str,
        html_body: str,
        text_body: str | None = None,
    ) -> None:
        """
        Send an email message to multiple recipients.
        """
        raise NotImplementedError
