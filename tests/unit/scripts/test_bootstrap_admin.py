"""
Tests for scripts/ops/bootstrap_admin.py
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from scripts.ops.bootstrap_admin import _bootstrap

from ai_news_digest.domain.models.user import User
from ai_news_digest.infrastructure.auth.password import hash_password


def _make_container(existing_user: User | None = None) -> MagicMock:
    container = MagicMock()
    container.user_repository = MagicMock()
    container.user_repository.get_by_email = AsyncMock(return_value=existing_user)
    container.user_repository.create = AsyncMock()
    container.user_repository.update = AsyncMock()
    return container


@pytest.fixture
def mock_session() -> MagicMock:
    session = MagicMock()
    return session


@pytest.mark.asyncio
async def test_bootstrap_creates_admin_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """When no user exists, a new admin user is created."""

    container = _make_container(existing_user=None)

    async def _mock_session():
        yield MagicMock()

    monkeypatch.setenv("ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("ADMIN_PASSWORD", "SecurePass123")
    monkeypatch.setattr(
        "scripts.ops.bootstrap_admin.get_db_session",
        _mock_session,
    )

    with patch(
        "scripts.ops.bootstrap_admin.Container",
        return_value=container,
    ):
        result = await _bootstrap()

    assert result == 0
    container.user_repository.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_bootstrap_promotes_existing_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When the user already exists, they are promoted to admin."""

    existing = User(
        id="123e4567-e89b-12d3-a456-426614174000",
        email="admin@example.com",
        hashed_password=hash_password("OldPass123"),
        is_active=False,
        is_admin=False,
        created_at=datetime.now(UTC),
    )

    container = _make_container(existing_user=existing)

    async def _mock_session():
        yield MagicMock()

    monkeypatch.setenv("ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("ADMIN_PASSWORD", "SecurePass123")
    monkeypatch.setattr(
        "scripts.ops.bootstrap_admin.get_db_session",
        _mock_session,
    )

    with patch(
        "scripts.ops.bootstrap_admin.Container",
        return_value=container,
    ):
        result = await _bootstrap()

    assert result == 0
    assert existing.is_admin is True
    assert existing.is_active is True
    container.user_repository.update.assert_awaited_once_with(existing)


def test_bootstrap_requires_email_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing ADMIN_EMAIL causes the script to exit with code 1."""
    monkeypatch.delenv("ADMIN_EMAIL", raising=False)
    monkeypatch.setenv("ADMIN_PASSWORD", "SecurePass123")

    with pytest.raises(SystemExit) as exc_info:
        import asyncio

        asyncio.run(_bootstrap())

    assert exc_info.value.code == 1


def test_bootstrap_requires_password_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing ADMIN_PASSWORD causes the script to exit with code 1."""
    monkeypatch.setenv("ADMIN_EMAIL", "admin@example.com")
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)

    with pytest.raises(SystemExit) as exc_info:
        import asyncio

        asyncio.run(_bootstrap())

    assert exc_info.value.code == 1
