"""
Unit tests for setup_exception_handlers.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from fastapi import FastAPI, status

from ai_news_digest.api.middleware.exception_handler import (
    setup_exception_handlers,
)
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

    def _make_request(self, request_id: str = "test-request-id") -> MagicMock:
        request = MagicMock()
        request.state.request_id = request_id
        request.url.path = "/test"
        request.method = "GET"
        return request

    def _get_handler(self, app: FastAPI, exc_class):
        return app.exception_handlers[exc_class]

    async def test_resource_not_found_includes_request_id(self) -> None:
        """Test ResourceNotFoundError response includes request_id."""
        app = FastAPI()
        setup_exception_handlers(app)

        request = self._make_request()
        handler = self._get_handler(app, ResourceNotFoundError)
        response = await handler(request, ResourceNotFoundError("not found"))

        assert response.status_code == status.HTTP_404_NOT_FOUND
        content = json.loads(response.body)
        assert content["request_id"] == "test-request-id"
        assert content["code"] == "RESOURCE_NOT_FOUND"

    async def test_validation_error_includes_request_id(self) -> None:
        """Test ValidationError response includes request_id."""
        app = FastAPI()
        setup_exception_handlers(app)

        request = self._make_request()
        handler = self._get_handler(app, ValidationError)
        response = await handler(request, ValidationError("invalid"))

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        content = json.loads(response.body)
        assert content["request_id"] == "test-request-id"
        assert content["code"] == "VALIDATION_ERROR"

    async def test_duplicate_resource_includes_request_id(self) -> None:
        """Test DuplicateResourceError response includes request_id."""
        app = FastAPI()
        setup_exception_handlers(app)

        request = self._make_request()
        handler = self._get_handler(app, DuplicateResourceError)
        response = await handler(request, DuplicateResourceError("exists"))

        assert response.status_code == status.HTTP_409_CONFLICT
        content = json.loads(response.body)
        assert content["request_id"] == "test-request-id"
        assert content["code"] == "DUPLICATE_RESOURCE"

    async def test_authentication_error_includes_request_id(self) -> None:
        """Test AuthenticationError response includes request_id."""
        app = FastAPI()
        setup_exception_handlers(app)

        request = self._make_request()
        handler = self._get_handler(app, AuthenticationError)
        response = await handler(request, AuthenticationError("unauthorized"))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        content = json.loads(response.body)
        assert content["request_id"] == "test-request-id"
        assert content["code"] == "AUTHENTICATION_ERROR"

    async def test_authorization_error_includes_request_id(self) -> None:
        """Test AuthorizationError response includes request_id."""
        app = FastAPI()
        setup_exception_handlers(app)

        request = self._make_request()
        handler = self._get_handler(app, AuthorizationError)
        response = await handler(request, AuthorizationError("forbidden"))

        assert response.status_code == status.HTTP_403_FORBIDDEN
        content = json.loads(response.body)
        assert content["request_id"] == "test-request-id"
        assert content["code"] == "AUTHORIZATION_ERROR"

    async def test_rate_limit_error_includes_request_id(self) -> None:
        """Test RateLimitError response includes request_id."""
        app = FastAPI()
        setup_exception_handlers(app)

        request = self._make_request()
        handler = self._get_handler(app, RateLimitError)
        response = await handler(request, RateLimitError("too many requests"))

        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        content = json.loads(response.body)
        assert content["request_id"] == "test-request-id"
        assert content["code"] == "RATE_LIMIT_EXCEEDED"

    async def test_external_service_error_includes_request_id(self) -> None:
        """Test ExternalServiceError response includes request_id."""
        app = FastAPI()
        setup_exception_handlers(app)

        request = self._make_request()
        handler = self._get_handler(app, ExternalServiceError)
        response = await handler(request, ExternalServiceError("service down"))

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        content = json.loads(response.body)
        assert content["request_id"] == "test-request-id"
        assert content["code"] == "EXTERNAL_SERVICE_ERROR"

    async def test_database_error_sanitized_in_production(self) -> None:
        """Test DatabaseError response is sanitized in production."""
        app = FastAPI()
        setup_exception_handlers(app)

        request = self._make_request()
        handler = self._get_handler(app, DatabaseError)

        with patch("ai_news_digest.api.middleware.exception_handler.settings") as mock_settings:
            mock_settings.environment = "production"
            response = await handler(
                request, DatabaseError("connection refused: postgres://localhost:5432")
            )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        content = json.loads(response.body)
        assert content["code"] == "INTERNAL_SERVER_ERROR"
        assert content["message"] == "Database error occurred"
        assert "postgres" not in content["message"]
        assert content["request_id"] == "test-request-id"

    async def test_configuration_error_sanitized_in_production(self) -> None:
        """Test ConfigurationError response is sanitized in production."""
        app = FastAPI()
        setup_exception_handlers(app)

        request = self._make_request()
        handler = self._get_handler(app, ConfigurationError)

        with patch("ai_news_digest.api.middleware.exception_handler.settings") as mock_settings:
            mock_settings.environment = "production"
            response = await handler(request, ConfigurationError("missing API key: sk-secret-123"))

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        content = json.loads(response.body)
        assert content["code"] == "INTERNAL_SERVER_ERROR"
        assert content["message"] == "Server configuration error."
        assert "sk-secret-123" not in content["message"]
        assert content["request_id"] == "test-request-id"

    async def test_database_error_not_sanitized_in_development(self) -> None:
        """Test DatabaseError response includes details in development."""
        app = FastAPI()
        setup_exception_handlers(app)

        request = self._make_request()
        handler = self._get_handler(app, DatabaseError)

        with patch("ai_news_digest.api.middleware.exception_handler.settings") as mock_settings:
            mock_settings.environment = "development"
            response = await handler(request, DatabaseError("connection refused"))

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        content = json.loads(response.body)
        assert content["code"] == "DATABASE_ERROR"
        assert content["message"] == "connection refused"

    async def test_external_service_error_sanitized_in_production(self) -> None:
        """Test ExternalServiceError response is sanitized in production."""
        app = FastAPI()
        setup_exception_handlers(app)

        request = self._make_request()
        handler = self._get_handler(app, ExternalServiceError)

        with patch("ai_news_digest.api.middleware.exception_handler.settings") as mock_settings:
            mock_settings.environment = "production"
            response = await handler(
                request,
                ExternalServiceError("OpenAI API key invalid: sk-abc123"),
            )

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        content = json.loads(response.body)
        assert content["code"] == "INTERNAL_SERVER_ERROR"
        assert content["message"] == "External service unavailable."
        assert "sk-abc123" not in content["message"]
        assert content["request_id"] == "test-request-id"

    async def test_global_handler_includes_request_id(self) -> None:
        """Test global exception handler includes request_id."""
        app = FastAPI()
        setup_exception_handlers(app)

        request = self._make_request()
        handler = self._get_handler(app, Exception)
        response = await handler(request, RuntimeError("unexpected"))

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        content = json.loads(response.body)
        assert content["request_id"] == "test-request-id"

    async def test_global_handler_does_not_expose_details(self) -> None:
        """Test global exception handler does not expose exception details."""
        app = FastAPI()
        setup_exception_handlers(app)

        request = self._make_request()
        handler = self._get_handler(app, Exception)
        response = await handler(request, RuntimeError("secret leaked: password=abc"))

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        content = json.loads(response.body)
        assert content["code"] == "INTERNAL_SERVER_ERROR"
        assert content["message"] == "Internal server error."
        assert "password" not in content["message"]
        assert "abc" not in content["message"]

    async def test_error_response_envelope_structure(self) -> None:
        """Test all error responses have consistent envelope structure."""
        app = FastAPI()
        setup_exception_handlers(app)

        request = self._make_request()

        test_cases = [
            (ResourceNotFoundError, status.HTTP_404_NOT_FOUND, "RESOURCE_NOT_FOUND"),
            (DuplicateResourceError, status.HTTP_409_CONFLICT, "DUPLICATE_RESOURCE"),
            (ValidationError, status.HTTP_422_UNPROCESSABLE_ENTITY, "VALIDATION_ERROR"),
            (AuthenticationError, status.HTTP_401_UNAUTHORIZED, "AUTHENTICATION_ERROR"),
            (AuthorizationError, status.HTTP_403_FORBIDDEN, "AUTHORIZATION_ERROR"),
            (RateLimitError, status.HTTP_429_TOO_MANY_REQUESTS, "RATE_LIMIT_EXCEEDED"),
            (ExternalServiceError, status.HTTP_503_SERVICE_UNAVAILABLE, "EXTERNAL_SERVICE_ERROR"),
        ]

        for exc_class, expected_status, expected_code in test_cases:
            handler = self._get_handler(app, exc_class)
            response = await handler(request, exc_class("test message"))
            content = json.loads(response.body)

            assert response.status_code == expected_status
            assert "code" in content
            assert "message" in content
            assert "request_id" in content
            assert content["code"] == expected_code
            assert content["request_id"] == "test-request-id"
            assert content["message"] == "test message"

    async def test_no_stack_trace_in_response(self) -> None:
        """Test that exception details do not include stack trace information."""
        app = FastAPI()
        setup_exception_handlers(app)

        request = self._make_request()
        handler = self._get_handler(app, DatabaseError)

        try:
            raise RuntimeError("nested error")
        except RuntimeError:
            response = await handler(request, DatabaseError("db error"))

        content = json.loads(response.body)
        assert "traceback" not in json.dumps(content).lower()
        assert "Traceback" not in content.get("message", "")

    async def test_no_secrets_in_error_message(self) -> None:
        """Test that secrets are not exposed in error responses."""
        app = FastAPI()
        setup_exception_handlers(app)

        request = self._make_request()
        handler = self._get_handler(app, DatabaseError)

        with patch("ai_news_digest.api.middleware.exception_handler.settings") as mock_settings:
            mock_settings.environment = "production"
            response = await handler(
                request,
                DatabaseError("failed with password=secret123 and token=xyz"),
            )

        content = json.loads(response.body)
        assert "secret123" not in content["message"]
        assert "xyz" not in content["message"]
