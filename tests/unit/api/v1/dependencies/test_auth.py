"""
Unit tests for authentication dependencies.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from ai_news_digest.api.v1.dependencies.auth import (
    get_current_active_user,
    get_current_user,
)
from ai_news_digest.core.exceptions import AuthenticationError
from ai_news_digest.domain.models.user import User


@pytest.fixture
def mock_session() -> AsyncSession:
    """Create a mock AsyncSession."""
    session = MagicMock(spec=AsyncSession)
    return session


@pytest.fixture
def mock_container() -> MagicMock:
    container = MagicMock()
    return container


@pytest.mark.asyncio
async def test_get_current_user_valid_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test get_current_user with valid token."""
    from ai_news_digest.infrastructure.auth.jwt import create_access_token

    token = create_access_token(subject="user-123")

    user = User(
        id=uuid4(),
        email="test@example.com",
        hashed_password="hashed",
        is_active=True,
        is_admin=True,
        created_at=datetime.now(UTC),
    )

    mock_session = MagicMock()
    mock_container = MagicMock()
    mock_container.user_repository.get_by_id = AsyncMock(return_value=user)

    monkeypatch.setattr(
        "ai_news_digest.api.v1.dependencies.auth.get_db_session",
        lambda: mock_session,
    )
    monkeypatch.setattr(
        "ai_news_digest.api.v1.dependencies.auth.Container",
        lambda s: mock_container,
    )

    result = await get_current_user(token, mock_session)

    assert result.email == "test@example.com"


@pytest.mark.asyncio
async def test_get_current_user_invalid_token() -> None:
    """Test get_current_user raises on invalid token."""
    mock_session = MagicMock()

    with pytest.raises(AuthenticationError):
        await get_current_user("invalid-token", mock_session)


@pytest.mark.asyncio
async def test_get_current_active_user_success() -> None:
    """Test get_current_active_user with active user."""
    user = User(
        id=uuid4(),
        email="test@example.com",
        hashed_password="hashed",
        is_active=True,
        is_admin=True,
        created_at=datetime.now(UTC),
    )

    result = await get_current_active_user(user)

    assert result.is_active is True


@pytest.mark.asyncio
async def test_get_current_active_user_inactive() -> None:
    """Test get_current_active_user raises on inactive user."""
    user = User(
        id=uuid4(),
        email="test@example.com",
        hashed_password="hashed",
        is_active=False,
        is_admin=True,
        created_at=datetime.now(UTC),
    )

    with pytest.raises(AuthenticationError, match="Inactive user"):
        await get_current_active_user(user)
