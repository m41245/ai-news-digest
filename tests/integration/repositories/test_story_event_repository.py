from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from ai_news_digest.domain.enums.story_event_type import StoryEventType
from ai_news_digest.domain.models.story_event import StoryEvent
from ai_news_digest.infrastructure.database.repositories.story_event_repository import (
    StoryEventRepository,
)


@pytest.fixture
def event() -> StoryEvent:
    return StoryEvent.create(
        story_cluster_id=uuid4(),
        event_type=StoryEventType.ANNOUNCEMENT,
        title="Test Event",
        description="Test description",
        confidence=0.8,
        sequence=0,
    )


class TestStoryEventRepository:
    @pytest.mark.asyncio
    async def test_create_and_get(
        self,
        db_session: AsyncSession,
        event: StoryEvent,
    ) -> None:
        repo = StoryEventRepository(db_session)
        created = await repo.create(event)
        assert created.id is not None
        fetched = await repo.get_by_id(created.id)
        assert fetched is not None
        assert fetched.title == "Test Event"

    @pytest.mark.asyncio
    async def test_list_by_cluster_id(
        self,
        db_session: AsyncSession,
        event: StoryEvent,
    ) -> None:
        repo = StoryEventRepository(db_session)
        await repo.create(event)
        events = await repo.list_by_cluster_id(event.story_cluster_id)
        assert len(events) >= 1

    @pytest.mark.asyncio
    async def test_replace_for_cluster(
        self,
        db_session: AsyncSession,
        event: StoryEvent,
    ) -> None:
        repo = StoryEventRepository(db_session)
        await repo.create(event)
        new_event = StoryEvent.create(
            story_cluster_id=event.story_cluster_id,
            event_type=StoryEventType.OTHER,
            title="New Event",
            description="New desc",
            confidence=0.5,
            sequence=0,
        )
        result = await repo.replace_for_cluster(event.story_cluster_id, [new_event])
        assert len(result) == 1
        all_events = await repo.list_by_cluster_id(event.story_cluster_id)
        assert len(all_events) == 1
        assert all_events[0].title == "New Event"

    @pytest.mark.asyncio
    async def test_delete_for_cluster(
        self,
        db_session: AsyncSession,
        event: StoryEvent,
    ) -> None:
        repo = StoryEventRepository(db_session)
        await repo.create(event)
        deleted = await repo.delete_for_cluster(event.story_cluster_id)
        assert deleted >= 1
        events = await repo.list_by_cluster_id(event.story_cluster_id)
        assert events == []

    @pytest.mark.asyncio
    async def test_count_by_cluster_id(
        self,
        db_session: AsyncSession,
        event: StoryEvent,
    ) -> None:
        repo = StoryEventRepository(db_session)
        await repo.create(event)
        count = await repo.count_by_cluster_id(event.story_cluster_id)
        assert count >= 1


__all__ = ["TestStoryEventRepository"]
