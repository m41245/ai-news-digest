"""
Unit tests for ``NotificationSchedulingService``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from ai_news_digest.application.services.notifications.scheduling_service import (
    NotificationSchedulingService,
)
from ai_news_digest.domain.enums.notification import (
    DeliveryChannel,
    DeliveryStatus,
    NotificationType,
)
from ai_news_digest.domain.models.notification import Notification, NotificationDelivery
from ai_news_digest.domain.models.notification_preference import NotificationPreference


def _make_notification(
    notification_type: NotificationType = NotificationType.IMPORTANT_STORY,
) -> Notification:
    return Notification(
        id=uuid4(),
        user_id=uuid4(),
        notification_type=notification_type,
        title="Test",
        body="Body",
        severity="medium",
    )


def _make_preference(
    email_enabled: bool = True,
    immediate_enabled: bool = True,
    daily_digest_enabled: bool = False,
    weekly_digest_enabled: bool = False,
    quiet_hours_start: str | None = None,
    quiet_hours_end: str | None = None,
    max_per_day: int = 10,
    timezone: str = "UTC",
) -> NotificationPreference:
    pref = NotificationPreference.create_default(uuid4())
    pref.email_enabled = email_enabled
    pref.immediate_enabled = immediate_enabled
    pref.daily_digest_enabled = daily_digest_enabled
    pref.weekly_digest_enabled = weekly_digest_enabled
    pref.quiet_hours_start = quiet_hours_start
    pref.quiet_hours_end = quiet_hours_end
    pref.max_per_day = max_per_day
    pref.timezone = timezone
    return pref


@pytest.fixture
def mock_notification_repo() -> MagicMock:
    repo = MagicMock()
    repo.list_for_user = AsyncMock(return_value=([], 0))
    return repo


@pytest.fixture
def mock_delivery_repo() -> MagicMock:
    repo = MagicMock()
    repo.create = AsyncMock(side_effect=lambda d: d)
    repo.count_pending_since = AsyncMock(return_value=0)
    repo.list_pending = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_pref_repo() -> MagicMock:
    repo = MagicMock()
    repo.get_by_user_id = AsyncMock(side_effect=lambda uid: _make_preference())
    return repo


@pytest.fixture
def service(
    mock_notification_repo: MagicMock,
    mock_delivery_repo: MagicMock,
    mock_pref_repo: MagicMock,
) -> NotificationSchedulingService:
    return NotificationSchedulingService(
        notification_repo=mock_notification_repo,
        delivery_repo=mock_delivery_repo,
        preference_repo=mock_pref_repo,
    )


@pytest.mark.asyncio
async def test_creates_immediate_email_delivery_when_email_enabled(
    service: NotificationSchedulingService,
    mock_delivery_repo: MagicMock,
    mock_pref_repo: MagicMock,
) -> None:
    notification = _make_notification()
    preference = _make_preference(email_enabled=True, immediate_enabled=True)
    mock_pref_repo.get_by_user_id = AsyncMock(return_value=preference)

    with patch(
        "ai_news_digest.application.services.notifications.scheduling_service.create_email_sender"
    ) as mock_factory:
        mock_factory.return_value = MagicMock()
        deliveries = await service.schedule_notification(notification, preference=preference)

    assert len(deliveries) == 2
    channels = {d.channel for d in deliveries}
    assert DeliveryChannel.IN_APP in channels
    assert DeliveryChannel.EMAIL in channels
    email_deliveries = [d for d in deliveries if d.channel == DeliveryChannel.EMAIL]
    assert email_deliveries[0].scheduled_for is None


@pytest.mark.asyncio
async def test_skips_email_delivery_when_email_disabled(
    service: NotificationSchedulingService,
    mock_delivery_repo: MagicMock,
    mock_pref_repo: MagicMock,
) -> None:
    notification = _make_notification()
    preference = _make_preference(email_enabled=False)
    mock_pref_repo.get_by_user_id = AsyncMock(return_value=preference)

    with patch(
        "ai_news_digest.application.services.notifications.scheduling_service.create_email_sender"
    ) as mock_factory:
        mock_factory.return_value = MagicMock()
        deliveries = await service.schedule_notification(notification, preference=preference)

    assert len(deliveries) == 1
    assert deliveries[0].channel == DeliveryChannel.IN_APP
    assert deliveries[0].status.value == "pending"


@pytest.mark.asyncio
async def test_respects_quiet_hours_defers_email_delivery(
    service: NotificationSchedulingService,
    mock_delivery_repo: MagicMock,
    mock_pref_repo: MagicMock,
) -> None:
    notification = _make_notification()
    preference = _make_preference(
        email_enabled=True,
        immediate_enabled=True,
        quiet_hours_start="22:00",
        quiet_hours_end="07:00",
        timezone="UTC",
    )
    mock_pref_repo.get_by_user_id = AsyncMock(return_value=preference)

    with patch(
        "ai_news_digest.application.services.notifications.scheduling_service.create_email_sender"
    ) as mock_factory:
        mock_factory.return_value = MagicMock()
        with patch(
            "ai_news_digest.application.services.notifications.scheduling_service.datetime"
        ) as mock_dt:
            mock_dt.now.return_value = datetime(2026, 1, 1, 23, 0, tzinfo=UTC)
            mock_dt.UTC = UTC
            deliveries = await service.schedule_notification(notification, preference=preference)

    deferred = [
        d for d in deliveries if d.channel == DeliveryChannel.EMAIL and d.status.value == "deferred"
    ]
    assert len(deferred) == 1
    assert deferred[0].next_attempt_at is not None


@pytest.mark.asyncio
async def test_respects_daily_caps(
    service: NotificationSchedulingService,
    mock_delivery_repo: MagicMock,
    mock_pref_repo: MagicMock,
) -> None:
    notification = _make_notification()
    preference = _make_preference(email_enabled=True, immediate_enabled=True, max_per_day=2)
    mock_pref_repo.get_by_user_id = AsyncMock(return_value=preference)
    mock_delivery_repo.count_pending_since = AsyncMock(return_value=2)

    with patch(
        "ai_news_digest.application.services.notifications.scheduling_service.create_email_sender"
    ) as mock_factory:
        mock_factory.return_value = MagicMock()
        deliveries = await service.schedule_notification(notification, preference=preference)

    suppressed = [
        d
        for d in deliveries
        if d.channel == DeliveryChannel.EMAIL and d.status.value == "suppressed"
    ]
    assert len(suppressed) == 1
    assert suppressed[0].suppression_reason == "daily_cap_reached"


def test_generates_stable_idempotency_keys(service: NotificationSchedulingService) -> None:
    notification = _make_notification()
    key1 = service._generate_idempotency_key(notification.id, "email", "daily")
    key2 = service._generate_idempotency_key(notification.id, "email", "daily")
    assert key1 == key2
    assert len(key1) == 64


def test_generates_different_keys_for_different_windows(
    service: NotificationSchedulingService,
) -> None:
    notification = _make_notification()
    key_daily = service._generate_idempotency_key(notification.id, "email", "daily")
    key_weekly = service._generate_idempotency_key(notification.id, "email", "weekly")
    assert key_daily != key_weekly


@pytest.mark.asyncio
async def test_avoids_duplicate_delivery_records(
    mock_notification_repo: MagicMock,
    mock_delivery_repo: MagicMock,
    mock_pref_repo: MagicMock,
) -> None:
    existing = NotificationDelivery(
        id=uuid4(),
        notification_id=uuid4(),
        channel=DeliveryChannel.EMAIL,
        status=DeliveryStatus.PENDING,
    )
    mock_delivery_repo.list_pending = AsyncMock(return_value=[existing])
    mock_notification_repo.list_for_user = AsyncMock(return_value=([], 0))
    service = NotificationSchedulingService(
        notification_repo=mock_notification_repo,
        delivery_repo=mock_delivery_repo,
        preference_repo=mock_pref_repo,
    )

    result = await service.batch_schedule_pending(limit=10)
    assert result["scheduled"] == 0


@pytest.mark.asyncio
async def test_schedules_digest_ready_notifications(
    service: NotificationSchedulingService,
    mock_delivery_repo: MagicMock,
    mock_pref_repo: MagicMock,
) -> None:
    notification = _make_notification(NotificationType.DIGEST_READY)
    preference = _make_preference(
        email_enabled=True,
        daily_digest_enabled=True,
        weekly_digest_enabled=False,
    )
    mock_pref_repo.get_by_user_id = AsyncMock(return_value=preference)

    with patch(
        "ai_news_digest.application.services.notifications.scheduling_service.create_email_sender"
    ) as mock_factory:
        mock_factory.return_value = MagicMock()
        deliveries = await service.schedule_notification(notification, preference=preference)

    email_deliveries = [d for d in deliveries if d.channel == DeliveryChannel.EMAIL]
    assert len(email_deliveries) == 1
    assert email_deliveries[0].delivery_window == "daily"
    assert email_deliveries[0].scheduled_for is not None


@pytest.mark.asyncio
async def test_handles_timezone_aware_scheduling(
    service: NotificationSchedulingService,
    mock_delivery_repo: MagicMock,
    mock_pref_repo: MagicMock,
) -> None:
    notification = _make_notification(NotificationType.DIGEST_READY)
    preference = _make_preference(
        email_enabled=True,
        daily_digest_enabled=True,
        timezone="America/New_York",
    )
    mock_pref_repo.get_by_user_id = AsyncMock(return_value=preference)

    with patch(
        "ai_news_digest.application.services.notifications.scheduling_service.create_email_sender"
    ) as mock_factory:
        mock_factory.return_value = MagicMock()
        deliveries = await service.schedule_notification(notification, preference=preference)

    email_deliveries = [d for d in deliveries if d.channel == DeliveryChannel.EMAIL]
    assert len(email_deliveries) == 1
    assert email_deliveries[0].scheduled_for.tzinfo is not None


@pytest.mark.asyncio
async def test_no_digest_window_configuration_suppresses_email(
    service: NotificationSchedulingService,
    mock_delivery_repo: MagicMock,
    mock_pref_repo: MagicMock,
) -> None:
    notification = _make_notification(NotificationType.DIGEST_READY)
    preference = _make_preference(
        email_enabled=True,
        daily_digest_enabled=False,
        weekly_digest_enabled=False,
    )
    mock_pref_repo.get_by_user_id = AsyncMock(return_value=preference)

    with patch(
        "ai_news_digest.application.services.notifications.scheduling_service.create_email_sender"
    ) as mock_factory:
        mock_factory.return_value = MagicMock()
        deliveries = await service.schedule_notification(notification, preference=preference)

    suppressed = [
        d
        for d in deliveries
        if d.channel == DeliveryChannel.EMAIL and d.status.value == "suppressed"
    ]
    assert len(suppressed) == 1
    assert suppressed[0].suppression_reason == "no_digest_window_configured"


@pytest.mark.asyncio
async def test_batch_schedule_pending_respects_limit(
    service: NotificationSchedulingService,
    mock_notification_repo: MagicMock,
    mock_delivery_repo: MagicMock,
    mock_pref_repo: MagicMock,
) -> None:
    notifications = [_make_notification() for _ in range(3)]
    mock_notification_repo.list_for_user = AsyncMock(side_effect=[(notifications, 3), ([], 0)])
    mock_delivery_repo.list_pending = AsyncMock(return_value=[])
    mock_pref_repo.get_by_user_id = AsyncMock(return_value=_make_preference(email_enabled=False))

    result = await service.batch_schedule_pending(limit=2)
    assert result["scheduled"] == 2


__all__ = [
    "test_avoids_duplicate_delivery_records",
    "test_batch_schedule_pending_respects_limit",
    "test_creates_immediate_email_delivery_when_email_enabled",
    "test_generates_different_keys_for_different_windows",
    "test_generates_stable_idempotency_keys",
    "test_handles_timezone_aware_scheduling",
    "test_no_digest_window_configuration_suppresses_email",
    "test_respects_daily_caps",
    "test_respects_quiet_hours_defers_email_delivery",
    "test_schedules_digest_ready_notifications",
    "test_skips_email_delivery_when_email_disabled",
]
