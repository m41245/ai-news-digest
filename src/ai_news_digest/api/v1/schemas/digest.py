"""
Digest API schemas.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field


class DigestCreate(BaseModel):
    """Request model for creating a digest."""

    title: Annotated[str, Field(min_length=1, max_length=200)]
    content: Annotated[str, Field(min_length=1)]
    limit: int = Field(50, ge=1, le=100)


class DigestUpdate(BaseModel):
    """Request model for updating a digest."""

    title: Annotated[str | None, Field(default=None, min_length=1, max_length=200)] = None
    content: Annotated[str | None, Field(default=None, min_length=1)] = None
    article_ids: list[UUID] | None = None


class DigestReplace(BaseModel):
    """Request model for replacing a digest."""

    title: Annotated[str, Field(min_length=1, max_length=200)]
    content: Annotated[str, Field(min_length=1)]
    article_ids: list[UUID] | None = None


class DigestResponse(BaseModel):
    """Response model representing a digest."""

    id: UUID
    title: str
    content: str
    format: str
    generated_at: str
    article_ids: list[UUID]


__all__ = ["DigestCreate", "DigestReplace", "DigestResponse", "DigestUpdate"]
