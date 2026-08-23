"""
Unit tests for BaseRepository.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from ai_news_digest.core.exceptions import DatabaseError
from ai_news_digest.infrastructure.database.repositories.base_repository import BaseRepository


@pytest.fixture
def mock_session() -> AsyncMock:
    """Create a mock AsyncSession."""
    session = AsyncMock()
    return session


@pytest.fixture
def repository(mock_session: AsyncMock) -> BaseRepository:
    """Create a BaseRepository instance."""
    return BaseRepository(mock_session)


@pytest.mark.asyncio
async def test_base_repository_add(repository: BaseRepository, mock_session: AsyncMock) -> None:
    """Test _add method."""
    model = MagicMock()
    result = await repository._add(model)

    mock_session.add.assert_called_once_with(model)
    assert result == model


@pytest.mark.asyncio
async def test_base_repository_add_all(repository: BaseRepository, mock_session: AsyncMock) -> None:
    """Test _add_all method."""
    models = [MagicMock(), MagicMock()]
    await repository._add_all(models)

    mock_session.add_all.assert_called_once()


@pytest.mark.asyncio
async def test_base_repository_flush(repository: BaseRepository, mock_session: AsyncMock) -> None:
    """Test _flush method."""
    await repository._flush()

    mock_session.flush.assert_called_once()


@pytest.mark.asyncio
async def test_base_repository_commit(repository: BaseRepository, mock_session: AsyncMock) -> None:
    """Test _commit method."""
    await repository._commit()

    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_base_repository_rollback(
    repository: BaseRepository, mock_session: AsyncMock
) -> None:
    """Test _rollback method."""
    await repository._rollback()

    mock_session.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_base_repository_refresh(repository: BaseRepository, mock_session: AsyncMock) -> None:
    """Test _refresh method."""
    model = MagicMock()
    result = await repository._refresh(model)

    mock_session.refresh.assert_called_once_with(model)
    assert result == model


@pytest.mark.asyncio
async def test_base_repository_add_and_refresh(
    repository: BaseRepository, mock_session: AsyncMock
) -> None:
    """Test _add_and_refresh method."""
    model = MagicMock()
    result = await repository._add_and_refresh(model)

    mock_session.add.assert_called_once_with(model)
    mock_session.commit.assert_called_once()
    mock_session.refresh.assert_called_once_with(model)
    assert result == model


@pytest.mark.asyncio
async def test_base_repository_delete(repository: BaseRepository, mock_session: AsyncMock) -> None:
    """Test _delete method."""
    model = MagicMock()
    await repository._delete(model)

    mock_session.delete.assert_called_once_with(model)
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_base_repository_flush_error_propagates_as_database_error(
    repository: BaseRepository, mock_session: AsyncMock
) -> None:
    """Test _flush wraps exceptions in DatabaseError."""
    mock_session.flush.side_effect = Exception("flush failed")

    with pytest.raises(DatabaseError, match="Database flush failed"):
        await repository._flush()


@pytest.mark.asyncio
async def test_base_repository_rollback_error_propagates_as_database_error(
    repository: BaseRepository, mock_session: AsyncMock
) -> None:
    """Test _rollback wraps exceptions in DatabaseError."""
    mock_session.rollback.side_effect = Exception("rollback failed")

    with pytest.raises(DatabaseError, match="Database rollback failed"):
        await repository._rollback()


@pytest.mark.asyncio
async def test_base_repository_refresh_error_propagates_as_database_error(
    repository: BaseRepository, mock_session: AsyncMock
) -> None:
    """Test _refresh wraps exceptions in DatabaseError."""
    mock_session.refresh.side_effect = Exception("refresh failed")
    model = MagicMock()

    with pytest.raises(DatabaseError, match="Database refresh failed"):
        await repository._refresh(model)


@pytest.mark.asyncio
async def test_base_repository_delete_error_propagates_as_database_error(
    repository: BaseRepository, mock_session: AsyncMock
) -> None:
    """Test _delete wraps exceptions in DatabaseError."""
    mock_session.delete.side_effect = Exception("delete failed")
    model = MagicMock()

    with pytest.raises(DatabaseError, match="Database delete failed"):
        await repository._delete(model)
