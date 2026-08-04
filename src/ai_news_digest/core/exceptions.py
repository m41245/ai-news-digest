from __future__ import annotations

from typing import Any


class AppError(Exception):
    """
    Base exception for all application-specific errors.
    """

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(message)


class ValidationError(AppError):
    """
    Raised when application validation fails.
    """


class ResourceNotFoundError(AppError):
    """
    Raised when a requested resource does not exist.
    """


class DuplicateResourceError(AppError):
    """
    Raised when attempting to create a duplicate resource.
    """


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


class DatabaseError(AppError):
    """
    Raised when a database operation fails.
    """


class ConfigurationError(AppError):
    """
    Raised when application configuration is invalid.
    """


class AuthenticationError(AppError):
    """
    Raised when authentication fails.
    """


class AuthorizationError(AppError):
    """
    Raised when authorization fails.
    """
