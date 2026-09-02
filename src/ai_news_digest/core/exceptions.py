from __future__ import annotations

from typing import Any


class AppError(Exception):
    """
    Base exception for all application-specific errors.
    """

    code: str = "APP_ERROR"

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        code: str | None = None,
    ) -> None:
        self.message = message
        self.details = details or {}
        self.code = code or self.__class__.code
        super().__init__(message)


class ValidationError(AppError):
    """
    Raised when application validation fails.
    """

    code = "VALIDATION_ERROR"


class ResourceNotFoundError(AppError):
    """
    Raised when a requested resource does not exist.
    """

    code = "RESOURCE_NOT_FOUND"


class DuplicateResourceError(AppError):
    """
    Raised when attempting to create a duplicate resource.
    """

    code = "DUPLICATE_RESOURCE"


class ExternalServiceError(AppError):
    """
    Raised when an external dependency fails.

    Examples:
        - OpenAI
        - Anthropic
        - RSS feeds
        - SMTP
        - Redis
    """

    code = "EXTERNAL_SERVICE_ERROR"


class DatabaseError(AppError):
    """
    Raised when a database operation fails.
    """

    code = "DATABASE_ERROR"


class ConfigurationError(AppError):
    """
    Raised when application configuration is invalid.
    """

    code = "CONFIGURATION_ERROR"


class AuthenticationError(AppError):
    """
    Raised when authentication fails.
    """

    code = "AUTHENTICATION_ERROR"


class AuthorizationError(AppError):
    """
    Raised when authorization fails.
    """

    code = "AUTHORIZATION_ERROR"


class RateLimitError(AppError):
    """
    Raised when a client exceeds the rate limit.
    """

    code = "RATE_LIMIT_EXCEEDED"
