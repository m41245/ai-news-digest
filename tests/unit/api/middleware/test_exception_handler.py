"""
Unit tests for setup_exception_handlers.
"""

from __future__ import annotations

from fastapi import FastAPI

from ai_news_digest.api.middleware.exception_handler import (
    setup_exception_handlers,
)
from ai_news_digest.core.exceptions import (
    DatabaseError,
    ExternalServiceError,
    ResourceNotFoundError,
    ValidationError,
)


class TestSetupExceptionHandlers:
    """Tests for setup_exception_handlers."""

    def test_setup_registers_resource_not_found_handler(self) -> None:
        """Test ResourceNotFoundError handler is registered."""
        app = FastAPI()
        setup_exception_handlers(app)

        assert ResourceNotFoundError in app.exception_handlers

    def test_setup_registers_validation_error_handler(self) -> None:
        """Test ValidationError handler is registered."""
        app = FastAPI()
        setup_exception_handlers(app)

        assert ValidationError in app.exception_handlers

    def test_setup_registers_external_service_error_handler(self) -> None:
        """Test ExternalServiceError handler is registered."""
        app = FastAPI()
        setup_exception_handlers(app)

        assert ExternalServiceError in app.exception_handlers

    def test_setup_registers_database_error_handler(self) -> None:
        """Test DatabaseError handler is registered."""
        app = FastAPI()
        setup_exception_handlers(app)

        assert DatabaseError in app.exception_handlers
