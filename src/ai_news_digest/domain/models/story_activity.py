from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from ai_news_digest.domain.enums.story_activity_status import StoryActivityStatus


@dataclass(slots=True)
class StoryActivity:
    """
    Represents the current activity state of a story cluster.

    Activity is determined from recent publication velocity, source diversity,
    meaningful updates, and optional LLM ambiguity resolution.
    """

    id: UUID
    story_cluster_id: UUID
    status: StoryActivityStatus
    activity_score: float
    confidence: float
    explanation: str
    evaluated_at: datetime
    detection_version: str
    article_count_recent: int = 0
    unique_source_count_recent: int = 0
    recent_article_velocity: float = 0.0
    latest_article_at: datetime | None = None
    first_article_at: datetime | None = None
    recent_claim_count: int = 0
    recent_conflict_count: int = 0
    state_change_count: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def create(
        cls,
        *,
        story_cluster_id: UUID,
        status: StoryActivityStatus,
        activity_score: float,
        confidence: float,
        explanation: str,
        evaluated_at: datetime,
        detection_version: str,
        article_count_recent: int = 0,
        unique_source_count_recent: int = 0,
        recent_article_velocity: float = 0.0,
        latest_article_at: datetime | None = None,
        first_article_at: datetime | None = None,
        recent_claim_count: int = 0,
        recent_conflict_count: int = 0,
        state_change_count: int = 0,
    ) -> StoryActivity:
        now = datetime.now(UTC)
        return cls(
            id=uuid4(),
            story_cluster_id=story_cluster_id,
            status=status,
            activity_score=max(0.0, min(1.0, activity_score)),
            confidence=max(0.0, min(1.0, confidence)),
            explanation=explanation,
            evaluated_at=evaluated_at,
            detection_version=detection_version,
            article_count_recent=article_count_recent,
            unique_source_count_recent=unique_source_count_recent,
            recent_article_velocity=recent_article_velocity,
            latest_article_at=latest_article_at,
            first_article_at=first_article_at,
            recent_claim_count=recent_claim_count,
            recent_conflict_count=recent_conflict_count,
            state_change_count=state_change_count,
            created_at=now,
            updated_at=now,
        )


__all__ = ["StoryActivity"]
