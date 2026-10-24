"""
Unit tests for UserRepository.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from ai_news_digest.domain.models.user import User
from ai_news_digest.infrastructure.database.repositories.user_repository import UserRepository


@pytest.fixture
def mock_session() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def repository(mock_session: AsyncMock) -> UserRepository:
    return UserRepository(mock_session)


@pytest.mark.asyncio
async def test_user_repository_get_by_id_found(
    repository: UserRepository, mock_session: AsyncMock
) -> None:
    model = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = model
    mock_session.execute.return_value = result
    user = User.create(email="a@example.com", hashed_password="hashed")  # noqa: S106
    with patch(
        "ai_news_digest.infrastructure.database.repositories.user_repository.UserMapper.to_domain",
        return_value=user,
    ):
        assert await repository.get_by_id(uuid4()) == user


@pytest.mark.asyncio
async def test_user_repository_get_by_id_not_found(
    repository: UserRepository, mock_session: AsyncMock
) -> None:
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = result
    assert await repository.get_by_id(uuid4()) is None


@pytest.mark.asyncio
async def test_user_repository_get_by_email_found(
    repository: UserRepository, mock_session: AsyncMock
) -> None:
    model = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = model
    mock_session.execute.return_value = result
    user = User.create(email="a@example.com", hashed_password="hashed")  # noqa: S106
    with patch(
        "ai_news_digest.infrastructure.database.repositories.user_repository.UserMapper.to_domain",
        return_value=user,
    ):
        assert await repository.get_by_email("a@example.com") == user


@pytest.mark.asyncio
async def test_user_repository_get_by_email_not_found(
    repository: UserRepository, mock_session: AsyncMock
) -> None:
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = result
    assert await repository.get_by_email("missing@example.com") is None
