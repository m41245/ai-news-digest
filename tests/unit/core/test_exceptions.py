"""
Unit tests for core exceptions.
"""

from __future__ import annotations

from ai_news_digest.core.exceptions import (
    AppError,
    AuthenticationError,
    AuthorizationError,
    ConfigurationError,
    DatabaseError,
    DuplicateResourceError,
    ExternalServiceError,
    ResourceNotFoundError,
    ValidationError,
)


def test_app_error_basic() -> None:
    """Test basic AppError."""
    error = AppError("Test error message")

    assert error.message == "Test error message"
    assert error.details == {}
    assert str(error) == "Test error message"


def test_app_error_with_details() -> None:
    """Test AppError with details."""
    details = {"field": "value", "code": 123}
    error = AppError("Test error", details=details)

    assert error.message == "Test error"
    assert error.details == details
    assert error.details["field"] == "value"


def test_validation_error() -> None:
    """Test ValidationError."""
    error = ValidationError("Validation failed")

    assert isinstance(error, AppError)
    assert error.message == "Validation failed"


def test_resource_not_found_error() -> None:
    """Test ResourceNotFoundError."""
    error = ResourceNotFoundError("Resource not found")

    assert isinstance(error, AppError)
    assert error.message == "Resource not found"


def test_duplicate_resource_error() -> None:
    """Test DuplicateResourceError."""
    error = DuplicateResourceError("Duplicate resource")

    assert isinstance(error, AppError)
    assert error.message == "Duplicate resource"


def test_external_service_error() -> None:
    """Test ExternalServiceError."""
    error = ExternalServiceError("External service failed")

    assert isinstance(error, AppError)
    assert error.message == "External service failed"


def test_database_error() -> None:
    """Test DatabaseError."""
    error = DatabaseError("Database operation failed")

    assert isinstance(error, AppError)
    assert error.message == "Database operation failed"


def test_configuration_error() -> None:
    """Test ConfigurationError."""
    error = ConfigurationError("Invalid configuration")

    assert isinstance(error, AppError)
    assert error.message == "Invalid configuration"


def test_authentication_error() -> None:
    """Test AuthenticationError."""
    error = AuthenticationError("Authentication failed")

    assert isinstance(error, AppError)
    assert error.message == "Authentication failed"


def test_authorization_error() -> None:
    """Test AuthorizationError."""
    error = AuthorizationError("Authorization failed")

    assert isinstance(error, AppError)
    assert error.message == "Authorization failed"


def test_app_error_details_empty_dict() -> None:
    """Test AppError with empty details dict."""
    error = AppError("Test error", details={})

    assert error.details == {}


def test_app_error_details_none() -> None:
    """Test AppError with None details."""
    error = AppError("Test error", details=None)

    assert error.details == {}
