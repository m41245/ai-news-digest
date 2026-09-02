"""
Unit tests for global exception handling.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from fastapi import FastAPI, status

from ai_news_digest.api.middleware.exception_handler import setup_exception_handlers
from ai_news_digest.core.exceptions import ResourceNotFoundError


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
            RateLimitError,
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
        assert RateLimitError in app.exception_handlers
        assert Exception in app.exception_handlers

    def test_global_handler_catches_unexpected_exceptions(self) -> None:
        """The global Exception handler should be registered."""
        app = FastAPI()
        setup_exception_handlers(app)

        assert Exception in app.exception_handlers

    def _make_request(self, request_id: str = "test-request-id") -> MagicMock:
        request = MagicMock()
        request.state.request_id = request_id
        request.url.path = "/test"
        request.method = "GET"
        return request

    async def test_global_handler_returns_500_for_unhandled_exceptions(self) -> None:
        """Global handler should return 500 for unexpected exceptions."""
        app = FastAPI()
        setup_exception_handlers(app)

        request = self._make_request()
        handler = app.exception_handlers[Exception]
        response = await handler(request, RuntimeError("boom"))

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    async def test_global_handler_returns_consistent_envelope(self) -> None:
        """Global handler should return consistent error envelope."""
        app = FastAPI()
        setup_exception_handlers(app)

        request = self._make_request()
        handler = app.exception_handlers[Exception]
        response = await handler(request, RuntimeError("boom"))
        content = json.loads(response.body)

        assert "code" in content
        assert "message" in content
        assert "request_id" in content
        assert content["code"] == "INTERNAL_SERVER_ERROR"
        assert content["message"] == "Internal server error."
        assert content["request_id"] == "test-request-id"

    async def test_global_handler_includes_request_id(self) -> None:
        """Global handler should include request_id in response."""
        app = FastAPI()
        setup_exception_handlers(app)

        request = self._make_request("custom-req-456")
        handler = app.exception_handlers[Exception]
        response = await handler(request, RuntimeError("boom"))
        content = json.loads(response.body)

        assert content["request_id"] == "custom-req-456"

    async def test_global_handler_does_not_expose_exception_type(self) -> None:
        """Global handler should not expose the original exception type."""
        app = FastAPI()
        setup_exception_handlers(app)

        request = self._make_request()
        handler = app.exception_handlers[Exception]
        response = await handler(request, RuntimeError("boom"))
        content = json.loads(response.body)

        assert "RuntimeError" not in json.dumps(content)
        assert "Traceback" not in json.dumps(content)

    async def test_global_handler_does_not_expose_exception_message(self) -> None:
        """Global handler should not expose the original exception message."""
        app = FastAPI()
        setup_exception_handlers(app)

        request = self._make_request()
        handler = app.exception_handlers[Exception]
        response = await handler(request, RuntimeError("secret internal detail"))
        content = json.loads(response.body)

        assert content["message"] == "Internal server error."
        assert "secret internal detail" not in content["message"]

    async def test_global_handler_logs_exception(self) -> None:
        """Global handler should log the unhandled exception."""
        app = FastAPI()
        setup_exception_handlers(app)

        request = self._make_request()
        handler = app.exception_handlers[Exception]

        with patch("ai_news_digest.api.middleware.exception_handler.logger") as mock_logger:
            await handler(request, RuntimeError("boom"))

        mock_logger.exception.assert_called_once()
        call_kwargs = mock_logger.exception.call_args.kwargs
        assert call_kwargs["extra"]["path"] == "/test"
        assert call_kwargs["extra"]["method"] == "GET"

    async def test_global_handler_response_format_matches_app_error_handlers(
        self,
    ) -> None:
        """Global handler response format should match AppError handlers."""
        app = FastAPI()
        setup_exception_handlers(app)

        request = self._make_request()

        global_handler = app.exception_handlers[Exception]
        global_response = await global_handler(request, RuntimeError("boom"))
        global_content = json.loads(global_response.body)

        app_error_handler = app.exception_handlers[ResourceNotFoundError]
        app_error_response = await app_error_handler(request, ResourceNotFoundError("test"))
        app_error_content = json.loads(app_error_response.body)

        assert set(global_content.keys()) == set(app_error_content.keys())
        assert "code" in global_content
        assert "message" in global_content
        assert "request_id" in global_content

    async def test_global_handler_missing_request_id(self) -> None:
        """Global handler should handle missing request_id gracefully."""
        app = FastAPI()
        setup_exception_handlers(app)

        request = MagicMock()
        del request.state.request_id
        request.url.path = "/test"
        request.method = "GET"

        handler = app.exception_handlers[Exception]
        response = await handler(request, RuntimeError("boom"))
        content = json.loads(response.body)

        assert content["request_id"] is None

    async def test_global_handler_does_not_leak_stack_trace(self) -> None:
        """Global handler response should not contain stack trace details."""
        app = FastAPI()
        setup_exception_handlers(app)

        request = self._make_request()
        handler = app.exception_handlers[Exception]

        try:
            raise ValueError("nested failure")
        except ValueError:
            response = await handler(request, RuntimeError("outer"))

        body = response.body.decode()
        assert "Traceback" not in body
        assert 'File "' not in body
        assert "line" not in body.lower() or "deadline" in body.lower()

    async def test_global_handler_does_not_leak_secrets(self) -> None:
        """Global handler should not leak secrets from exception messages."""
        app = FastAPI()
        setup_exception_handlers(app)

        request = self._make_request()
        handler = app.exception_handlers[Exception]
        response = await handler(
            request, RuntimeError("database connection failed: postgres://user:password@db:5432")
        )
        content = json.loads(response.body)

        assert "postgres" not in content["message"]
        assert "password" not in content["message"]
        assert "db:5432" not in content["message"]


__all__ = ["TestGlobalExceptionHandler"]
