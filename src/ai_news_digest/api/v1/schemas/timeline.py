from __future__ import annotations

from pydantic import BaseModel


class StoryEventResponse(BaseModel):
    id: str
    event_type: str
    title: str
    description: str
    confidence: float
    event_time: str | None = None
    representative_article_id: str | None = None
    sequence: int = 0
    article_count: int = 0
    claim_count: int = 0
    processing_metadata: dict[str, str] | None = None


class StoryTimelineResponse(BaseModel):
    cluster_id: str
    events: list[StoryEventResponse] = []
    generated_at: str
    generation_method: str = "deterministic"


__all__ = ["StoryEventResponse", "StoryTimelineResponse"]
