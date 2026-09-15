from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from ai_news_digest.domain.enums.trend_status import TrendStatus
from ai_news_digest.domain.enums.trend_type import TrendType
from ai_news_digest.domain.models.trend import Trend
from ai_news_digest.infrastructure.database.models.trend_model import TrendModel


class TrendMapper:
    """Convert between Trend domain model and TrendModel database model."""

    @staticmethod
    def to_model(trend: Trend) -> TrendModel:
        return TrendModel(
            id=str(trend.id),
            trend_type=trend.trend_type.value,
            canonical_key=trend.canonical_key,
            display_name=trend.display_name,
            status=trend.status.value,
            trend_score=trend.trend_score,
            momentum_score=trend.momentum_score,
            first_detected_at=trend.first_detected_at,
            last_detected_at=trend.last_detected_at,
            recent_activity=trend.recent_activity,
            baseline_activity=trend.baseline_activity,
            source_count=trend.source_count,
            story_count=trend.story_count,
            event_count=trend.event_count,
            explanation=trend.explanation,
            trend_metadata=_serialize_metadata(trend.trend_metadata),
            created_at=trend.created_at,
            updated_at=trend.updated_at,
        )

    @staticmethod
    def to_domain(model: TrendModel) -> Trend:
        return Trend(
            id=UUID(model.id),
            trend_type=TrendType(model.trend_type),
            canonical_key=model.canonical_key,
            display_name=model.display_name,
            status=TrendStatus(model.status),
            trend_score=float(model.trend_score),
            momentum_score=float(model.momentum_score),
            first_detected_at=model.first_detected_at,
            last_detected_at=model.last_detected_at,
            recent_activity=int(model.recent_activity),
            baseline_activity=int(model.baseline_activity),
            source_count=int(model.source_count),
            story_count=int(model.story_count),
            event_count=int(model.event_count),
            explanation=model.explanation,
            trend_metadata=_deserialize_metadata(model.trend_metadata),
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def update_model(model: TrendModel, trend: Trend) -> None:
        model.trend_type = trend.trend_type.value
        model.canonical_key = trend.canonical_key
        model.display_name = trend.display_name
        model.status = trend.status.value
        model.trend_score = trend.trend_score
        model.momentum_score = trend.momentum_score
        model.last_detected_at = trend.last_detected_at
        model.recent_activity = trend.recent_activity
        model.baseline_activity = trend.baseline_activity
        model.source_count = trend.source_count
        model.story_count = trend.story_count
        model.event_count = trend.event_count
        model.explanation = trend.explanation
        model.trend_metadata = _serialize_metadata(trend.trend_metadata)
        model.updated_at = datetime.now(UTC)


def _serialize_metadata(metadata: dict[str, str]) -> str | None:
    import json

    if not metadata:
        return None
    try:
        return json.dumps(metadata)
    except (TypeError, ValueError):
        return None


def _deserialize_metadata(raw: str | None) -> dict[str, str]:
    import json

    if not raw:
        return {}
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return {str(k): str(v) for k, v in data.items()}
    except (TypeError, ValueError):
        pass
    return {}


__all__ = ["TrendMapper"]
