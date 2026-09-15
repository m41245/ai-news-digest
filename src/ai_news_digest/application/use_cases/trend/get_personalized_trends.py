"""
GetPersonalizedTrendsUseCase for M86.

Returns trends ranked by personalized relevance for the current user.
"""

from __future__ import annotations

from typing import Any

from ai_news_digest.application.services.personalization.personalized_relevance_engine import (
    PersonalizedRelevanceEngine,
)
from ai_news_digest.application.services.ranking.constants import FeedDefaults
from ai_news_digest.domain.models.user import User
from ai_news_digest.domain.models.user_preference import UserPreferenceProfile
from ai_news_digest.domain.ports.trend_repository import TrendRepository
from ai_news_digest.domain.ports.user_preference_repository import UserPreferenceRepository


class GetPersonalizedTrendsUseCase:
    """Return deterministic personalized trends for the current user."""

    def __init__(
        self,
        preference_repository: UserPreferenceRepository,
        trend_repository: TrendRepository,
    ) -> None:
        self._preference_repository = preference_repository
        self._trend_repository = trend_repository
        self._engine = PersonalizedRelevanceEngine()

    async def execute(
        self,
        current_user: User,
        page: int = 1,
        page_size: int = FeedDefaults.DEFAULT_PAGE_SIZE,
    ) -> list[dict[str, Any]]:
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = FeedDefaults.DEFAULT_PAGE_SIZE
        if page_size > FeedDefaults.MAX_PAGE_SIZE:
            page_size = FeedDefaults.MAX_PAGE_SIZE

        profile = await self._preference_repository.get_by_user_id(current_user.id)
        if profile is None:
            profile = UserPreferenceProfile(user_id=current_user.id)
            await self._preference_repository.create(profile)

        trends = await self._trend_repository.list_personalized(
            user_preference_profile=profile,
            limit=FeedDefaults.MAX_PAGE_SIZE,
            offset=0,
        )

        scored: list[dict[str, Any]] = []
        for trend in trends:
            explanation = self._engine.score_trend(trend, profile)
            scored.append({
                "id": str(trend.id),
                "trend_type": trend.trend_type.value,
                "display_name": trend.display_name,
                "status": trend.status.value,
                "trend_score": trend.trend_score,
                "momentum_score": trend.momentum_score,
                "recent_activity": trend.recent_activity,
                "baseline_activity": trend.baseline_activity,
                "source_count": trend.source_count,
                "story_count": trend.story_count,
                "event_count": trend.event_count,
                "explanation": trend.explanation,
                "personalized_relevance_score": explanation.score,
                "relevance_reasons": explanation.all_reasons,
                "first_detected_at": trend.first_detected_at.isoformat(),
                "last_detected_at": trend.last_detected_at.isoformat(),
                "trend_metadata": trend.trend_metadata,
            })

        scored.sort(key=lambda x: (-x["personalized_relevance_score"], -x["trend_score"], x["id"]))

        offset = (page - 1) * page_size
        return scored[offset : offset + page_size]
