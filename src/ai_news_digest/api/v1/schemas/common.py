"""
Shared API schemas for pagination and error envelopes.

These schemas are reusable across the versioned REST API and keep response
shapes consistent without exposing domain entities or ORM models.
"""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")

DEFAULT_PAGE_LIMIT = 20
MAX_PAGE_LIMIT = 100
MAX_OFFSET = 10_000


class PaginatedResponse(BaseModel, Generic[T]):
    """Envelope returned by collection endpoints."""

    items: list[T]
    total: int
    limit: int
    offset: int


class ErrorResponse(BaseModel):
    """Standard error envelope returned by exception handlers."""

    detail: str


__all__ = [
    "DEFAULT_PAGE_LIMIT",
    "MAX_OFFSET",
    "MAX_PAGE_LIMIT",
    "ErrorResponse",
    "PaginatedResponse",
]
