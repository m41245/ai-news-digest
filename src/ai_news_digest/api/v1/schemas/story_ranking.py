"""
API schemas for M68 story ranking and Top Story.
"""

from __future__ import annotations

from pydantic import BaseModel


class StoryRankingSignalResponse(BaseModel):
    """Individual signal contribution in a cluster's ranking."""

    name: str
    normalized_value: float
    weight: float
    contribution: float
    explanation: str


class StoryRankingResponse(BaseModel):
    """Ranking result for a single StoryCluster."""

    story_cluster_id: str
    score: float
    rank: int
    signals: list[StoryRankingSignalResponse]
    explanation: str


class TopStoryResponse(BaseModel):
    """Top Story selection result."""

    top_story_cluster_id: str | None
    top_story_score: float | None
    total_candidates: int
    eligible_candidates: int
    ranking_window_start: str | None
    ranking_window_end: str | None
    generated_at: str


class RankedStoriesResponse(BaseModel):
    """Paginated ranked stories response."""

    items: list[StoryRankingResponse]
    total: int
    limit: int
    offset: int


__all__ = [
    "RankedStoriesResponse",
    "StoryRankingResponse",
    "StoryRankingSignalResponse",
    "TopStoryResponse",
]
