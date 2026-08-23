"""
Versioned API request/response schemas.

These modules contain dedicated Pydantic models used by the REST API. They
intentionally do not expose domain entities or SQLAlchemy ORM models.
"""

from __future__ import annotations

from ai_news_digest.api.v1.schemas.article import (
    ArticleCreate,
    ArticleResponse,
    ArticleUpdate,
)
from ai_news_digest.api.v1.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
)
from ai_news_digest.api.v1.schemas.common import (
    DEFAULT_PAGE_LIMIT,
    MAX_OFFSET,
    MAX_PAGE_LIMIT,
    ErrorResponse,
    PaginatedResponse,
)
from ai_news_digest.api.v1.schemas.delivery import DeliveryResponse
from ai_news_digest.api.v1.schemas.digest import (
    DigestCreate,
    DigestReplace,
    DigestResponse,
    DigestUpdate,
)
from ai_news_digest.api.v1.schemas.source import (
    SourceCreate,
    SourceResponse,
    SourceUpdate,
)
from ai_news_digest.api.v1.schemas.user import (
    AdminUserResponse,
    AdminUserUpdateRequest,
    UserResponse,
    UserUpdateRequest,
)

__all__ = [
    "DEFAULT_PAGE_LIMIT",
    "MAX_OFFSET",
    "MAX_PAGE_LIMIT",
    "AdminUserResponse",
    "AdminUserUpdateRequest",
    "ArticleCreate",
    "ArticleResponse",
    "ArticleUpdate",
    "DeliveryResponse",
    "DigestCreate",
    "DigestReplace",
    "DigestResponse",
    "DigestUpdate",
    "ErrorResponse",
    "LoginRequest",
    "LoginResponse",
    "PaginatedResponse",
    "RegisterRequest",
    "SourceCreate",
    "SourceResponse",
    "SourceUpdate",
    "UserResponse",
    "UserUpdateRequest",
]
