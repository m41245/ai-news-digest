"""
Unit tests for M96 saved story use cases.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from unittest.mock import AsyncMock

from ai_news_digest.application.use_cases.saved_story.save_story import (
    ListSavedStoriesUseCase,
    SaveStoryUseCase,
    UnsaveStoryUseCase,
)
from ai_news_digest.core.exceptions import DuplicateResourceError, ResourceNotFoundError
from ai_news_digest.domain.models.saved_story import SavedStory


def _make_saved_story(user_id: UUID, story_cluster_id: UUID) -> SavedStory:
    return SavedStory(
        id=uuid4(),
        user_id=user_id,
        story_cluster_id=story_cluster_id,
        created_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_save_story_creates_saved_story():
    repo = AsyncMock()
    use_case = SaveStoryUseCase(saved_story_repository=repo)

    user_id = uuid4()
    story_cluster_id = uuid4()
    repo.get_by_user_and_story.return_value = None
    repo.create.return_value = _make_saved_story(user_id, story_cluster_id)

    result = await use_case.execute(user_id=user_id, story_cluster_id=story_cluster_id)

    repo.get_by_user_and_story.assert_called_once_with(user_id, story_cluster_id)
    repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_save_story_duplicate_raises():
    repo = AsyncMock()
    use_case = SaveStoryUseCase(saved_story_repository=repo)

    user_id = uuid4()
    story_cluster_id = uuid4()
    existing = _make_saved_story(user_id, story_cluster_id)
    repo.get_by_user_and_story.return_value = existing

    with pytest.raises(DuplicateResourceError):
        await use_case.execute(user_id=user_id, story_cluster_id=story_cluster_id)

    repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_unsave_story_removes_saved_story():
    repo = AsyncMock()
    use_case = UnsaveStoryUseCase(saved_story_repository=repo)
    repo.delete.return_value = True

    await use_case.execute(user_id=uuid4(), story_cluster_id=uuid4())

    repo.delete.assert_called_once()


@pytest.mark.asyncio
async def test_unsave_story_not_found_raises():
    repo = AsyncMock()
    use_case = UnsaveStoryUseCase(saved_story_repository=repo)
    repo.delete.return_value = False

    with pytest.raises(ResourceNotFoundError):
        await use_case.execute(user_id=uuid4(), story_cluster_id=uuid4())


@pytest.mark.asyncio
async def test_list_saved_stories():
    repo = AsyncMock()
    use_case = ListSavedStoriesUseCase(saved_story_repository=repo)

    user_id = uuid4()
    saved = [_make_saved_story(user_id, uuid4()), _make_saved_story(user_id, uuid4())]
    repo.list_by_user.return_value = (saved, 2)

    items, total = await use_case.execute(user_id=user_id, limit=20, offset=0)

    assert len(items) == 2
    assert total == 2
