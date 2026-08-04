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
        Send an email message.
        """
        raise NotImplementedError
