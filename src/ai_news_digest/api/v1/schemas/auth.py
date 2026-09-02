"""
Authentication request/response schemas.
"""

from __future__ import annotations

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    """Request model for user login."""

    username: str
    password: str


class LoginResponse(BaseModel):
    """Response model for a successful login."""

    access_token: str
    token_type: str = "bearer"


class RegisterRequest(BaseModel):
    """Request model for user self-registration."""

    email: EmailStr
    password: str


__all__ = ["LoginRequest", "LoginResponse", "RegisterRequest"]
