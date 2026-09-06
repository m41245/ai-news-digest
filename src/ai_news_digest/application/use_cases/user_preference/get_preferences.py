from __future__ import annotations

from ai_news_digest.application.dto.user_preference import UserPreferenceResponse
from ai_news_digest.domain.models.user import User
from ai_news_digest.domain.models.user_preference import UserPreferenceProfile
from ai_news_digest.domain.ports.user_preference_repository import UserPreferenceRepository


class GetPreferencesUseCase:
    """Return the current user's preference profile or safe defaults."""

    def __init__(
        self,
        preference_repository: UserPreferenceRepository,
    ) -> None:
        self._preference_repository = preference_repository

    async def execute(
        self,
        current_user: User,
    ) -> UserPreferenceResponse:
        profile = await self._preference_repository.get_by_user_id(current_user.id)

        if profile is None:
            profile = UserPreferenceProfile(user_id=current_user.id)
            await self._preference_repository.create(profile)

        return _to_response(profile)


def _to_response(profile: UserPreferenceProfile) -> UserPreferenceResponse:
    return UserPreferenceResponse(
        user_id=str(profile.user_id),
        min_importance=profile.min_importance,
        min_confidence=profile.min_confidence,
        feed_sort=profile.feed_sort,
        freshness_window_days=profile.freshness_window_days,
        preferred_source_types=list(profile.preferred_source_types),
        followed_companies=[str(cid) for cid in sorted(profile.followed_company_ids)],
        followed_topics=[str(tid) for tid in sorted(profile.followed_topic_ids)],
        followed_categories=[str(cid) for cid in sorted(profile.followed_category_ids)],
        muted_companies=[str(cid) for cid in sorted(profile.muted_company_ids)],
        muted_topics=[str(tid) for tid in sorted(profile.muted_topic_ids)],
        muted_categories=[str(cid) for cid in sorted(profile.muted_category_ids)],
        created_at=profile.created_at.isoformat() if profile.created_at else None,
        updated_at=profile.updated_at.isoformat() if profile.updated_at else None,
    )
