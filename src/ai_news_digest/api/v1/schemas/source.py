"""
Source API schemas.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field


class SourceCreate(BaseModel):
    """Request model for creating a news source."""

    name: Annotated[str, Field(min_length=1, max_length=200)]
    feed_url: Annotated[str, Field(max_length=2048)]
    website_url: Annotated[str | None, Field(default=None, max_length=2048)] = None
    description: Annotated[str | None, Field(default=None, max_length=500)] = None


class SourceUpdate(BaseModel):
    """Request model for updating a news source."""

    name: Annotated[str | None, Field(default=None, min_length=1, max_length=200)] = None
    feed_url: Annotated[str | None, Field(default=None, max_length=2048)] = None
    website_url: Annotated[str | None, Field(default=None, max_length=2048)] = None
    description: Annotated[str | None, Field(default=None, max_length=500)] = None
    is_active: bool | None = None
    status: str | None = None


class SourceResponse(BaseModel):
    """Response model representing a news source."""

    id: UUID
    name: str
    feed_url: str
    website_url: str | None
    description: str | None
    is_active: bool
    status: str


__all__ = ["SourceCreate", "SourceResponse", "SourceUpdate"]
