from __future__ import annotations

from ai_news_digest.core.exceptions import ExternalServiceError


class AIError(ExternalServiceError):
    """Base for all provider-independent AI processing errors."""


class AIConfigurationError(AIError):
    """Raised when a selected provider is missing required configuration."""


class AIAuthenticationError(AIError):
    """Raised when provider authentication fails (invalid/expired API key)."""


class AIRateLimitError(AIError):
    """Raised when the provider rate-limits the request."""


class AITimeoutError(AIError):
    """Raised when the provider request exceeds the configured timeout."""


class AITransientError(AIError):
    """Raised for transient provider/network failures that may succeed on retry.

    Examples: 5xx responses, connection resets, temporary unavailability.
    """


class AIInvalidResponseError(AIError):
    """Raised when the provider returns a malformed or unusable response."""


class AIUnsupportedProviderError(AIError):
    """Raised when a requested provider is not registered or not supported."""


class AIPermanentProcessingError(AIError):
    """Raised when processing has definitively failed and should not be retried."""


__all__ = [
    "AIAuthenticationError",
    "AIConfigurationError",
    "AIError",
    "AIInvalidResponseError",
    "AIPermanentProcessingError",
    "AIRateLimitError",
    "AITimeoutError",
    "AITransientError",
    "AIUnsupportedProviderError",
]
