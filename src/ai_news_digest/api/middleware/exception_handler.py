from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fastapi import Request, status
from fastapi.responses import JSONResponse

from ai_news_digest.core.config import settings
from ai_news_digest.core.exceptions import (
    AppError,
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

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = logging.getLogger(__name__)


def _is_production() -> bool:
    return settings.environment == "production"


def _build_error_content(
    request: Request,
    status_code: int,
    exc: AppError,
    default_message: str,
) -> dict[str, str | None]:
    request_id = getattr(request.state, "request_id", None)
    if _is_production() and status_code >= 500:
        return {
            "code": "INTERNAL_SERVER_ERROR",
            "message": default_message,
            "request_id": request_id,
        }
    return {
        "code": exc.code,
        "message": exc.message,
        "request_id": request_id,
    }


def setup_exception_handlers(app: FastAPI) -> None:
    """Setup exception handlers for the FastAPI application."""

    @app.exception_handler(ResourceNotFoundError)
    async def resource_not_found_handler(
        request: Request,
        exc: ResourceNotFoundError,
    ) -> JSONResponse:
        content = _build_error_content(
            request, status.HTTP_404_NOT_FOUND, exc, "Resource not found."
        )
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=content,
        )

    @app.exception_handler(DuplicateResourceError)
    async def duplicate_resource_handler(
        request: Request,
        exc: DuplicateResourceError,
    ) -> JSONResponse:
        content = _build_error_content(
            request, status.HTTP_409_CONFLICT, exc, "Resource already exists."
        )
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=content,
        )

    @app.exception_handler(ValidationError)
    async def validation_error_handler(
        request: Request,
        exc: ValidationError,
    ) -> JSONResponse:
        content = _build_error_content(
            request, status.HTTP_422_UNPROCESSABLE_ENTITY, exc, "Validation failed."
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=content,
        )

    @app.exception_handler(AuthenticationError)
    async def authentication_error_handler(
        request: Request,
        exc: AuthenticationError,
    ) -> JSONResponse:
        content = _build_error_content(
            request, status.HTTP_401_UNAUTHORIZED, exc, "Authentication required."
        )
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=content,
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.exception_handler(AuthorizationError)
    async def authorization_error_handler(
        request: Request,
        exc: AuthorizationError,
    ) -> JSONResponse:
        content = _build_error_content(
            request, status.HTTP_403_FORBIDDEN, exc, "Insufficient permissions."
        )
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content=content,
        )

    @app.exception_handler(RateLimitError)
    async def rate_limit_error_handler(
        request: Request,
        exc: RateLimitError,
    ) -> JSONResponse:
        content = _build_error_content(
            request, status.HTTP_429_TOO_MANY_REQUESTS, exc, "Rate limit exceeded."
        )
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content=content,
        )

    @app.exception_handler(ExternalServiceError)
    async def external_service_error_handler(
        request: Request,
        exc: ExternalServiceError,
    ) -> JSONResponse:
        content = _build_error_content(
            request, status.HTTP_503_SERVICE_UNAVAILABLE, exc, "External service unavailable."
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=content,
        )

    @app.exception_handler(DatabaseError)
    async def database_error_handler(
        request: Request,
        exc: DatabaseError,
    ) -> JSONResponse:
        logger.exception(
            "Database error",
            extra={"path": request.url.path, "method": request.method},
        )
        content = _build_error_content(
            request, status.HTTP_500_INTERNAL_SERVER_ERROR, exc, "Database error occurred"
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=content,
        )

    @app.exception_handler(ConfigurationError)
    async def configuration_error_handler(
        request: Request,
        exc: ConfigurationError,
    ) -> JSONResponse:
        logger.exception(
            "Configuration error",
            extra={"path": request.url.path, "method": request.method},
        )
        content = _build_error_content(
            request, status.HTTP_500_INTERNAL_SERVER_ERROR, exc, "Server configuration error."
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=content,
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        """Catch-all handler for unexpected exceptions."""
        logger.exception(
            "Unhandled exception",
            extra={"path": request.url.path, "method": request.method},
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "code": "INTERNAL_SERVER_ERROR",
                "message": "Internal server error.",
                "request_id": getattr(request.state, "request_id", None),
            },
        )
