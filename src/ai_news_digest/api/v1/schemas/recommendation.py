from __future__ import annotations

from typing import Literal

from ai_news_digest.application.dto.recommendation import (
    RecommendationItemResponse,
    RecommendationResponse,
)


class RecommendationResponseWrapper(RecommendationResponse):
    """Wrapper for recommendation API responses."""


RecommendationSort = Literal["recommendation", "published_at", "importance"]


__all__ = [
    "RecommendationItemResponse",
    "RecommendationResponse",
    "RecommendationResponseWrapper",
    "RecommendationSort",
]
