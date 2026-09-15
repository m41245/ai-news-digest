from __future__ import annotations

from uuid import uuid4

from ai_news_digest.domain.enums.story_event_type import StoryEventType
from ai_news_digest.domain.models.story_event import StoryEvent


def test_confidence_clamped() -> None:
    event = StoryEvent.create(
        story_cluster_id=uuid4(),
        event_type=StoryEventType.OTHER,
        title="Test",
        description="Desc",
        confidence=1.5,
    )
    assert event.confidence == 1.0
    event2 = StoryEvent.create(
        story_cluster_id=uuid4(),
        event_type=StoryEventType.OTHER,
        title="Test",
        description="Desc",
        confidence=-0.5,
    )
    assert event2.confidence == 0.0


def test_create_event_defaults() -> None:
    event = StoryEvent.create(
        story_cluster_id=uuid4(),
        event_type=StoryEventType.ANNOUNCEMENT,
        title="Test",
        description="Desc",
    )
    assert event.confidence == 0.0
    assert event.sequence == 0
    assert event.article_ids == ()
    assert event.claim_ids == ()


def test_event_type_enum() -> None:
    assert StoryEventType.ANNOUNCEMENT.value == "announcement"
    assert StoryEventType.OTHER.value == "other"


__all__ = [
    "test_confidence_clamped",
    "test_create_event_defaults",
    "test_event_type_enum",
]
