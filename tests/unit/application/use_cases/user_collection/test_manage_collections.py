"""
Unit tests for M96 user collection use cases.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from unittest.mock import AsyncMock

from ai_news_digest.application.use_cases.user_collection.manage_collections import (
    CreateCollectionUseCase,
    DeleteCollectionUseCase,
    ListCollectionsUseCase,
    UpdateCollectionUseCase,
)
from ai_news_digest.core.exceptions import DuplicateResourceError, ResourceNotFoundError
from ai_news_digest.domain.models.user_collection import UserCollection


def _make_collection(user_id: UUID, name: str = "Test") -> UserCollection:
    return UserCollection(
        id=uuid4(),
        user_id=user_id,
        name=name,
        description="Test description",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_create_collection():
    repo = AsyncMock()
    use_case = CreateCollectionUseCase(collection_repository=repo)

    user_id = uuid4()
    repo.get_by_user_and_name.return_value = None
    repo.create.return_value = _make_collection(user_id, "Saved")

    result = await use_case.execute(user_id=user_id, name="Saved", description="My saved stories")

    repo.get_by_user_and_name.assert_called_once_with(user_id, "Saved")
    repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_create_duplicate_collection_raises():
    repo = AsyncMock()
    use_case = CreateCollectionUseCase(collection_repository=repo)

    user_id = uuid4()
    repo.get_by_user_and_name.return_value = _make_collection(user_id, "Saved")

    with pytest.raises(DuplicateResourceError):
        await use_case.execute(user_id=user_id, name="Saved")

    repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_delete_collection():
    repo = AsyncMock()
    use_case = DeleteCollectionUseCase(collection_repository=repo)
    repo.delete.return_value = True

    await use_case.execute(user_id=uuid4(), collection_id=uuid4())

    repo.delete.assert_called_once()


@pytest.mark.asyncio
async def test_list_collections():
    repo = AsyncMock()
    use_case = ListCollectionsUseCase(collection_repository=repo)

    user_id = uuid4()
    collections = [_make_collection(user_id, "Saved"), _make_collection(user_id, "Watchlist")]
    repo.list_by_user.return_value = (collections, 2)

    items, total = await use_case.execute(user_id=user_id, limit=50, offset=0)

    assert len(items) == 2
    assert total == 2
