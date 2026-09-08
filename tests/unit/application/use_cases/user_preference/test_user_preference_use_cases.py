"""
Unit tests for user preference use cases.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from ai_news_digest.application.use_cases.user_preference.follow_category import (
    FollowCategoryUseCase,
    UnfollowCategoryUseCase,
)
from ai_news_digest.application.use_cases.user_preference.follow_company import (
    FollowCompanyUseCase,
    UnfollowCompanyUseCase,
)
from ai_news_digest.application.use_cases.user_preference.follow_topic import (
    FollowTopicUseCase,
    UnfollowTopicUseCase,
)
from ai_news_digest.application.use_cases.user_preference.get_preferences import (
    GetPreferencesUseCase,
)
from ai_news_digest.application.use_cases.user_preference.mute_category import (
    MuteCategoryUseCase,
    UnmuteCategoryUseCase,
)
from ai_news_digest.application.use_cases.user_preference.mute_company import (
    MuteCompanyUseCase,
    UnmuteCompanyUseCase,
)
from ai_news_digest.application.use_cases.user_preference.mute_topic import (
    MuteTopicUseCase,
    UnmuteTopicUseCase,
)
from ai_news_digest.application.use_cases.user_preference.reset_preferences import (
    ResetPreferencesUseCase,
)
from ai_news_digest.application.use_cases.user_preference.update_preferences import (
    UpdatePreferencesUseCase,
)
from ai_news_digest.domain.models.user import User
from ai_news_digest.domain.models.user_preference import UserPreferenceProfile
from ai_news_digest.domain.ports.user_preference_repository import UserPreferenceRepository


def _make_user() -> User:
    return User(
        id=uuid4(),
        email="me@example.com",
        hashed_password="hashed",
        is_active=True,
        is_admin=False,
        created_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_get_preferences_creates_defaults() -> None:
    user = _make_user()
    repo = AsyncMock(spec=UserPreferenceRepository)
    repo.get_by_user_id = AsyncMock(return_value=None)
    repo.create = AsyncMock()

    uc = GetPreferencesUseCase(preference_repository=repo)
    result = await uc.execute(user)

    repo.get_by_user_id.assert_awaited_once_with(user.id)
    repo.create.assert_awaited_once()
    assert result.user_id == str(user.id)
    assert result.min_importance == 0.0
    assert result.feed_sort == "published_at"


@pytest.mark.asyncio
async def test_update_preferences() -> None:
    user = _make_user()
    profile = UserPreferenceProfile(user_id=user.id)
    repo = AsyncMock(spec=UserPreferenceRepository)
    repo.get_by_user_id = AsyncMock(return_value=profile)
    repo.update = AsyncMock(return_value=profile)

    uc = UpdatePreferencesUseCase(preference_repository=repo)
    request = type(
        "Req",
        (),
        {
            "min_importance": 0.9,
            "min_confidence": 0.8,
            "feed_sort": "importance",
            "freshness_window_days": 30,
            "preferred_source_types": ["official_company"],
        },
    )()
    result = await uc.execute(user, request)

    repo.update.assert_awaited_once()
    assert result.min_importance == 0.9


@pytest.mark.asyncio
async def test_update_preferences_validates_min_importance() -> None:
    user = _make_user()
    profile = UserPreferenceProfile(user_id=user.id)
    repo = AsyncMock(spec=UserPreferenceRepository)
    repo.get_by_user_id = AsyncMock(return_value=profile)

    uc = UpdatePreferencesUseCase(preference_repository=repo)
    request = type(
        "Req",
        (),
        {
            "min_importance": 1.5,
            "min_confidence": None,
            "feed_sort": None,
            "freshness_window_days": None,
            "preferred_source_types": None,
        },
    )()

    with pytest.raises(ValueError, match="min_importance must be between"):
        await uc.execute(user, request)


@pytest.mark.asyncio
async def test_update_preferences_normalizes_source_types() -> None:
    user = _make_user()
    profile = UserPreferenceProfile(user_id=user.id)
    repo = AsyncMock(spec=UserPreferenceRepository)
    repo.get_by_user_id = AsyncMock(return_value=profile)
    repo.update = AsyncMock(return_value=profile)

    uc = UpdatePreferencesUseCase(preference_repository=repo)
    request = type(
        "Req",
        (),
        {
            "min_importance": None,
            "min_confidence": None,
            "feed_sort": None,
            "freshness_window_days": None,
            "preferred_source_types": [
                "official_company",
                "invalid_type",
                "tech_publication",
                "official_company",
            ],
        },
    )()

    result = await uc.execute(user, request)
    assert result.preferred_source_types == ["official_company", "tech_publication"]


@pytest.mark.asyncio
async def test_follow_company() -> None:
    user = _make_user()
    repo = AsyncMock(spec=UserPreferenceRepository)
    uc = FollowCompanyUseCase(preference_repository=repo)
    company_id = uuid4()
    await uc.execute(user, company_id)
    repo.add_followed_company.assert_awaited_once_with(user.id, company_id)


@pytest.mark.asyncio
async def test_unfollow_company() -> None:
    user = _make_user()
    repo = AsyncMock(spec=UserPreferenceRepository)
    uc = UnfollowCompanyUseCase(preference_repository=repo)
    company_id = uuid4()
    await uc.execute(user, company_id)
    repo.remove_followed_company.assert_awaited_once_with(user.id, company_id)


@pytest.mark.asyncio
async def test_follow_topic() -> None:
    user = _make_user()
    repo = AsyncMock(spec=UserPreferenceRepository)
    uc = FollowTopicUseCase(preference_repository=repo)
    topic_id = uuid4()
    await uc.execute(user, topic_id)
    repo.add_followed_topic.assert_awaited_once_with(user.id, topic_id)


@pytest.mark.asyncio
async def test_unfollow_topic() -> None:
    user = _make_user()
    repo = AsyncMock(spec=UserPreferenceRepository)
    uc = UnfollowTopicUseCase(preference_repository=repo)
    topic_id = uuid4()
    await uc.execute(user, topic_id)
    repo.remove_followed_topic.assert_awaited_once_with(user.id, topic_id)


@pytest.mark.asyncio
async def test_follow_category() -> None:
    user = _make_user()
    repo = AsyncMock(spec=UserPreferenceRepository)
    uc = FollowCategoryUseCase(preference_repository=repo)
    category_id = uuid4()
    await uc.execute(user, category_id)
    repo.add_followed_category.assert_awaited_once_with(user.id, category_id)


@pytest.mark.asyncio
async def test_unfollow_category() -> None:
    user = _make_user()
    repo = AsyncMock(spec=UserPreferenceRepository)
    uc = UnfollowCategoryUseCase(preference_repository=repo)
    category_id = uuid4()
    await uc.execute(user, category_id)
    repo.remove_followed_category.assert_awaited_once_with(user.id, category_id)


@pytest.mark.asyncio
async def test_mute_company() -> None:
    user = _make_user()
    repo = AsyncMock(spec=UserPreferenceRepository)
    uc = MuteCompanyUseCase(preference_repository=repo)
    company_id = uuid4()
    await uc.execute(user, company_id)
    repo.add_muted_company.assert_awaited_once_with(user.id, company_id)


@pytest.mark.asyncio
async def test_unmute_company() -> None:
    user = _make_user()
    repo = AsyncMock(spec=UserPreferenceRepository)
    uc = UnmuteCompanyUseCase(preference_repository=repo)
    company_id = uuid4()
    await uc.execute(user, company_id)
    repo.remove_muted_company.assert_awaited_once_with(user.id, company_id)


@pytest.mark.asyncio
async def test_mute_topic() -> None:
    user = _make_user()
    repo = AsyncMock(spec=UserPreferenceRepository)
    uc = MuteTopicUseCase(preference_repository=repo)
    topic_id = uuid4()
    await uc.execute(user, topic_id)
    repo.add_muted_topic.assert_awaited_once_with(user.id, topic_id)


@pytest.mark.asyncio
async def test_unmute_topic() -> None:
    user = _make_user()
    repo = AsyncMock(spec=UserPreferenceRepository)
    uc = UnmuteTopicUseCase(preference_repository=repo)
    topic_id = uuid4()
    await uc.execute(user, topic_id)
    repo.remove_muted_topic.assert_awaited_once_with(user.id, topic_id)


@pytest.mark.asyncio
async def test_mute_category() -> None:
    user = _make_user()
    repo = AsyncMock(spec=UserPreferenceRepository)
    uc = MuteCategoryUseCase(preference_repository=repo)
    category_id = uuid4()
    await uc.execute(user, category_id)
    repo.add_muted_category.assert_awaited_once_with(user.id, category_id)


@pytest.mark.asyncio
async def test_unmute_category() -> None:
    user = _make_user()
    repo = AsyncMock(spec=UserPreferenceRepository)
    uc = UnmuteCategoryUseCase(preference_repository=repo)
    category_id = uuid4()
    await uc.execute(user, category_id)
    repo.remove_muted_category.assert_awaited_once_with(user.id, category_id)


@pytest.mark.asyncio
async def test_reset_preferences() -> None:
    user = _make_user()
    repo = AsyncMock(spec=UserPreferenceRepository)
    uc = ResetPreferencesUseCase(preference_repository=repo)
    await uc.execute(user)
    repo.delete_by_user_id.assert_awaited_once_with(user.id)
