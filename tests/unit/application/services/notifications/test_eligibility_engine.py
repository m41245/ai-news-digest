"""
Unit tests for the notification eligibility engine.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from ai_news_digest.application.services.notifications.eligibility_engine import (
    NotificationEligibilityEngine,
)
from ai_news_digest.domain.enums.notification import (
    NotificationType,
)
from ai_news_digest.domain.models.notification_preference import NotificationPreference
from ai_news_digest.domain.models.story_cluster import StoryCluster
from ai_news_digest.domain.models.user import User
from ai_news_digest.domain.models.user_preference import UserPreferenceProfile


def _make_user() -> User:
    return User(
        id=uuid4(),
        email="user@example.com",
        hashed_password="hashed",
        is_active=True,
        is_admin=False,
        created_at=datetime.now(UTC),
    )


def _make_story(importance: float | None = 0.8, confidence: float | None = 0.9) -> StoryCluster:
    return StoryCluster(
        id=uuid4(),
        title="Test Story",
        slug="test-story",
        summary="A test story summary.",
        importance_score=importance,
        confidence=confidence,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def mock_notification_repo() -> MagicMock:
    repo = MagicMock()
    repo.count_unread_since = AsyncMock(return_value=0)
    return repo


@pytest.fixture
def mock_pref_repo() -> MagicMock:
    repo = MagicMock()
    repo.get_by_user_id = AsyncMock(return_value=NotificationPreference.create_default(uuid4()))
    return repo


@pytest.fixture
def mock_user_pref_repo() -> MagicMock:
    repo = MagicMock()
    repo.get_by_user_id = AsyncMock(return_value=UserPreferenceProfile(user_id=uuid4()))
    return repo


@pytest.fixture
def engine(
    mock_notification_repo: MagicMock,
    mock_pref_repo: MagicMock,
    mock_user_pref_repo: MagicMock,
) -> NotificationEligibilityEngine:
    return NotificationEligibilityEngine(
        notification_repository=mock_notification_repo,
        notification_preference_repo=mock_pref_repo,
        user_preference_repo=mock_user_pref_repo,
    )


@pytest.mark.asyncio
async def test_important_story_eligible(engine: NotificationEligibilityEngine) -> None:
    user = _make_user()
    story = _make_story(importance=0.9, confidence=0.9)
    eligible, reason, metadata = await engine.evaluate_story(
        user=user,
        story=story,
        notification_type=NotificationType.IMPORTANT_STORY,
    )
    assert eligible is True
    assert reason is None
    assert metadata["notification_type"] == NotificationType.IMPORTANT_STORY.value


@pytest.mark.asyncio
async def test_below_importance_threshold_suppressed(
    engine: NotificationEligibilityEngine,
) -> None:
    user = _make_user()
    story = _make_story(importance=0.1, confidence=0.9)
    pref = NotificationPreference.create_default(user.id)
    pref.min_importance = 0.5
    engine._notification_preference_repo.get_by_user_id = AsyncMock(return_value=pref)

    eligible, reason, _metadata = await engine.evaluate_story(
        user=user,
        story=story,
        notification_type=NotificationType.IMPORTANT_STORY,
    )
    assert eligible is False
    assert reason == "below_importance_threshold"


@pytest.mark.asyncio
async def test_below_confidence_threshold_suppressed(
    engine: NotificationEligibilityEngine,
) -> None:
    user = _make_user()
    story = _make_story(importance=0.9, confidence=0.1)
    pref = NotificationPreference.create_default(user.id)
    pref.min_confidence = 0.5
    engine._notification_preference_repo.get_by_user_id = AsyncMock(return_value=pref)

    eligible, reason, _metadata = await engine.evaluate_story(
        user=user,
        story=story,
        notification_type=NotificationType.IMPORTANT_STORY,
    )
    assert eligible is False
    assert reason == "below_confidence_threshold"


@pytest.mark.asyncio
async def test_muted_company_suppresses_followed_company_update(
    engine: NotificationEligibilityEngine,
) -> None:
    user = _make_user()
    story = _make_story()
    company_id = uuid4()
    user_pref = UserPreferenceProfile(
        user_id=user.id,
        muted_company_ids=frozenset([company_id]),
    )
    engine._user_preference_repo.get_by_user_id = AsyncMock(return_value=user_pref)

    eligible, reason, _metadata = await engine.evaluate_story(
        user=user,
        story=story,
        notification_type=NotificationType.FOLLOWED_COMPANY_UPDATE,
        company_id=company_id,
    )
    assert eligible is False
    assert reason == "muted_company"


@pytest.mark.asyncio
async def test_muted_topic_suppresses_followed_topic_update(
    engine: NotificationEligibilityEngine,
) -> None:
    user = _make_user()
    story = _make_story()
    topic_id = uuid4()
    user_pref = UserPreferenceProfile(
        user_id=user.id,
        muted_topic_ids=frozenset([topic_id]),
    )
    engine._user_preference_repo.get_by_user_id = AsyncMock(return_value=user_pref)

    eligible, reason, _metadata = await engine.evaluate_story(
        user=user,
        story=story,
        notification_type=NotificationType.FOLLOWED_TOPIC_UPDATE,
        topic_id=topic_id,
    )
    assert eligible is False
    assert reason == "muted_topic"


@pytest.mark.asyncio
async def test_daily_cap_blocks_notification(
    engine: NotificationEligibilityEngine,
) -> None:
    user = _make_user()
    story = _make_story()
    pref = NotificationPreference.create_default(user.id)
    pref.max_per_day = 2
    engine._notification_preference_repo.get_by_user_id = AsyncMock(return_value=pref)
    engine._notification_repository.count_unread_since = AsyncMock(return_value=2)

    eligible, reason, _metadata = await engine.evaluate_story(
        user=user,
        story=story,
        notification_type=NotificationType.IMPORTANT_STORY,
    )
    assert eligible is False
    assert reason == "daily_cap_reached"


@pytest.mark.asyncio
async def test_quiet_hours_suppress_notification(
    engine: NotificationEligibilityEngine,
) -> None:
    user = _make_user()
    story = _make_story()
    pref = NotificationPreference.create_default(user.id)
    pref.quiet_hours_start = "22:00"
    pref.quiet_hours_end = "06:00"
    pref.timezone = "UTC"
    engine._notification_preference_repo.get_by_user_id = AsyncMock(return_value=pref)

    with pytest.MonkeyPatch.context() as m:
        fixed_time = datetime(2024, 1, 1, 23, 0, tzinfo=UTC)
        m.setattr(
            "ai_news_digest.application.services.notifications.eligibility_engine.datetime",
            MagicMock(),
        )
        m.setattr(
            "ai_news_digest.application.services.notifications.eligibility_engine.datetime.now",
            lambda tz=None: fixed_time,
        )
        eligible, reason, _metadata = await engine.evaluate_story(
            user=user,
            story=story,
            notification_type=NotificationType.IMPORTANT_STORY,
        )
    assert eligible is False
    assert reason == "quiet_hours"


@pytest.mark.asyncio
async def test_deduplication_key_stable(engine: NotificationEligibilityEngine) -> None:
    user = _make_user()
    story = _make_story()
    key1 = engine.build_deduplication_key(
        user_id=user.id,
        notification_type=NotificationType.IMPORTANT_STORY,
        story_id=story.id,
    )
    key2 = engine.build_deduplication_key(
        user_id=user.id,
        notification_type=NotificationType.IMPORTANT_STORY,
        story_id=story.id,
    )
    assert key1 == key2
    parts = key1.split(":")
    assert parts[0] == str(user.id)
    assert parts[1] == NotificationType.IMPORTANT_STORY.value
    assert parts[2] == str(story.id)


@pytest.mark.asyncio
async def test_notifications_disabled_when_both_channels_off(
    engine: NotificationEligibilityEngine,
) -> None:
    user = _make_user()
    story = _make_story()
    pref = NotificationPreference.create_default(user.id)
    pref.in_app_enabled = False
    pref.email_enabled = False
    engine._notification_preference_repo.get_by_user_id = AsyncMock(return_value=pref)

    eligible, reason, _metadata = await engine.evaluate_story(
        user=user,
        story=story,
        notification_type=NotificationType.IMPORTANT_STORY,
    )
    assert eligible is False
    assert reason == "notifications_disabled"


@pytest.mark.asyncio
async def test_followed_company_update_eligible_when_not_muted(
    engine: NotificationEligibilityEngine,
) -> None:
    user = _make_user()
    story = _make_story()
    company_id = uuid4()
    user_pref = UserPreferenceProfile(
        user_id=user.id,
        followed_company_ids=frozenset([company_id]),
    )
    engine._user_preference_repo.get_by_user_id = AsyncMock(return_value=user_pref)

    eligible, reason, _metadata = await engine.evaluate_story(
        user=user,
        story=story,
        notification_type=NotificationType.FOLLOWED_COMPANY_UPDATE,
        company_id=company_id,
    )
    assert eligible is True
    assert reason is None


@pytest.mark.asyncio
async def test_followed_topic_update_eligible_when_not_muted(
    engine: NotificationEligibilityEngine,
) -> None:
    user = _make_user()
    story = _make_story()
    topic_id = uuid4()
    user_pref = UserPreferenceProfile(
        user_id=user.id,
        followed_topic_ids=frozenset([topic_id]),
    )
    engine._user_preference_repo.get_by_user_id = AsyncMock(return_value=user_pref)

    eligible, reason, _metadata = await engine.evaluate_story(
        user=user,
        story=story,
        notification_type=NotificationType.FOLLOWED_TOPIC_UPDATE,
        topic_id=topic_id,
    )
    assert eligible is True
    assert reason is None


@pytest.mark.asyncio
async def test_followed_updates_disabled_suppresses_notification(
    engine: NotificationEligibilityEngine,
) -> None:
    user = _make_user()
    story = _make_story()
    pref = NotificationPreference.create_default(user.id)
    pref.notify_followed_companies = False
    pref.notify_followed_topics = False
    engine._notification_preference_repo.get_by_user_id = AsyncMock(return_value=pref)

    eligible, reason, _metadata = await engine.evaluate_story(
        user=user,
        story=story,
        notification_type=NotificationType.FOLLOWED_COMPANY_UPDATE,
    )
    assert eligible is False
    assert reason == "followed_updates_disabled"


@pytest.mark.asyncio
async def test_story_evolution_disabled_suppresses_notification(
    engine: NotificationEligibilityEngine,
) -> None:
    user = _make_user()
    story = _make_story()
    pref = NotificationPreference.create_default(user.id)
    pref.notify_story_evolution = False
    engine._notification_preference_repo.get_by_user_id = AsyncMock(return_value=pref)

    eligible, reason, _metadata = await engine.evaluate_story(
        user=user,
        story=story,
        notification_type=NotificationType.STORY_EVOLUTION,
    )
    assert eligible is False
    assert reason == "story_evolution_disabled"


@pytest.mark.asyncio
async def test_contradiction_disabled_suppresses_notification(
    engine: NotificationEligibilityEngine,
) -> None:
    user = _make_user()
    story = _make_story()
    pref = NotificationPreference.create_default(user.id)
    pref.notify_corrections = False
    engine._notification_preference_repo.get_by_user_id = AsyncMock(return_value=pref)

    eligible, reason, _metadata = await engine.evaluate_story(
        user=user,
        story=story,
        notification_type=NotificationType.CONTRADICTION_DETECTED,
    )
    assert eligible is False
    assert reason == "corrections_disabled"


@pytest.mark.asyncio
async def test_correction_published_disabled_suppresses_notification(
    engine: NotificationEligibilityEngine,
) -> None:
    user = _make_user()
    story = _make_story()
    pref = NotificationPreference.create_default(user.id)
    pref.notify_corrections = False
    engine._notification_preference_repo.get_by_user_id = AsyncMock(return_value=pref)

    eligible, reason, _metadata = await engine.evaluate_story(
        user=user,
        story=story,
        notification_type=NotificationType.CORRECTION_PUBLISHED,
    )
    assert eligible is False
    assert reason == "corrections_disabled"


@pytest.mark.asyncio
async def test_digest_ready_disabled_suppresses_notification(
    engine: NotificationEligibilityEngine,
) -> None:
    user = _make_user()
    story = _make_story()
    pref = NotificationPreference.create_default(user.id)
    pref.daily_digest_enabled = False
    pref.weekly_digest_enabled = False
    engine._notification_preference_repo.get_by_user_id = AsyncMock(return_value=pref)

    eligible, reason, _metadata = await engine.evaluate_story(
        user=user,
        story=story,
        notification_type=NotificationType.DIGEST_READY,
    )
    assert eligible is False
    assert reason == "digest_notifications_disabled"


__all__ = [
    "test_below_confidence_threshold_suppressed",
    "test_below_importance_threshold_suppressed",
    "test_contradiction_disabled_suppresses_notification",
    "test_correction_published_disabled_suppresses_notification",
    "test_daily_cap_blocks_notification",
    "test_deduplication_key_stable",
    "test_digest_ready_disabled_suppresses_notification",
    "test_followed_company_update_eligible_when_not_muted",
    "test_followed_topic_update_eligible_when_not_muted",
    "test_followed_updates_disabled_suppresses_notification",
    "test_important_story_eligible",
    "test_muted_company_suppresses_followed_company_update",
    "test_muted_topic_suppresses_followed_topic_update",
    "test_notifications_disabled_when_both_channels_off",
    "test_quiet_hours_suppress_notification",
    "test_story_evolution_disabled_suppresses_notification",
]
