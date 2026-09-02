"""
Article API schemas.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field


class ArticleResponse(BaseModel):
    """Response model representing an article."""

    id: UUID
    title: str
    url: str
    summary: str | None = None
    content: str | None = None
    status: str
    published_at: datetime | None = None
    fetched_at: datetime | None = None
    source_id: UUID | None = None
    category_id: UUID | None = None


class ArticleUpdate(BaseModel):
    """Request model for updating an article."""

    title: Annotated[str | None, Field(default=None, min_length=1)] = None
    summary: str | None = None
    content: str | None = None
    category_id: UUID | None = None


class ArticleCreate(BaseModel):
    """Request model for creating an article."""

    title: Annotated[str, Field(min_length=1)]
    url: str = Field(...)
    summary: str = Field(...)
    content: str | None = None
    source_id: UUID
    published_at: datetime
    category_id: UUID | None = None


__all__ = ["ArticleCreate", "ArticleResponse", "ArticleUpdate"]
