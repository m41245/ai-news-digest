from ai_news_digest.application.dto.user_preference import (
    UserPreferenceResponse,
    UserPreferenceUpdateRequest,
)
from ai_news_digest.application.use_cases.user_preference.follow_category import (
    FollowCategoryUseCase,
)
from ai_news_digest.application.use_cases.user_preference.follow_company import (
    FollowCompanyUseCase,
)
from ai_news_digest.application.use_cases.user_preference.follow_topic import (
    FollowTopicUseCase,
)
from ai_news_digest.application.use_cases.user_preference.get_personalized_feed import (
    GetPersonalizedFeedUseCase,
)
from ai_news_digest.application.use_cases.user_preference.get_preferences import (
    GetPreferencesUseCase,
)
from ai_news_digest.application.use_cases.user_preference.mute_category import (
    MuteCategoryUseCase,
)
from ai_news_digest.application.use_cases.user_preference.mute_company import (
    MuteCompanyUseCase,
)
from ai_news_digest.application.use_cases.user_preference.mute_topic import (
    MuteTopicUseCase,
)
from ai_news_digest.application.use_cases.user_preference.reset_preferences import (
    ResetPreferencesUseCase,
)
from ai_news_digest.application.use_cases.user_preference.unfollow_category import (
    UnfollowCategoryUseCase,
)
from ai_news_digest.application.use_cases.user_preference.unfollow_company import (
    UnfollowCompanyUseCase,
)
from ai_news_digest.application.use_cases.user_preference.unfollow_topic import (
    UnfollowTopicUseCase,
)
from ai_news_digest.application.use_cases.user_preference.unmute_category import (
    UnmuteCategoryUseCase,
)
from ai_news_digest.application.use_cases.user_preference.unmute_company import (
    UnmuteCompanyUseCase,
)
from ai_news_digest.application.use_cases.user_preference.unmute_topic import (
    UnmuteTopicUseCase,
)
from ai_news_digest.application.use_cases.user_preference.update_preferences import (
    UpdatePreferencesUseCase,
)

__all__ = [
    "FollowCategoryUseCase",
    "FollowCompanyUseCase",
    "FollowTopicUseCase",
    "GetPersonalizedFeedUseCase",
    "GetPreferencesUseCase",
    "MuteCategoryUseCase",
    "MuteCompanyUseCase",
    "MuteTopicUseCase",
    "ResetPreferencesUseCase",
    "UnfollowCategoryUseCase",
    "UnfollowCompanyUseCase",
    "UnfollowTopicUseCase",
    "UnmuteCategoryUseCase",
    "UnmuteCompanyUseCase",
    "UnmuteTopicUseCase",
    "UpdatePreferencesUseCase",
    "UserPreferenceResponse",
    "UserPreferenceUpdateRequest",
]
