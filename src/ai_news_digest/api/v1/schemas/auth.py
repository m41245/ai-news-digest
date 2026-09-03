"""
Authentication request/response schemas.
"""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, field_validator

from ai_news_digest.infrastructure.auth.password import _validate_password_strength


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

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        """Reject passwords that do not meet minimum strength requirements."""
        result = _validate_password_strength(value)
        if not result.valid:
            raise ValueError("; ".join(result.errors))
        return value


__all__ = ["LoginRequest", "LoginResponse", "RegisterRequest"]
