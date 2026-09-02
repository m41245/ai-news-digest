from __future__ import annotations

import bcrypt
from pydantic import BaseModel, Field

from ai_news_digest.core.config import get_settings
from ai_news_digest.core.exceptions import ValidationError

settings = get_settings()

# Minimum password strength requirements
_MIN_PASSWORD_LENGTH = 8


class PasswordStrength(BaseModel):
    """Result of password strength validation."""

    valid: bool
    errors: list[str] = Field(default_factory=list)


def _validate_password_strength(password: str) -> PasswordStrength:
    """Validate password meets minimum security requirements."""
    errors: list[str] = []

    if len(password) < _MIN_PASSWORD_LENGTH:
        errors.append(f"Password must be at least {_MIN_PASSWORD_LENGTH} characters long.")

    if not any(c.isupper() for c in password):
        errors.append("Password must contain at least one uppercase letter.")

    if not any(c.islower() for c in password):
        errors.append("Password must contain at least one lowercase letter.")

    if not any(c.isdigit() for c in password):
        errors.append("Password must contain at least one number.")

    return PasswordStrength(valid=len(errors) == 0, errors=errors)


def hash_password(password: str) -> str:
    """
    Hash a plaintext password using bcrypt.

    Raises ValidationError if the password does not meet minimum strength requirements.
    """
    strength = _validate_password_strength(password)
    if not strength.valid:
        raise ValidationError(
            f"Password does not meet security requirements: {' '.join(strength.errors)}"
        )
    salt = bcrypt.gensalt(rounds=settings.bcrypt_rounds)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against a bcrypt hash.
    """
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )
