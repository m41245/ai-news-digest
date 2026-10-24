"""
Unit tests for UserCollectionRepository.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from ai_news_digest.infrastructure.database.repositories.user_collection_repository import (
    SqlAlchemyUserCollectionRepository,
)


@pytest.fixture
def mock_session() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def repository(mock_session: AsyncMock) -> SqlAlchemyUserCollectionRepository:
    return SqlAlchemyUserCollectionRepository(mock_session)


@pytest.mark.asyncio
async def test_user_collection_create(repository, mock_session) -> None:
    collection = MagicMock()
    collection.id = uuid4()
    collection.user_id = uuid4()
    collection.name = "name"
    collection.description = None
    collection.created_at = None
    collection.updated_at = None
    model = MagicMock()
    with (
        patch.object(repository, "_add_and_refresh", new_callable=AsyncMock, return_value=model),
        patch.object(repository, "_to_domain", return_value=collection),
    ):
        assert await repository.create(collection) == collection


@pytest.mark.asyncio
async def test_user_collection_list_by_user(repository, mock_session) -> None:
    model = MagicMock()
    count_result = MagicMock()
    count_result.scalar_one.return_value = 1
    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = [model]
    mock_session.execute.side_effect = [count_result, list_result]
    collection = MagicMock()
    with patch.object(repository, "_to_domain", return_value=collection):
        items, total = await repository.list_by_user(uuid4())
    assert items == [collection]
    assert total == 1


@pytest.mark.asyncio
async def test_user_collection_get_by_user_and_name_not_found(repository, mock_session) -> None:
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = result
    assert await repository.get_by_user_and_name(uuid4(), "name") is None


@pytest.mark.asyncio
async def test_user_collection_get_by_user_and_name_found(repository, mock_session) -> None:
    model = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = model
    mock_session.execute.return_value = result
    collection = MagicMock()
    with patch.object(repository, "_to_domain", return_value=collection):
        assert await repository.get_by_user_and_name(uuid4(), "name") == collection


@pytest.mark.asyncio
async def test_user_collection_delete_found(repository, mock_session) -> None:
    model = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = model
    mock_session.execute.return_value = result
    assert await repository.delete(uuid4(), uuid4()) is True


@pytest.mark.asyncio
async def test_user_collection_delete_not_found(repository, mock_session) -> None:
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = result
    assert await repository.delete(uuid4(), uuid4()) is False
