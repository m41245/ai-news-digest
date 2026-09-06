from __future__ import annotations

import json
from uuid import UUID

from ai_news_digest.domain.models.user_preference import UserPreferenceProfile
from ai_news_digest.infrastructure.database.models.user_followed_category_model import (
    UserFollowedCategoryModel,
)
from ai_news_digest.infrastructure.database.models.user_followed_company_model import (
    UserFollowedCompanyModel,
)
from ai_news_digest.infrastructure.database.models.user_followed_topic_model import (
    UserFollowedTopicModel,
)
from ai_news_digest.infrastructure.database.models.user_muted_category_model import (
    UserMutedCategoryModel,
)
from ai_news_digest.infrastructure.database.models.user_muted_company_model import (
    UserMutedCompanyModel,
)
from ai_news_digest.infrastructure.database.models.user_muted_topic_model import (
    UserMutedTopicModel,
)
from ai_news_digest.infrastructure.database.models.user_preference_model import (
    UserPreferenceProfileModel,
)


class UserPreferenceMapper:
    """Maps between UserPreferenceProfile domain objects and ORM entities."""

    @staticmethod
    def to_model(profile: UserPreferenceProfile) -> UserPreferenceProfileModel:
        return UserPreferenceProfileModel(
            user_id=str(profile.user_id),
            min_importance=profile.min_importance,
            min_confidence=profile.min_confidence,
            feed_sort=profile.feed_sort,
            freshness_window_days=profile.freshness_window_days,
            preferred_source_types_json=(
                json.dumps(list(profile.preferred_source_types), ensure_ascii=False)
                if profile.preferred_source_types
                else None
            ),
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        )

    @staticmethod
    def update_model(
        model: UserPreferenceProfileModel,
        profile: UserPreferenceProfile,
    ) -> None:
        model.min_importance = profile.min_importance
        model.min_confidence = profile.min_confidence
        model.feed_sort = profile.feed_sort
        model.freshness_window_days = profile.freshness_window_days
        model.preferred_source_types_json = (
            json.dumps(list(profile.preferred_source_types), ensure_ascii=False)
            if profile.preferred_source_types
            else None
        )
        model.updated_at = profile.updated_at

    @staticmethod
    def to_domain(
        model: UserPreferenceProfileModel,
        followed_companies: list[UserFollowedCompanyModel] | None = None,
        followed_topics: list[UserFollowedTopicModel] | None = None,
        followed_categories: list[UserFollowedCategoryModel] | None = None,
        muted_companies: list[UserMutedCompanyModel] | None = None,
        muted_topics: list[UserMutedTopicModel] | None = None,
        muted_categories: list[UserMutedCategoryModel] | None = None,
    ) -> UserPreferenceProfile:
        preferred_source_types: tuple[str, ...] = ()
        if model.preferred_source_types_json:
            try:
                parsed = json.loads(model.preferred_source_types_json)
                if isinstance(parsed, list):
                    preferred_source_types = tuple(str(item) for item in parsed)
            except (ValueError, TypeError):
                preferred_source_types = ()

        return UserPreferenceProfile(
            user_id=UUID(model.user_id),
            followed_company_ids=frozenset(
                UUID(link.company_id) for link in (followed_companies or [])
            ),
            followed_topic_ids=frozenset(
                UUID(link.topic_id) for link in (followed_topics or [])
            ),
            followed_category_ids=frozenset(
                UUID(link.category_id) for link in (followed_categories or [])
            ),
            muted_company_ids=frozenset(
                UUID(link.company_id) for link in (muted_companies or [])
            ),
            muted_topic_ids=frozenset(
                UUID(link.topic_id) for link in (muted_topics or [])
            ),
            muted_category_ids=frozenset(
                UUID(link.category_id) for link in (muted_categories or [])
            ),
            min_importance=model.min_importance,
            min_confidence=model.min_confidence,
            feed_sort=model.feed_sort,
            freshness_window_days=model.freshness_window_days,
            preferred_source_types=preferred_source_types,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
