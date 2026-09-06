"""
Unit tests for ``DigestBatchingService``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from ai_news_digest.application.services.notifications.digest_batching_service import (
    DigestBatchingService,
    _MAX_DIGEST_ITEMS,
)
from ai_news_digest.domain.enums.notification import (
    DeliveryChannel,
    DeliveryStatus,
    NotificationSeverity,
    NotificationType,
)
from ai_news_digest.domain.models.notification import Notification, NotificationDelivery
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


def _make_notification(
    user: User,
    notification_type: NotificationType = NotificationType.DIGEST_READY,
    severity: NotificationSeverity = NotificationSeverity.MEDIUM,
    metadata: dict[str, Any] | None = None,
) -> Notification:
    return Notification(
        id=uuid4(),
        user_id=user.id,
        notification_type=notification_type,
        title="Story",
        body="Body",
        severity=severity,
        metadata=metadata,
    )


def _make_delivery(
    notification_id: UUID,
    status: DeliveryStatus = DeliveryStatus.SCHEDULED,
    scheduled_for: datetime | None = None,
    delivery_window: str = "daily",
    suppression_reason: str | None = None,
) -> NotificationDelivery:
    return NotificationDelivery(
        id=uuid4(),
        notification_id=notification_id,
        channel=DeliveryChannel.EMAIL,
        status=status,
        scheduled_for=scheduled_for or datetime(2020, 1, 1, tzinfo=UTC),
        delivery_window=delivery_window,
        suppression_reason=suppression_reason,
    )


@pytest.fixture
def mock_notification_repo() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_delivery_repo() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_pref_repo() -> MagicMock:
    return MagicMock()


@pytest.fixture
def service(
    mock_notification_repo: MagicMock,
    mock_delivery_repo: MagicMock,
    mock_pref_repo: MagicMock,
) -> DigestBatchingService:
    return DigestBatchingService(
        notification_repo=mock_notification_repo,
        delivery_repo=mock_delivery_repo,
        preference_repo=mock_pref_repo,
    )


@pytest.mark.asyncio
async def test_groups_notifications_by_user_and_window(
    service: DigestBatchingService,
    mock_notification_repo: MagicMock,
    mock_delivery_repo: MagicMock,
) -> None:
    user = _make_user()
    notification = _make_notification(user)
    delivery = _make_delivery(notification.id, delivery_window="daily")
    mock_delivery_repo.list_scheduled = AsyncMock(return_value=[delivery])
    mock_notification_repo.get_by_id = AsyncMock(return_value=notification)

    result = await service.group_for_digest("daily")
    assert user.id in result
    assert len(result[user.id]) == 1


@pytest.mark.asyncio
async def test_deduplicates_within_digest(
    service: DigestBatchingService,
    mock_notification_repo: MagicMock,
    mock_delivery_repo: MagicMock,
) -> None:
    user = _make_user()
    notification = _make_notification(user)
    delivery1 = _make_delivery(notification.id, delivery_window="daily")
    delivery2 = _make_delivery(notification.id, delivery_window="daily")
    mock_delivery_repo.list_scheduled = AsyncMock(return_value=[delivery1, delivery2])
    mock_notification_repo.get_by_id = AsyncMock(return_value=notification)

    result = await service.group_for_digest("daily")
    assert len(result[user.id]) == 1


@pytest.mark.asyncio
async def test_sorts_by_importance_severity(
    service: DigestBatchingService,
    mock_notification_repo: MagicMock,
    mock_delivery_repo: MagicMock,
) -> None:
    user = _make_user()
    low_notification = _make_notification(user, severity=NotificationSeverity.LOW)
    high_notification = _make_notification(user, severity=NotificationSeverity.HIGH)
    low_delivery = _make_delivery(low_notification.id, delivery_window="daily")
    high_delivery = _make_delivery(high_notification.id, delivery_window="daily")
    mock_delivery_repo.list_scheduled = AsyncMock(return_value=[low_delivery, high_delivery])
    mock_notification_repo.get_by_id = AsyncMock(side_effect=lambda nid: (
        high_notification if nid == high_notification.id else low_notification
    ))

    result = await service.group_for_digest("daily")
    user_deliveries = result[user.id]
    ids = [d.notification_id for d in user_deliveries]
    assert ids.index(high_notification.id) < ids.index(low_notification.id)


@pytest.mark.asyncio
async def test_caps_digest_size(
    service: DigestBatchingService,
    mock_notification_repo: MagicMock,
    mock_delivery_repo: MagicMock,
) -> None:
    user = _make_user()
    deliveries = [
        _make_delivery(uuid4(), delivery_window="daily")
        for _ in range(_MAX_DIGEST_ITEMS + 5)
    ]
    mock_delivery_repo.list_scheduled = AsyncMock(return_value=deliveries)
    mock_notification_repo.get_by_id = AsyncMock(return_value=None)

    result = await service.group_for_digest("daily", limit=_MAX_DIGEST_ITEMS)
    assert all(len(v) <= _MAX_DIGEST_ITEMS for v in result.values())


@pytest.mark.asyncio
async def test_avoids_empty_digests(
    service: DigestBatchingService,
    mock_delivery_repo: MagicMock,
) -> None:
    mock_delivery_repo.list_scheduled = AsyncMock(return_value=[])
    result = await service.group_for_digest("daily")
    assert result == {}


@pytest.mark.asyncio
async def test_avoids_duplicate_digests(
    service: DigestBatchingService,
    mock_notification_repo: MagicMock,
    mock_delivery_repo: MagicMock,
) -> None:
    user = _make_user()
    notification = _make_notification(user)
    delivery1 = _make_delivery(notification.id, delivery_window="daily")
    delivery2 = _make_delivery(notification.id, delivery_window="daily")
    mock_delivery_repo.list_scheduled = AsyncMock(return_value=[delivery1, delivery2])
    mock_notification_repo.get_by_id = AsyncMock(return_value=notification)

    result = await service.group_for_digest("daily")
    assert len(result[user.id]) == 1


@pytest.mark.asyncio
async def test_uses_bounded_queries(
    service: DigestBatchingService,
    mock_delivery_repo: MagicMock,
) -> None:
    mock_delivery_repo.list_scheduled = AsyncMock(return_value=[])
    await service.group_for_digest("daily", limit=10)
    call_kwargs = mock_delivery_repo.list_scheduled.call_args
    assert call_kwargs is not None
    assert call_kwargs.kwargs.get("limit") == 100


@pytest.mark.asyncio
async def test_skips_suppressed_deliveries(
    service: DigestBatchingService,
    mock_notification_repo: MagicMock,
    mock_delivery_repo: MagicMock,
) -> None:
    user = _make_user()
    notification = _make_notification(user)
    suppressed_delivery = _make_delivery(
        notification.id,
        suppression_reason="daily_cap_reached",
        delivery_window="daily",
    )
    mock_delivery_repo.list_scheduled = AsyncMock(return_value=[suppressed_delivery])
    mock_notification_repo.get_by_id = AsyncMock(return_value=notification)

    result = await service.group_for_digest("daily")
    assert user.id not in result


@pytest.mark.asyncio
async def test_get_digest_items_sorted_by_importance(
    service: DigestBatchingService,
    mock_notification_repo: MagicMock,
) -> None:
    user = _make_user()
    low_notification = _make_notification(user, severity=NotificationSeverity.LOW)
    high_notification = _make_notification(user, severity=NotificationSeverity.HIGH)
    mock_notification_repo.list_for_user = AsyncMock(return_value=([low_notification, high_notification], 2))

    items = await service.get_digest_items_for_user(user.id, "daily", limit=10)
    assert items[0]["importance_score"] >= items[-1]["importance_score"]


__all__ = [
    "test_avoids_duplicate_digests",
    "test_avoids_empty_digests",
    "test_caps_digest_size",
    "test_deduplicates_within_digest",
    "test_get_digest_items_sorted_by_importance",
    "test_groups_notifications_by_user_and_window",
    "test_skips_suppressed_deliveries",
    "test_sorts_by_importance_severity",
    "test_uses_bounded_queries",
]
