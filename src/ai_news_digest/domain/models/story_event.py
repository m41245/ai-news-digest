from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from ai_news_digest.domain.enums.story_event_type import StoryEventType


@dataclass(slots=True)
class StoryEvent:
    id: UUID
    story_cluster_id: UUID
    event_type: StoryEventType
    title: str
    description: str
    confidence: float
    event_time: datetime | None = None
    representative_article_id: UUID | None = None
    processing_metadata: dict[str, str] = field(default_factory=dict)
    schema_version: str = "v1"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    sequence: int = 0
    article_ids: tuple[UUID, ...] = ()
    claim_ids: tuple[UUID, ...] = ()

    @classmethod
    def create(
        cls,
        *,
        story_cluster_id: UUID,
        event_type: StoryEventType,
        title: str,
        description: str,
        confidence: float = 0.0,
        event_time: datetime | None = None,
        representative_article_id: UUID | None = None,
        processing_metadata: dict[str, str] | None = None,
        schema_version: str = "v1",
        sequence: int = 0,
        article_ids: tuple[UUID, ...] = (),
        claim_ids: tuple[UUID, ...] = (),
    ) -> StoryEvent:
        now = datetime.now(UTC)
        return cls(
            id=uuid4(),
            story_cluster_id=story_cluster_id,
            event_type=event_type,
            title=title,
            description=description,
            confidence=max(0.0, min(1.0, confidence)),
            event_time=event_time,
            representative_article_id=representative_article_id,
            processing_metadata=processing_metadata or {},
            schema_version=schema_version,
            created_at=now,
            updated_at=now,
            sequence=sequence,
            article_ids=article_ids,
            claim_ids=claim_ids,
        )


__all__ = ["StoryEvent"]
