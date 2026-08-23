"""
Unit tests for JWT utilities.
"""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from jose import JWTError

from ai_news_digest.infrastructure.auth.jwt import create_access_token, decode_access_token


def test_create_access_token_returns_string() -> None:
    """Test that create_access_token returns a string."""
    token = create_access_token(subject="user-123")
    assert isinstance(token, str)
    assert len(token) > 0


def test_create_access_token_default_expiry() -> None:
    """Test that create_access_token uses default expiry from settings."""
    fake_settings = MagicMock()
    fake_settings.jwt_expiration_minutes = 15
    fake_settings.jwt_secret_key = "test-secret"
    fake_settings.jwt_algorithm = "HS256"

    with patch(
        "ai_news_digest.infrastructure.auth.jwt.settings",
        fake_settings,
    ):
        token = create_access_token(subject="user-123")
        payload = decode_access_token(token)
        assert payload.sub == "user-123"


def test_create_access_token_custom_expiry() -> None:
    """Test that create_access_token respects custom expiry."""
    token = create_access_token(
        subject="user-123",
        expires_delta=timedelta(minutes=5),
    )
    payload = decode_access_token(token)
    assert payload.sub == "user-123"


def test_decode_access_token_invalid() -> None:
    """Test that decode_access_token raises on invalid token."""
    with pytest.raises(JWTError):
        decode_access_token("not-a-valid-token")


def test_decode_access_token_wrong_secret() -> None:
    """Test that decode_access_token raises on token signed with different secret."""
    fake_settings = MagicMock()
    fake_settings.jwt_expiration_minutes = 60
    fake_settings.jwt_secret_key = "original-secret"
    fake_settings.jwt_algorithm = "HS256"

    with patch(
        "ai_news_digest.infrastructure.auth.jwt.settings",
        fake_settings,
    ):
        token = create_access_token(subject="user-123")

    fake_settings.jwt_secret_key = "different-secret"

    with (
        patch(
            "ai_news_digest.infrastructure.auth.jwt.settings",
            fake_settings,
        ),
        pytest.raises(JWTError),
    ):
        decode_access_token(token)
