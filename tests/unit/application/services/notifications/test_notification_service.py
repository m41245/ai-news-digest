"""
Unit tests for the notification service.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from ai_news_digest.application.services.notifications.notification_service import (
    NotificationService,
)
from ai_news_digest.domain.enums.notification import NotificationSeverity, NotificationType
from ai_news_digest.domain.models.notification import Notification
from ai_news_digest.domain.models.notification_preference import NotificationPreference
from ai_news_digest.domain.models.story_cluster import StoryCluster
from ai_news_digest.domain.models.user import User


def _make_user() -> User:
    return User(
        id=uuid4(),
        email="user@example.com",
        hashed_password="hashed",
        is_active=True,
        is_admin=False,
        created_at=datetime.now(UTC),
    )


def _make_story() -> StoryCluster:
    return StoryCluster(
        id=uuid4(),
        title="Test Story",
        slug="test-story",
        summary="A test story.",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def mock_notification_repo() -> MagicMock:
    repo = MagicMock()
    repo.get_by_deduplication_key = AsyncMock(return_value=None)
    repo.create = AsyncMock(side_effect=lambda n: n)
    repo.count_unread_since = AsyncMock(return_value=0)
    repo.mark_read = AsyncMock(return_value=None)
    repo.mark_all_read = AsyncMock(return_value=0)
    repo.dismiss = AsyncMock(return_value=None)
    repo.list_for_user = AsyncMock(return_value=([], 0))
    repo.count_unread = AsyncMock(return_value=0)
    repo.expire_old = AsyncMock(return_value=0)
    return repo


@pytest.fixture
def mock_delivery_repo() -> MagicMock:
    repo = MagicMock()
    repo.create = AsyncMock(return_value=MagicMock())
    return repo


@pytest.fixture
def mock_pref_repo() -> MagicMock:
    repo = MagicMock()
    repo.get_by_user_id = AsyncMock(
        return_value=NotificationPreference.create_default(uuid4())
    )
    repo.update = AsyncMock(side_effect=lambda p: p)
    repo.create = AsyncMock(side_effect=lambda p: p)
    repo.get_by_unsubscribe_token = AsyncMock(return_value=None)
    repo.delete_by_user_id = AsyncMock(return_value=None)
    return repo


@pytest.fixture
def mock_eligibility_engine() -> MagicMock:
    engine = MagicMock()
    engine.build_deduplication_key = MagicMock(return_value="dedup-key")
    engine.evaluate_story = AsyncMock(return_value=(True, None, {}))
    return engine


@pytest.fixture
def service(
    mock_notification_repo: MagicMock,
    mock_delivery_repo: MagicMock,
    mock_pref_repo: MagicMock,
    mock_eligibility_engine: MagicMock,
) -> NotificationService:
    return NotificationService(
        notification_repository=mock_notification_repo,
        delivery_repository=mock_delivery_repo,
        preference_repository=mock_pref_repo,
        eligibility_engine=mock_eligibility_engine,
    )


@pytest.mark.asyncio
async def test_create_notification_returns_none_when_duplicate(
    service: NotificationService,
    mock_notification_repo: MagicMock,
) -> None:
    user = _make_user()
    story = _make_story()
    existing = Notification(
        id=uuid4(),
        user_id=user.id,
        notification_type=NotificationType.IMPORTANT_STORY,
        title="Existing",
        body="Body",
        severity=NotificationSeverity.MEDIUM,
        deduplication_key="dedup-key",
    )
    mock_notification_repo.get_by_deduplication_key = AsyncMock(return_value=existing)

    result = await service.create_notification(
        user=user,
        notification_type=NotificationType.IMPORTANT_STORY,
        title="Title",
        body="Body",
        severity=NotificationSeverity.MEDIUM,
        story=story,
    )
    assert result is existing


@pytest.mark.asyncio
async def test_create_notification_returns_none_when_suppressed(
    service: NotificationService,
    mock_eligibility_engine: MagicMock,
) -> None:
    user = _make_user()
    story = _make_story()
    mock_eligibility_engine.evaluate_story = AsyncMock(return_value=(False, "reason", {}))

    result = await service.create_notification(
        user=user,
        notification_type=NotificationType.IMPORTANT_STORY,
        title="Title",
        body="Body",
        severity=NotificationSeverity.MEDIUM,
        story=story,
    )
    assert result is None


@pytest.mark.asyncio
async def test_create_notification_creates_deliveries(
    service: NotificationService,
    mock_notification_repo: MagicMock,
    mock_delivery_repo: MagicMock,
    mock_eligibility_engine: MagicMock,
) -> None:
    user = _make_user()
    story = _make_story()
    created_notification = Notification(
        id=uuid4(),
        user_id=user.id,
        notification_type=NotificationType.IMPORTANT_STORY,
        title="Title",
        body="Body",
        severity=NotificationSeverity.MEDIUM,
        deduplication_key="dedup-key",
    )
    mock_notification_repo.create = AsyncMock(return_value=created_notification)

    result = await service.create_notification(
        user=user,
        notification_type=NotificationType.IMPORTANT_STORY,
        title="Title",
        body="Body",
        severity=NotificationSeverity.MEDIUM,
        story=story,
    )
    assert result is created_notification
    assert mock_delivery_repo.create.call_count == 1


@pytest.mark.asyncio
async def test_ensure_default_preferences_creates_when_missing(
    service: NotificationService,
    mock_pref_repo: MagicMock,
) -> None:
    mock_pref_repo.get_by_user_id = AsyncMock(return_value=None)
    mock_pref_repo.create = AsyncMock(side_effect=lambda p: p)

    pref = await service.ensure_default_preferences(uuid4())
    assert pref is not None
    assert pref.unsubscribe_token is not None


@pytest.mark.asyncio
async def test_unsubscribe_email_success(
    service: NotificationService,
    mock_pref_repo: MagicMock,
) -> None:
    pref = NotificationPreference.create_default(uuid4())
    pref.unsubscribe_token = "token-123"
    mock_pref_repo.get_by_unsubscribe_token = AsyncMock(return_value=pref)
    mock_pref_repo.update = AsyncMock(return_value=pref)

    success = await service.unsubscribe_email("token-123")
    assert success is True
    assert pref.email_enabled is False


@pytest.mark.asyncio
async def test_unsubscribe_email_invalid_token(
    service: NotificationService,
    mock_pref_repo: MagicMock,
) -> None:
    mock_pref_repo.get_by_unsubscribe_token = AsyncMock(return_value=None)

    success = await service.unsubscribe_email("bad-token")
    assert success is False


@pytest.mark.asyncio
async def test_update_preferences_partial(
    service: NotificationService,
    mock_pref_repo: MagicMock,
) -> None:
    pref = NotificationPreference.create_default(uuid4())
    mock_pref_repo.get_by_user_id = AsyncMock(return_value=pref)
    mock_pref_repo.update = AsyncMock(return_value=pref)

    updated = await service.update_preferences(pref.user_id, {"min_importance": 0.7})
    assert updated.min_importance == 0.7


@pytest.mark.asyncio
async def test_mark_read_returns_none_when_notification_missing(
    service: NotificationService,
    mock_notification_repo: MagicMock,
) -> None:
    mock_notification_repo.mark_read = AsyncMock(return_value=None)

    result = await service.mark_read(uuid4(), uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_mark_all_read_returns_count(
    service: NotificationService,
    mock_notification_repo: MagicMock,
) -> None:
    mock_notification_repo.mark_all_read = AsyncMock(return_value=5)

    count = await service.mark_all_read(uuid4())
    assert count == 5


@pytest.mark.asyncio
async def test_dismiss_returns_none_when_notification_missing(
    service: NotificationService,
    mock_notification_repo: MagicMock,
) -> None:
    mock_notification_repo.dismiss = AsyncMock(return_value=None)

    result = await service.dismiss(uuid4(), uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_get_unread_count_returns_count(
    service: NotificationService,
    mock_notification_repo: MagicMock,
) -> None:
    mock_notification_repo.count_unread = AsyncMock(return_value=3)

    count = await service.get_unread_count(uuid4())
    assert count == 3


@pytest.mark.asyncio
async def test_list_notifications_returns_paginated_results(
    service: NotificationService,
    mock_notification_repo: MagicMock,
) -> None:
    notification = Notification(
        id=uuid4(),
        user_id=uuid4(),
        notification_type=NotificationType.IMPORTANT_STORY,
        title="Title",
        body="Body",
        severity=NotificationSeverity.MEDIUM,
        deduplication_key="key",
    )
    mock_notification_repo.list_for_user = AsyncMock(return_value=([notification], 1))

    items, total = await service.list_notifications(uuid4(), limit=20, offset=0)
    assert len(items) == 1
    assert total == 1


@pytest.mark.asyncio
async def test_reset_preferences_deletes_and_recreates(
    service: NotificationService,
    mock_pref_repo: MagicMock,
) -> None:
    user_id = uuid4()
    mock_pref_repo.delete_by_user_id = AsyncMock(return_value=None)
    created_pref = NotificationPreference.create_default(user_id)
    mock_pref_repo.create = AsyncMock(return_value=created_pref)

    pref = await service.reset_preferences(user_id)
    assert pref is not None
    assert pref.user_id == user_id
    mock_pref_repo.delete_by_user_id.assert_awaited_once_with(user_id)
    mock_pref_repo.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_notification_returns_none_for_other_user(
    service: NotificationService,
    mock_notification_repo: MagicMock,
) -> None:
    user_a = uuid4()
    user_b = uuid4()
    notification = Notification(
        id=uuid4(),
        user_id=user_a,
        notification_type=NotificationType.IMPORTANT_STORY,
        title="Title",
        body="Body",
        severity=NotificationSeverity.MEDIUM,
        deduplication_key="key",
    )
    mock_notification_repo.get_by_id = AsyncMock(return_value=notification)

    result = await service.get_notification(notification.id, user_b)
    assert result is None


__all__ = [
    "test_create_notification_creates_deliveries",
    "test_create_notification_returns_none_when_duplicate",
    "test_create_notification_returns_none_when_suppressed",
    "test_dismiss_returns_none_when_notification_missing",
    "test_ensure_default_preferences_creates_when_missing",
    "test_get_notification_returns_none_for_other_user",
    "test_get_unread_count_returns_count",
    "test_list_notifications_returns_paginated_results",
    "test_mark_all_read_returns_count",
    "test_mark_read_returns_none_when_notification_missing",
    "test_reset_preferences_deletes_and_recreates",
    "test_unsubscribe_email_invalid_token",
    "test_unsubscribe_email_success",
    "test_update_preferences_partial",
]
