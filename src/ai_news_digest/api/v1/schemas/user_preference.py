from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field

from ai_news_digest.application.services.ranking.constants import (
    SourceTypePreferenceBehavior,
)


class UserPreferenceResponse(BaseModel):
    """Response schema for user preference profile."""

    user_id: str
    min_importance: float = 0.0
    min_confidence: float = 0.0
    feed_sort: str = "published_at"
    freshness_window_days: int | None = None
    preferred_source_types: list[str] = Field(default_factory=list)
    followed_companies: list[str] = Field(default_factory=list)
    followed_topics: list[str] = Field(default_factory=list)
    followed_categories: list[str] = Field(default_factory=list)
    muted_companies: list[str] = Field(default_factory=list)
    muted_topics: list[str] = Field(default_factory=list)
    muted_categories: list[str] = Field(default_factory=list)
    followed_sources: list[str] = Field(default_factory=list)
    muted_sources: list[str] = Field(default_factory=list)
    created_at: str | None = None
    updated_at: str | None = None


class UserPreferenceUpdateRequest(BaseModel):
    """Request schema for updating user preferences."""

    min_importance: Annotated[float | None, Field(default=None, ge=0.0, le=1.0)] = None
    min_confidence: Annotated[float | None, Field(default=None, ge=0.0, le=1.0)] = None
    feed_sort: Annotated[
        str | None,
        Field(default=None, pattern="^(published_at|importance|relevance)$"),
    ] = None
    freshness_window_days: Annotated[int | None, Field(default=None, ge=1)] = None
    preferred_source_types: Annotated[
        list[str] | None,
        Field(default=None, min_length=1),
    ] = None

    def normalize_preferred_source_types(self) -> tuple[str, ...] | None:
        if self.preferred_source_types is None:
            return None
        valid = SourceTypePreferenceBehavior.normalize(self.preferred_source_types)
        return tuple(valid) if valid else None


class PersonalizedTrendResponse(BaseModel):
    """Response schema for personalized trend items."""

    id: str
    trend_type: str
    display_name: str
    status: str
    trend_score: float
    momentum_score: float
    recent_activity: int
    baseline_activity: int
    source_count: int
    story_count: int
    event_count: int
    explanation: str
    personalized_relevance_score: float
    relevance_reasons: list[str]
    first_detected_at: str | None = None
    last_detected_at: str | None = None
    trend_metadata: dict[str, str] | None = None


__all__ = [
    "PersonalizedTrendResponse",
    "UserPreferenceResponse",
    "UserPreferenceUpdateRequest",
]
