"""
Unit tests for TrendMapper.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from ai_news_digest.domain.enums.trend_status import TrendStatus
from ai_news_digest.domain.enums.trend_type import TrendType
from ai_news_digest.domain.models.trend import Trend
from ai_news_digest.infrastructure.database.mappers.trend_mapper import TrendMapper
from ai_news_digest.infrastructure.database.models.trend_model import TrendModel


@pytest.fixture
def sample_trend() -> Trend:
    """Create a sample Trend domain object."""
    return Trend(
        id=uuid4(),
        trend_type=TrendType.TOPIC_TREND,
        canonical_key="ai",
        display_name="Artificial Intelligence",
        status=TrendStatus.RISING,
        trend_score=75.5,
        momentum_score=10.0,
        first_detected_at=datetime.now(UTC),
        last_detected_at=datetime.now(UTC),
        recent_activity=100,
        baseline_activity=50,
        source_count=5,
        story_count=3,
        event_count=2,
        explanation="Sustained activity around AI topics.",
        trend_metadata={"extractor": "trend-v1", "signals": "42"},
        related_company_ids={uuid4(), uuid4()},
        related_topic_ids={uuid4()},
        related_category_ids={uuid4(), uuid4(), uuid4()},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_trend_model() -> TrendModel:
    """Create a sample TrendModel ORM entity."""
    return TrendModel(
        id=str(uuid4()),
        trend_type=TrendType.TOPIC_TREND.value,
        canonical_key="ai",
        display_name="Artificial Intelligence",
        status=TrendStatus.RISING.value,
        trend_score=75.5,
        momentum_score=10.0,
        first_detected_at=datetime.now(UTC),
        last_detected_at=datetime.now(UTC),
        recent_activity=100,
        baseline_activity=50,
        source_count=5,
        story_count=3,
        event_count=2,
        explanation="Sustained activity around AI topics.",
        trend_metadata='{"extractor": "trend-v1", "signals": "42"}',
        related_company_ids=",".join(str(i) for i in sorted({uuid4(), uuid4()})),
        related_topic_ids=str(uuid4()),
        related_category_ids=",".join(str(i) for i in sorted({uuid4(), uuid4(), uuid4()})),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def test_trend_mapper_to_model(sample_trend: Trend) -> None:
    model = TrendMapper.to_model(sample_trend)

    assert isinstance(model, TrendModel)
    assert model.id == str(sample_trend.id)
    assert model.trend_type == sample_trend.trend_type.value
    assert model.canonical_key == sample_trend.canonical_key
    assert model.display_name == sample_trend.display_name
    assert model.status == sample_trend.status.value
    assert model.trend_score == sample_trend.trend_score
    assert model.momentum_score == sample_trend.momentum_score
    assert model.first_detected_at == sample_trend.first_detected_at
    assert model.last_detected_at == sample_trend.last_detected_at
    assert model.recent_activity == sample_trend.recent_activity
    assert model.baseline_activity == sample_trend.baseline_activity
    assert model.source_count == sample_trend.source_count
    assert model.story_count == sample_trend.story_count
    assert model.event_count == sample_trend.event_count
    assert model.explanation == sample_trend.explanation


def test_trend_mapper_to_domain(sample_trend_model: TrendModel) -> None:
    trend = TrendMapper.to_domain(sample_trend_model)

    assert isinstance(trend, Trend)
    assert trend.id == UUID(sample_trend_model.id)
    assert trend.trend_type == TrendType(sample_trend_model.trend_type)
    assert trend.canonical_key == sample_trend_model.canonical_key
    assert trend.display_name == sample_trend_model.display_name
    assert trend.status == TrendStatus(sample_trend_model.status)
    assert trend.trend_score == float(sample_trend_model.trend_score)
    assert trend.momentum_score == float(sample_trend_model.momentum_score)
    assert trend.first_detected_at == sample_trend_model.first_detected_at
    assert trend.last_detected_at == sample_trend_model.last_detected_at
    assert trend.recent_activity == int(sample_trend_model.recent_activity)
    assert trend.baseline_activity == int(sample_trend_model.baseline_activity)
    assert trend.source_count == int(sample_trend_model.source_count)
    assert trend.story_count == int(sample_trend_model.story_count)
    assert trend.event_count == int(sample_trend_model.event_count)
    assert trend.explanation == sample_trend_model.explanation


def test_trend_mapper_update_model(sample_trend: Trend, sample_trend_model: TrendModel) -> None:
    sample_trend.trend_score = 90.0
    sample_trend.status = TrendStatus.SUSTAINED
    sample_trend.recent_activity = 200
    sample_trend.explanation = "Updated explanation."

    TrendMapper.update_model(sample_trend_model, sample_trend)

    assert sample_trend_model.trend_score == sample_trend.trend_score
    assert sample_trend_model.status == sample_trend.status.value
    assert sample_trend_model.recent_activity == sample_trend.recent_activity
    assert sample_trend_model.explanation == sample_trend.explanation
    assert sample_trend_model.updated_at >= sample_trend_model.created_at


def test_trend_mapper_round_trip(sample_trend: Trend) -> None:
    model = TrendMapper.to_model(sample_trend)
    restored = TrendMapper.to_domain(model)

    assert restored.id == sample_trend.id
    assert restored.trend_type == sample_trend.trend_type
    assert restored.canonical_key == sample_trend.canonical_key
    assert restored.display_name == sample_trend.display_name
    assert restored.status == sample_trend.status
    assert restored.trend_score == sample_trend.trend_score
    assert restored.momentum_score == sample_trend.momentum_score
    assert restored.first_detected_at == sample_trend.first_detected_at
    assert restored.last_detected_at == sample_trend.last_detected_at
    assert restored.recent_activity == sample_trend.recent_activity
    assert restored.baseline_activity == sample_trend.baseline_activity
    assert restored.source_count == sample_trend.source_count
    assert restored.story_count == sample_trend.story_count
    assert restored.event_count == sample_trend.event_count
    assert restored.explanation == sample_trend.explanation
    assert restored.trend_metadata == sample_trend.trend_metadata
    assert restored.related_company_ids == sample_trend.related_company_ids
    assert restored.related_topic_ids == sample_trend.related_topic_ids
    assert restored.related_category_ids == sample_trend.related_category_ids
    assert restored.created_at == sample_trend.created_at
    assert restored.updated_at == sample_trend.updated_at


def test_trend_mapper_to_model_with_none_metadata(sample_trend: Trend) -> None:
    sample_trend.trend_metadata = None
    model = TrendMapper.to_model(sample_trend)
    assert model.trend_metadata is None


def test_trend_mapper_to_domain_with_none_metadata() -> None:
    model = TrendModel(
        id=str(uuid4()),
        trend_type=TrendType.TOPIC_TREND.value,
        canonical_key="ai",
        display_name="Artificial Intelligence",
        status=TrendStatus.RISING.value,
        trend_score=1.0,
        momentum_score=1.0,
        first_detected_at=datetime.now(UTC),
        last_detected_at=datetime.now(UTC),
        recent_activity=0,
        baseline_activity=0,
        source_count=0,
        story_count=0,
        event_count=0,
        explanation="x",
        trend_metadata=None,
        related_company_ids=None,
        related_topic_ids=None,
        related_category_ids=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    trend = TrendMapper.to_domain(model)
    assert trend.trend_metadata == {}
    assert trend.related_company_ids == frozenset()
    assert trend.related_topic_ids == frozenset()
    assert trend.related_category_ids == frozenset()


def test_trend_mapper_to_domain_malformed_metadata_falls_back() -> None:
    model = TrendModel(
        id=str(uuid4()),
        trend_type=TrendType.TOPIC_TREND.value,
        canonical_key="ai",
        display_name="Artificial Intelligence",
        status=TrendStatus.RISING.value,
        trend_score=1.0,
        momentum_score=1.0,
        first_detected_at=datetime.now(UTC),
        last_detected_at=datetime.now(UTC),
        recent_activity=0,
        baseline_activity=0,
        source_count=0,
        story_count=0,
        event_count=0,
        explanation="x",
        trend_metadata="{not valid json",
        related_company_ids=None,
        related_topic_ids=None,
        related_category_ids=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    trend = TrendMapper.to_domain(model)
    assert trend.trend_metadata == {}


def test_trend_mapper_to_domain_invalid_trend_type_raises() -> None:
    model = TrendModel(
        id=str(uuid4()),
        trend_type="not_a_trend_type",
        canonical_key="ai",
        display_name="Artificial Intelligence",
        status=TrendStatus.RISING.value,
        trend_score=1.0,
        momentum_score=1.0,
        first_detected_at=datetime.now(UTC),
        last_detected_at=datetime.now(UTC),
        recent_activity=0,
        baseline_activity=0,
        source_count=0,
        story_count=0,
        event_count=0,
        explanation="x",
        trend_metadata=None,
        related_company_ids=None,
        related_topic_ids=None,
        related_category_ids=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    with pytest.raises(ValueError):
        TrendMapper.to_domain(model)


def test_trend_mapper_to_domain_invalid_trend_status_raises() -> None:
    model = TrendModel(
        id=str(uuid4()),
        trend_type=TrendType.TOPIC_TREND.value,
        canonical_key="ai",
        display_name="Artificial Intelligence",
        status="not_a_trend_status",
        trend_score=1.0,
        momentum_score=1.0,
        first_detected_at=datetime.now(UTC),
        last_detected_at=datetime.now(UTC),
        recent_activity=0,
        baseline_activity=0,
        source_count=0,
        story_count=0,
        event_count=0,
        explanation="x",
        trend_metadata=None,
        related_company_ids=None,
        related_topic_ids=None,
        related_category_ids=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    with pytest.raises(ValueError):
        TrendMapper.to_domain(model)


def test_trend_mapper_update_model_with_none_metadata(
    sample_trend: Trend, sample_trend_model: TrendModel
) -> None:
    sample_trend.trend_metadata = None

    TrendMapper.update_model(sample_trend_model, sample_trend)

    assert sample_trend_model.trend_metadata is None


def test_trend_mapper_update_model_with_empty_metadata(
    sample_trend: Trend, sample_trend_model: TrendModel
) -> None:
    sample_trend.trend_metadata = {}

    TrendMapper.update_model(sample_trend_model, sample_trend)

    assert sample_trend_model.trend_metadata is None


def test_trend_mapper_to_model_empty_related_ids_serialized_as_none(
    sample_trend: Trend,
) -> None:
    sample_trend.related_company_ids = frozenset()
    sample_trend.related_topic_ids = frozenset()
    sample_trend.related_category_ids = frozenset()

    model = TrendMapper.to_model(sample_trend)

    assert model.related_company_ids is None
    assert model.related_topic_ids is None
    assert model.related_category_ids is None


def test_trend_mapper_to_domain_malformed_related_ids_are_skipped() -> None:
    valid_id = uuid4()
    model = TrendModel(
        id=str(uuid4()),
        trend_type=TrendType.TOPIC_TREND.value,
        canonical_key="ai",
        display_name="Artificial Intelligence",
        status=TrendStatus.RISING.value,
        trend_score=1.0,
        momentum_score=1.0,
        first_detected_at=datetime.now(UTC),
        last_detected_at=datetime.now(UTC),
        recent_activity=0,
        baseline_activity=0,
        source_count=0,
        story_count=0,
        event_count=0,
        explanation="x",
        trend_metadata=None,
        related_company_ids=f"not-a-uuid,{valid_id}",
        related_topic_ids=None,
        related_category_ids=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    trend = TrendMapper.to_domain(model)
    assert trend.related_company_ids == frozenset({valid_id})


def test_trend_mapper_to_model_metadata_serialization_failure(
    sample_trend: Trend,
) -> None:
    sample_trend.trend_metadata = {"key": object()}  # type: ignore[arg-type]

    model = TrendMapper.to_model(sample_trend)

    assert model.trend_metadata is None


def test_trend_mapper_to_domain_metadata_decoding_to_non_dict_is_empty() -> None:
    model = TrendModel(
        id=str(uuid4()),
        trend_type=TrendType.TOPIC_TREND.value,
        canonical_key="ai",
        display_name="Artificial Intelligence",
        status=TrendStatus.RISING.value,
        trend_score=1.0,
        momentum_score=1.0,
        first_detected_at=datetime.now(UTC),
        last_detected_at=datetime.now(UTC),
        recent_activity=0,
        baseline_activity=0,
        source_count=0,
        story_count=0,
        event_count=0,
        explanation="x",
        trend_metadata="[1, 2, 3]",
        related_company_ids=None,
        related_topic_ids=None,
        related_category_ids=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    trend = TrendMapper.to_domain(model)
    assert trend.trend_metadata == {}
