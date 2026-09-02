"""
Unit tests for JWT utilities.
"""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from jwt.exceptions import PyJWTError as JWTError

from ai_news_digest.infrastructure.auth.jwt import (
    _validate_algorithm,
    create_access_token,
    decode_access_token,
)


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


def test_validate_algorithm_rejects_none() -> None:
    """The 'none' algorithm must be rejected to prevent unsigned tokens."""
    with pytest.raises(ValueError):
        _validate_algorithm("none")
    with pytest.raises(ValueError):
        _validate_algorithm("None")
    with pytest.raises(ValueError):
        _validate_algorithm("NONE ")


def test_validate_algorithm_allows_safe_algorithms() -> None:
    """Safe algorithms must be accepted unchanged."""
    assert _validate_algorithm("HS256") == "HS256"
    assert _validate_algorithm("RS256") == "RS256"


def test_create_access_token_rejects_none_algorithm() -> None:
    """create_access_token must refuse to sign with the 'none' algorithm."""
    fake_settings = MagicMock()
    fake_settings.jwt_expiration_minutes = 60
    fake_settings.jwt_secret_key = "test-secret"
    fake_settings.jwt_algorithm = "none"

    with (
        patch(
            "ai_news_digest.infrastructure.auth.jwt.settings",
            fake_settings,
        ),
        pytest.raises(ValueError),
    ):
        create_access_token(subject="user-123")


def test_decode_access_token_rejects_none_algorithm() -> None:
    """decode_access_token must refuse the 'none' algorithm for any token."""
    fake_settings = MagicMock()
    fake_settings.jwt_expiration_minutes = 60
    fake_settings.jwt_secret_key = "test-secret"
    fake_settings.jwt_algorithm = "none"

    with (
        patch(
            "ai_news_digest.infrastructure.auth.jwt.settings",
            fake_settings,
        ),
        pytest.raises(ValueError),
    ):
        decode_access_token("some.token.value")


def test_decode_access_token_rejects_different_algorithm() -> None:
    """A token must not decode when the configured algorithm differs."""
    sign_settings = MagicMock()
    sign_settings.jwt_expiration_minutes = 60
    sign_settings.jwt_secret_key = "test-secret"
    sign_settings.jwt_algorithm = "HS256"

    with patch(
        "ai_news_digest.infrastructure.auth.jwt.settings",
        sign_settings,
    ):
        token = create_access_token(subject="user-123")

    verify_settings = MagicMock()
    verify_settings.jwt_expiration_minutes = 60
    verify_settings.jwt_secret_key = "test-secret"
    verify_settings.jwt_algorithm = "HS384"

    with (
        patch(
            "ai_news_digest.infrastructure.auth.jwt.settings",
            verify_settings,
        ),
        pytest.raises(JWTError),
    ):
        decode_access_token(token)
