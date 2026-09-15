"""
Integration tests for StoryActivityRepository.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from ai_news_digest.domain.enums.story_activity_status import StoryActivityStatus
from ai_news_digest.domain.models.story_activity import StoryActivity
from ai_news_digest.infrastructure.database.repositories.story_activity_repository import (
    StoryActivityRepository,
)


@pytest.fixture
def activity() -> StoryActivity:
    return StoryActivity.create(
        story_cluster_id=uuid4(),
        status=StoryActivityStatus.DEVELOPING,
        activity_score=0.6,
        confidence=0.7,
        explanation="Moderate activity",
        evaluated_at=datetime.now(UTC),
        detection_version="v1",
    )


class TestStoryActivityRepository:
    @pytest.mark.asyncio
    async def test_create_and_get(
        self,
        db_session: AsyncSession,
        activity: StoryActivity,
    ) -> None:
        repository = StoryActivityRepository(db_session)
        created = await repository.create(activity)
        assert created.id is not None

        fetched = await repository.get_by_story_cluster_id(created.story_cluster_id)
        assert fetched is not None
        assert fetched.status == StoryActivityStatus.DEVELOPING
        assert fetched.activity_score == 0.6

    @pytest.mark.asyncio
    async def test_upsert_creates_when_missing(
        self,
        db_session: AsyncSession,
        activity: StoryActivity,
    ) -> None:
        repository = StoryActivityRepository(db_session)
        result = await repository.upsert(activity)
        assert result.id is not None
        assert result.status == StoryActivityStatus.DEVELOPING

    @pytest.mark.asyncio
    async def test_upsert_updates_existing(
        self,
        db_session: AsyncSession,
        activity: StoryActivity,
    ) -> None:
        repository = StoryActivityRepository(db_session)
        created = await repository.create(activity)

        updated = StoryActivity.create(
            story_cluster_id=created.story_cluster_id,
            status=StoryActivityStatus.BREAKING,
            activity_score=0.9,
            confidence=0.9,
            explanation="Updated",
            evaluated_at=datetime.now(UTC),
            detection_version="v1",
        )
        result = await repository.upsert(updated)
        assert result.status == StoryActivityStatus.BREAKING
        assert result.activity_score == 0.9

    @pytest.mark.asyncio
    async def test_list_recent(
        self,
        db_session: AsyncSession,
        activity: StoryActivity,
    ) -> None:
        repository = StoryActivityRepository(db_session)
        await repository.create(activity)
        results = await repository.list_recent(limit=10)
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_count(
        self,
        db_session: AsyncSession,
        activity: StoryActivity,
    ) -> None:
        repository = StoryActivityRepository(db_session)
        await repository.create(activity)
        count = await repository.count()
        assert count >= 1


__all__ = ["TestStoryActivityRepository"]
