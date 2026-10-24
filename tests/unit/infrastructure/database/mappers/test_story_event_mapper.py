"""
Unit tests for StoryEventMapper.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from ai_news_digest.domain.enums.story_event_type import StoryEventType
from ai_news_digest.domain.models.story_event import StoryEvent
from ai_news_digest.infrastructure.database.mappers.story_event_mapper import (
    StoryEventMapper,
)
from ai_news_digest.infrastructure.database.models.story_event_model import (
    StoryEventModel,
)


@pytest.fixture
def sample_story_event() -> StoryEvent:
    """Create a sample StoryEvent domain object."""
    return StoryEvent(
        id=uuid4(),
        story_cluster_id=uuid4(),
        event_type=StoryEventType.PRODUCT_LAUNCH,
        title="New model released",
        description="The latest model is now available.",
        confidence=0.94,
        event_time=datetime.now(UTC),
        representative_article_id=uuid4(),
        processing_metadata={"extractor": "event-v1", "tokens": "88"},
        schema_version="v1",
        sequence=2,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_story_event_model() -> StoryEventModel:
    """Create a sample StoryEventModel ORM entity."""
    return StoryEventModel(
        id=str(uuid4()),
        story_cluster_id=str(uuid4()),
        event_type=StoryEventType.PRODUCT_LAUNCH.value,
        title="New model released",
        description="The latest model is now available.",
        confidence=0.94,
        event_time=datetime.now(UTC),
        representative_article_id=str(uuid4()),
        processing_metadata='{"extractor": "event-v1", "tokens": "88"}',
        schema_version="v1",
        sequence=2,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def test_story_event_mapper_to_model(sample_story_event: StoryEvent) -> None:
    model = StoryEventMapper.to_model(sample_story_event)

    assert isinstance(model, StoryEventModel)
    assert model.id == str(sample_story_event.id)
    assert model.story_cluster_id == str(sample_story_event.story_cluster_id)
    assert model.event_type == sample_story_event.event_type.value
    assert model.title == sample_story_event.title
    assert model.description == sample_story_event.description
    assert model.confidence == sample_story_event.confidence
    assert model.event_time == sample_story_event.event_time
    assert model.representative_article_id == str(sample_story_event.representative_article_id)
    assert model.schema_version == sample_story_event.schema_version
    assert model.sequence == sample_story_event.sequence


def test_story_event_mapper_to_domain(sample_story_event_model: StoryEventModel) -> None:
    event = StoryEventMapper.to_domain(sample_story_event_model)

    assert isinstance(event, StoryEvent)
    assert event.id == UUID(sample_story_event_model.id)
    assert event.story_cluster_id == UUID(sample_story_event_model.story_cluster_id)
    assert event.event_type == StoryEventType(sample_story_event_model.event_type)
    assert event.title == sample_story_event_model.title
    assert event.description == sample_story_event_model.description
    assert event.confidence == sample_story_event_model.confidence
    assert event.event_time == sample_story_event_model.event_time
    assert event.representative_article_id == UUID(
        sample_story_event_model.representative_article_id
    )
    assert event.schema_version == sample_story_event_model.schema_version
    assert event.sequence == sample_story_event_model.sequence
    assert event.created_at == sample_story_event_model.created_at
    assert event.updated_at == sample_story_event_model.updated_at


def test_story_event_mapper_update_model(
    sample_story_event: StoryEvent, sample_story_event_model: StoryEventModel
) -> None:
    sample_story_event.title = "Updated title."
    sample_story_event.confidence = 0.5
    sample_story_event.event_type = StoryEventType.FUNDING
    sample_story_event.representative_article_id = None

    StoryEventMapper.update_model(sample_story_event_model, sample_story_event)

    assert sample_story_event_model.title == sample_story_event.title
    assert sample_story_event_model.confidence == sample_story_event.confidence
    assert sample_story_event_model.event_type == sample_story_event.event_type.value
    assert sample_story_event_model.representative_article_id is None
    assert sample_story_event_model.updated_at >= sample_story_event_model.created_at


def test_story_event_mapper_round_trip(sample_story_event: StoryEvent) -> None:
    model = StoryEventMapper.to_model(sample_story_event)
    restored = StoryEventMapper.to_domain(model)

    assert restored.id == sample_story_event.id
    assert restored.story_cluster_id == sample_story_event.story_cluster_id
    assert restored.event_type == sample_story_event.event_type
    assert restored.title == sample_story_event.title
    assert restored.description == sample_story_event.description
    assert restored.confidence == sample_story_event.confidence
    assert restored.event_time == sample_story_event.event_time
    assert restored.representative_article_id == sample_story_event.representative_article_id
    assert restored.processing_metadata == sample_story_event.processing_metadata
    assert restored.schema_version == sample_story_event.schema_version
    assert restored.sequence == sample_story_event.sequence
    # created_at/updated_at are not populated by to_model (DB server_default owns them),
    # so they are not part of the mapper round trip.


def test_story_event_mapper_to_model_with_none_representative_article_id(
    sample_story_event: StoryEvent,
) -> None:
    sample_story_event.representative_article_id = None
    model = StoryEventMapper.to_model(sample_story_event)
    assert model.representative_article_id is None


def test_story_event_mapper_to_domain_with_none_representative_article_id() -> None:
    model = StoryEventModel(
        id=str(uuid4()),
        story_cluster_id=str(uuid4()),
        event_type=StoryEventType.PRODUCT_LAUNCH.value,
        title="t",
        description="d",
        confidence=0.5,
        event_time=None,
        representative_article_id=None,
        processing_metadata=None,
        schema_version="v1",
        sequence=0,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    event = StoryEventMapper.to_domain(model)
    assert event.representative_article_id is None
    assert event.event_time is None
    assert event.processing_metadata == {}


def test_story_event_mapper_to_model_with_none_metadata(sample_story_event: StoryEvent) -> None:
    sample_story_event.processing_metadata = None
    model = StoryEventMapper.to_model(sample_story_event)
    assert model.processing_metadata is None


def test_story_event_mapper_to_domain_with_none_metadata() -> None:
    model = StoryEventModel(
        id=str(uuid4()),
        story_cluster_id=str(uuid4()),
        event_type=StoryEventType.PRODUCT_LAUNCH.value,
        title="t",
        description="d",
        confidence=0.5,
        event_time=None,
        representative_article_id=None,
        processing_metadata=None,
        schema_version="v1",
        sequence=0,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    event = StoryEventMapper.to_domain(model)
    assert event.processing_metadata == {}


def test_story_event_mapper_to_domain_invalid_event_type_falls_back() -> None:
    model = StoryEventModel(
        id=str(uuid4()),
        story_cluster_id=str(uuid4()),
        event_type="not_a_story_event_type",
        title="t",
        description="d",
        confidence=0.5,
        event_time=None,
        representative_article_id=None,
        processing_metadata=None,
        schema_version="v1",
        sequence=0,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    event = StoryEventMapper.to_domain(model)
    assert event.event_type == StoryEventType.OTHER


def test_story_event_mapper_to_domain_malformed_metadata_falls_back() -> None:
    model = StoryEventModel(
        id=str(uuid4()),
        story_cluster_id=str(uuid4()),
        event_type=StoryEventType.PRODUCT_LAUNCH.value,
        title="t",
        description="d",
        confidence=0.5,
        event_time=None,
        representative_article_id=None,
        processing_metadata="{not valid json",
        schema_version="v1",
        sequence=0,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    event = StoryEventMapper.to_domain(model)
    assert event.processing_metadata == {}


def test_story_event_mapper_update_model_with_none_metadata(
    sample_story_event: StoryEvent, sample_story_event_model: StoryEventModel
) -> None:
    sample_story_event.processing_metadata = None

    StoryEventMapper.update_model(sample_story_event_model, sample_story_event)

    assert sample_story_event_model.processing_metadata is None


def test_story_event_mapper_update_model_with_empty_metadata(
    sample_story_event: StoryEvent, sample_story_event_model: StoryEventModel
) -> None:
    sample_story_event.processing_metadata = {}

    StoryEventMapper.update_model(sample_story_event_model, sample_story_event)

    assert sample_story_event_model.processing_metadata is None
