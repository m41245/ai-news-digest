from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from ai_news_digest.domain.enums.trend_status import TrendStatus
from ai_news_digest.domain.enums.trend_type import TrendType


@dataclass(slots=True)
class Trend:
    """
    Represents a detected trend in the platform.

    A trend captures increasing or sustained activity around a topic,
    company, category, or story theme over time. Scores are deterministic
    and derived from bounded signals.
    """

    id: UUID
    trend_type: TrendType
    canonical_key: str
    display_name: str
    status: TrendStatus
    trend_score: float
    momentum_score: float
    first_detected_at: datetime
    last_detected_at: datetime
    recent_activity: int
    baseline_activity: int
    source_count: int
    story_count: int
    event_count: int
    explanation: str
    trend_metadata: dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def create(
        cls,
        *,
        trend_type: TrendType,
        canonical_key: str,
        display_name: str,
        status: TrendStatus,
        trend_score: float,
        momentum_score: float,
        first_detected_at: datetime,
        last_detected_at: datetime,
        recent_activity: int,
        baseline_activity: int,
        source_count: int,
        story_count: int,
        event_count: int,
        explanation: str,
        trend_metadata: dict[str, str] | None = None,
    ) -> Trend:
        now = datetime.now(UTC)
        return cls(
            id=uuid4(),
            trend_type=trend_type,
            canonical_key=canonical_key,
            display_name=display_name,
            status=status,
            trend_score=max(0.0, min(100.0, trend_score)),
            momentum_score=max(0.0, min(100.0, momentum_score)),
            first_detected_at=first_detected_at,
            last_detected_at=last_detected_at,
            recent_activity=max(0, recent_activity),
            baseline_activity=max(0, baseline_activity),
            source_count=max(0, source_count),
            story_count=max(0, story_count),
            event_count=max(0, event_count),
            explanation=explanation,
            trend_metadata=trend_metadata or {},
            created_at=now,
            updated_at=now,
        )

    def touch(self) -> None:
        self.last_detected_at = datetime.now(UTC)
        self.updated_at = self.last_detected_at

    def update_scores(
        self,
        trend_score: float,
        momentum_score: float,
        status: TrendStatus,
        explanation: str,
    ) -> None:
        self.trend_score = max(0.0, min(100.0, trend_score))
        self.momentum_score = max(0.0, min(100.0, momentum_score))
        self.status = status
        self.explanation = explanation
        self.touch()


__all__ = ["Trend"]
