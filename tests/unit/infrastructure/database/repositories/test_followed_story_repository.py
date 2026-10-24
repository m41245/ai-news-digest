"""
Unit tests for FollowedStoryRepository.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from ai_news_digest.domain.models.followed_story import FollowedStory
from ai_news_digest.infrastructure.database.repositories.followed_story_repository import (
    SqlAlchemyFollowedStoryRepository,
)


@pytest.fixture
def mock_session() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def repository(mock_session: AsyncMock) -> SqlAlchemyFollowedStoryRepository:
    return SqlAlchemyFollowedStoryRepository(mock_session)


@pytest.mark.asyncio
async def test_followed_story_create(repository, mock_session) -> None:
    story = MagicMock(spec=FollowedStory)
    story.id = uuid4()
    story.user_id = uuid4()
    story.story_cluster_id = uuid4()
    story.created_at = None
    model = MagicMock()
    with (
        patch.object(repository, "_add_and_refresh", new_callable=AsyncMock, return_value=model),
        patch.object(repository, "_to_domain", return_value=story),
    ):
        assert await repository.create(story) == story


@pytest.mark.asyncio
async def test_followed_story_get_by_user_and_story_not_found(repository, mock_session) -> None:
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = result
    assert await repository.get_by_user_and_story(uuid4(), uuid4()) is None


@pytest.mark.asyncio
async def test_followed_story_get_by_user_and_story_found(repository, mock_session) -> None:
    model = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = model
    mock_session.execute.return_value = result
    story = MagicMock()
    with patch.object(repository, "_to_domain", return_value=story):
        assert await repository.get_by_user_and_story(uuid4(), uuid4()) == story


@pytest.mark.asyncio
async def test_followed_story_list_by_user(repository, mock_session) -> None:
    model = MagicMock()
    count_result = MagicMock()
    count_result.scalar_one.return_value = 1
    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = [model]
    mock_session.execute.side_effect = [count_result, list_result]
    story = MagicMock()
    with patch.object(repository, "_to_domain", return_value=story):
        items, total = await repository.list_by_user(uuid4())
    assert items == [story]
    assert total == 1


@pytest.mark.asyncio
async def test_followed_story_delete_found(repository, mock_session) -> None:
    model = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = model
    mock_session.execute.return_value = result
    assert await repository.delete(uuid4(), uuid4()) is True


@pytest.mark.asyncio
async def test_followed_story_delete_not_found(repository, mock_session) -> None:
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = result
    assert await repository.delete(uuid4(), uuid4()) is False
