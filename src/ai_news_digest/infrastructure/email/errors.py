from __future__ import annotations

from ai_news_digest.core.exceptions import ExternalServiceError


class EmailError(ExternalServiceError):
    """Base exception for email delivery failures."""


class EmailConfigurationError(EmailError):
    """Raised when email configuration is invalid."""


class EmailAuthenticationError(EmailError):
    """Raised when SMTP authentication fails."""


class EmailConnectionError(EmailError):
    """Raised on transient SMTP connection failures."""


class EmailTimeoutError(EmailError):
    """Raised when an SMTP operation times out."""


class EmailRateLimitError(EmailError):
    """Raised when the SMTP server rate-limits the client."""


class EmailInvalidRecipientError(EmailError):
    """Raised when the recipient address is rejected by the server."""


class EmailPermanentFailureError(EmailError):
    """Raised when the server permanently rejects delivery."""


__all__ = [
    "EmailAuthenticationError",
    "EmailConfigurationError",
    "EmailConnectionError",
    "EmailError",
    "EmailInvalidRecipientError",
    "EmailPermanentFailureError",
    "EmailRateLimitError",
    "EmailTimeoutError",
]
