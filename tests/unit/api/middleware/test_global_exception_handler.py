"""
Unit tests for global exception handling.
"""

from __future__ import annotations

from fastapi import FastAPI

from ai_news_digest.api.middleware.exception_handler import setup_exception_handlers


class TestGlobalExceptionHandler:
    """Tests for global exception handling."""

    def test_exception_handler_registers_all_handlers(self) -> None:
        """All exception handlers should be registered on the app."""
        app = FastAPI()
        setup_exception_handlers(app)

        from ai_news_digest.core.exceptions import (
            AuthenticationError,
            AuthorizationError,
            ConfigurationError,
            DatabaseError,
            DuplicateResourceError,
            ExternalServiceError,
            ResourceNotFoundError,
            ValidationError,
        )

        assert ResourceNotFoundError in app.exception_handlers
        assert DuplicateResourceError in app.exception_handlers
        assert ValidationError in app.exception_handlers
        assert AuthenticationError in app.exception_handlers
        assert AuthorizationError in app.exception_handlers
        assert ExternalServiceError in app.exception_handlers
        assert DatabaseError in app.exception_handlers
        assert ConfigurationError in app.exception_handlers
        assert Exception in app.exception_handlers

    def test_global_handler_catches_unexpected_exceptions(self) -> None:
        """The global Exception handler should be registered."""
        app = FastAPI()
        setup_exception_handlers(app)

        assert Exception in app.exception_handlers


__all__ = ["TestGlobalExceptionHandler"]
