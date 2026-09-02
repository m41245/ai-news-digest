"""
User API schemas.

Server-controlled fields (``id``, ``hashed_password``, ``created_at``) are
never accepted on input and password hashes are never returned in responses.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, EmailStr, Field


class UserResponse(BaseModel):
    """Public representation of the current user."""

    id: str
    email: str
    is_active: bool
    is_admin: bool


class UserUpdateRequest(BaseModel):
    """Fields a user may update on their own profile."""

    email: Annotated[EmailStr | None, Field(default=None)] = None
    password: Annotated[str | None, Field(default=None, min_length=8)] = None


class AdminUserResponse(BaseModel):
    """Administrative representation of a user."""

    id: str
    email: str
    is_active: bool
    is_admin: bool
    created_at: datetime | None = None


class AdminUserUpdateRequest(BaseModel):
    """Fields an administrator may change on any user."""

    email: Annotated[EmailStr | None, Field(default=None)] = None
    is_active: bool | None = None
    is_admin: bool | None = None
    password: Annotated[str | None, Field(default=None, min_length=8)] = None


__all__ = [
    "AdminUserResponse",
    "AdminUserUpdateRequest",
    "UserResponse",
    "UserUpdateRequest",
]
