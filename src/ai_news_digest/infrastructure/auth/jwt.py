from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from jwt import decode, encode  # type: ignore[attr-defined]
from jwt.exceptions import PyJWTError as JWTError
from pydantic import BaseModel

from ai_news_digest.core.config import get_settings

settings = get_settings()


class TokenPayload(BaseModel):
    """
    Decoded JWT token payload.
    """

    sub: str
    exp: datetime | None = None


def _validate_algorithm(algorithm: str) -> str:
    """
    Ensure the configured JWT algorithm is safe to use.

    Explicitly rejects the "none" algorithm, which would allow tokens to be
    accepted without a signature (algorithm-confusion / signature-stripping
    attacks).
    """
    if algorithm.strip().lower() == "none":
        raise ValueError("JWT algorithm 'none' is not allowed.")
    return algorithm


def create_access_token(
    subject: str,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a signed JWT access token.
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.jwt_expiration_minutes)

    expire = datetime.now(UTC) + expires_delta

    to_encode: dict[str, Any] = {
        "sub": subject,
        "exp": expire,
    }

    algorithm = _validate_algorithm(settings.jwt_algorithm)

    return encode(  # type: ignore[no-any-return]
        to_encode,
        settings.jwt_secret_key,
        algorithm=algorithm,
    )


def decode_access_token(token: str) -> TokenPayload:
    """
    Decode and validate a JWT access token.

    Raises JWTError if the token is invalid or expired.
    """
    algorithm = _validate_algorithm(settings.jwt_algorithm)
    try:
        payload = decode(
            token,
            settings.jwt_secret_key,
            algorithms=[algorithm],
        )
    except JWTError as exc:
        raise JWTError("Invalid access token.") from exc

    return TokenPayload(
        sub=payload.get("sub", ""),
        exp=payload.get("exp"),
    )
