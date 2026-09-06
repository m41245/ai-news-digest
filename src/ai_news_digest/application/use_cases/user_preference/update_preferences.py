from __future__ import annotations

from ai_news_digest.application.dto.user_preference import (
    UserPreferenceResponse,
    UserPreferenceUpdateRequest,
)
from ai_news_digest.application.services.ranking.constants import (
    PreferenceValidation,
    SourceTypePreferenceBehavior,
)
from ai_news_digest.domain.models.user import User
from ai_news_digest.domain.models.user_preference import UserPreferenceProfile
from ai_news_digest.domain.ports.user_preference_repository import UserPreferenceRepository


class UpdatePreferencesUseCase:
    """Update scalar fields on the current user's preference profile."""

    def __init__(
        self,
        preference_repository: UserPreferenceRepository,
    ) -> None:
        self._preference_repository = preference_repository

    async def execute(
        self,
        current_user: User,
        request: UserPreferenceUpdateRequest,
    ) -> UserPreferenceResponse:
        profile = await self._preference_repository.get_by_user_id(current_user.id)

        if profile is None:
            profile = UserPreferenceProfile(user_id=current_user.id)

        if request.min_importance is not None:
            if not (
                PreferenceValidation.MIN_IMPORTANCE_MIN
                <= request.min_importance
                <= PreferenceValidation.MIN_IMPORTANCE_MAX
            ):
                raise ValueError(
                    f"min_importance must be between "
                    f"{PreferenceValidation.MIN_IMPORTANCE_MIN} and "
                    f"{PreferenceValidation.MIN_IMPORTANCE_MAX}"
                )
            profile.min_importance = request.min_importance

        if request.min_confidence is not None:
            if not (
                PreferenceValidation.MIN_CONFIDENCE_MIN
                <= request.min_confidence
                <= PreferenceValidation.MIN_CONFIDENCE_MAX
            ):
                raise ValueError(
                    f"min_confidence must be between "
                    f"{PreferenceValidation.MIN_CONFIDENCE_MIN} and "
                    f"{PreferenceValidation.MIN_CONFIDENCE_MAX}"
                )
            profile.min_confidence = request.min_confidence

        if request.feed_sort is not None:
            if request.feed_sort not in PreferenceValidation.VALID_SORT_VALUES:
                raise ValueError(
                    f"feed_sort must be one of {PreferenceValidation.VALID_SORT_VALUES}"
                )
            profile.feed_sort = request.feed_sort

        if request.freshness_window_days is not None:
            if not (
                PreferenceValidation.FRESHNESS_WINDOW_MIN
                <= request.freshness_window_days
                <= PreferenceValidation.FRESHNESS_WINDOW_MAX
            ):
                raise ValueError(
                    f"freshness_window_days must be between "
                    f"{PreferenceValidation.FRESHNESS_WINDOW_MIN} and "
                    f"{PreferenceValidation.FRESHNESS_WINDOW_MAX}"
                )
            profile.freshness_window_days = request.freshness_window_days

        if request.preferred_source_types is not None:
            normalized = SourceTypePreferenceBehavior.normalize(
                request.preferred_source_types
            )
            profile.preferred_source_types = normalized

        profile.touch()

        updated = await self._preference_repository.update(profile)

        return _to_response(updated)


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
