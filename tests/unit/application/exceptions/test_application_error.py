"""
Unit tests for ApplicationError.
"""

from __future__ import annotations

from ai_news_digest.application.exceptions.application_error import ApplicationError


def test_application_error_basic() -> None:
    """Test basic ApplicationError."""
    error = ApplicationError("Test error message")

    assert str(error) == "Test error message"


def test_application_error_inheritance() -> None:
    """Test ApplicationError inherits from Exception."""
    error = ApplicationError("Test error")

    assert isinstance(error, Exception)
    assert isinstance(error, ApplicationError)
