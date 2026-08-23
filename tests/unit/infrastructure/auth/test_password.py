"""
Unit tests for password hashing utilities.
"""

from __future__ import annotations

from ai_news_digest.infrastructure.auth.password import hash_password, verify_password


def test_hash_password_returns_string() -> None:
    """Test that hash_password returns a string."""
    hashed = hash_password("Secret123")
    assert isinstance(hashed, str)
    assert len(hashed) > 0


def test_hash_password_different_each_time() -> None:
    """Test that hashing the same password produces different hashes (due to salt)."""
    hashed1 = hash_password("Secret123")
    hashed2 = hash_password("Secret123")
    assert hashed1 != hashed2


def test_verify_password_success() -> None:
    """Test successful password verification."""
    hashed = hash_password("Secret123")
    assert verify_password("Secret123", hashed) is True


def test_verify_password_failure() -> None:
    """Test failed password verification."""
    hashed = hash_password("Secret123")
    assert verify_password("wrong", hashed) is False


def test_verify_password_empty() -> None:
    """Test verification with empty password."""
    hashed = hash_password("Abcdef12")
    assert verify_password("Abcdef12", hashed) is True
    assert verify_password("not-empty", hashed) is False
