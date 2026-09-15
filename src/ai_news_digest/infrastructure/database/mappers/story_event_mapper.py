from __future__ import annotations

from uuid import UUID

from ai_news_digest.domain.enums.story_event_type import StoryEventType
from ai_news_digest.domain.models.story_event import StoryEvent
from ai_news_digest.infrastructure.database.models.story_event_model import (
    StoryEventModel,
)


class StoryEventMapper:
    @staticmethod
    def to_model(event: StoryEvent) -> StoryEventModel:
        import json

        rep_id = (
            str(event.representative_article_id)
            if event.representative_article_id is not None
            else None
        )
        metadata = (
            json.dumps(event.processing_metadata) if event.processing_metadata else None
        )
        return StoryEventModel(
            id=str(event.id),
            story_cluster_id=str(event.story_cluster_id),
            event_type=event.event_type.value,
            title=event.title,
            description=event.description,
            confidence=event.confidence,
            event_time=event.event_time,
            representative_article_id=rep_id,
            processing_metadata=metadata,
            schema_version=event.schema_version,
            sequence=event.sequence,
        )

    @staticmethod
    def update_model(model: StoryEventModel, event: StoryEvent) -> None:
        import json
        from datetime import UTC, datetime

        rep_id = (
            str(event.representative_article_id)
            if event.representative_article_id is not None
            else None
        )
        metadata = (
            json.dumps(event.processing_metadata) if event.processing_metadata else None
        )
        model.event_type = event.event_type.value
        model.title = event.title
        model.description = event.description
        model.confidence = event.confidence
        model.event_time = event.event_time
        model.representative_article_id = rep_id
        model.processing_metadata = metadata
        model.schema_version = event.schema_version
        model.sequence = event.sequence
        model.updated_at = datetime.now(UTC)

    @staticmethod
    def to_domain(model: StoryEventModel) -> StoryEvent:
        import json

        try:
            event_type = StoryEventType(model.event_type)
        except ValueError:
            event_type = StoryEventType.OTHER
        metadata = {}
        if model.processing_metadata:
            try:
                metadata = json.loads(model.processing_metadata)
            except (json.JSONDecodeError, TypeError):
                metadata = {}
        rep_id = (
            UUID(model.representative_article_id)
            if model.representative_article_id is not None
            else None
        )
        return StoryEvent(
            id=UUID(model.id),
            story_cluster_id=UUID(model.story_cluster_id),
            event_type=event_type,
            title=model.title,
            description=model.description,
            confidence=model.confidence,
            event_time=model.event_time,
            representative_article_id=rep_id,
            processing_metadata=metadata,
            schema_version=model.schema_version,
            created_at=model.created_at,
            updated_at=model.updated_at,
            sequence=model.sequence,
        )


__all__ = ["StoryEventMapper"]
