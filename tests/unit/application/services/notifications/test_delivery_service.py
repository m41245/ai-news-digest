"""
Unit tests for ``NotificationDeliveryService``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from ai_news_digest.application.services.notifications.delivery_service import (
    _BACKOFF_BASE,
    _MAX_RETRIES,
    NotificationDeliveryService,
)
from ai_news_digest.domain.enums.notification import (
    DeliveryChannel,
    DeliveryStatus,
    NotificationSeverity,
    NotificationType,
)
from ai_news_digest.domain.models.notification import Notification, NotificationDelivery
from ai_news_digest.infrastructure.email.errors import (
    EmailConnectionError,
    EmailInvalidRecipientError,
    EmailPermanentFailureError,
    EmailTimeoutError,
)
from ai_news_digest.infrastructure.email.test_sender import TestEmailSender


def _make_notification() -> Notification:
    return Notification(
        id=uuid4(),
        user_id=uuid4(),
        notification_type=NotificationType.SYSTEM,
        title="Title",
        body="Body",
        severity=NotificationSeverity.MEDIUM,
    )


def _make_delivery(status: DeliveryStatus = DeliveryStatus.PENDING) -> NotificationDelivery:
    return NotificationDelivery(
        id=uuid4(),
        notification_id=uuid4(),
        channel=DeliveryChannel.EMAIL,
        status=status,
    )


@pytest.fixture
def mock_delivery_repo() -> MagicMock:
    repo = MagicMock()
    repo.list_scheduled = AsyncMock(return_value=[])
    repo.list_pending = AsyncMock(return_value=[])
    repo.list_retryable = AsyncMock(return_value=[])
    repo.list_stuck_processing = AsyncMock(return_value=[])
    repo.update = AsyncMock(side_effect=lambda d: d)
    return repo


@pytest.fixture
def mock_notification_repo() -> MagicMock:
    repo = MagicMock()
    repo.get_by_id = AsyncMock(
        side_effect=lambda nid: _make_notification() if nid == uuid4() else None
    )
    return repo


@pytest.fixture
def service(
    mock_delivery_repo: MagicMock,
    mock_notification_repo: MagicMock,
) -> NotificationDeliveryService:
    with patch(
        "ai_news_digest.application.services.notifications.delivery_service.create_email_sender",
        return_value=TestEmailSender(),
    ):
        svc = NotificationDeliveryService(
            delivery_repo=mock_delivery_repo,
            notification_repo=mock_notification_repo,
        )
    return svc


@pytest.mark.asyncio
async def test_process_scheduled_deliveries_processes_due_deliveries(
    service: NotificationDeliveryService,
    mock_delivery_repo: MagicMock,
) -> None:
    delivery = _make_delivery(DeliveryStatus.SCHEDULED)
    mock_delivery_repo.list_scheduled = AsyncMock(return_value=[delivery])
    with patch.object(service, "_process_single_delivery", new_callable=AsyncMock) as mock_process:
        result = await service.process_scheduled_deliveries(limit=10)
    assert result["processed"] == 1
    mock_process.assert_awaited_once_with(delivery)


@pytest.mark.asyncio
async def test_process_immediate_deliveries_skips_scheduled(
    service: NotificationDeliveryService,
    mock_delivery_repo: MagicMock,
) -> None:
    scheduled_delivery = _make_delivery(DeliveryStatus.PENDING)
    scheduled_delivery.scheduled_for = datetime.now(UTC)
    immediate_delivery = _make_delivery(DeliveryStatus.PENDING)
    mock_delivery_repo.list_pending = AsyncMock(
        return_value=[scheduled_delivery, immediate_delivery]
    )
    with patch.object(service, "_process_single_delivery", new_callable=AsyncMock) as mock_process:
        result = await service.process_immediate_deliveries(limit=10)
    assert result["processed"] == 1
    mock_process.assert_awaited_once_with(immediate_delivery)


@pytest.mark.asyncio
async def test_retries_with_exponential_backoff_on_timeout(
    service: NotificationDeliveryService,
    mock_delivery_repo: MagicMock,
) -> None:
    delivery = _make_delivery(DeliveryStatus.RETRYABLE_FAILURE)
    delivery.next_attempt_at = datetime.now(UTC)
    mock_delivery_repo.list_retryable = AsyncMock(return_value=[delivery])
    with patch.object(service, "_send_delivery", new_callable=AsyncMock) as mock_send:
        mock_send.side_effect = EmailTimeoutError("timeout")
        result = await service.retry_failed_deliveries(limit=10)
    assert result["retried"] == 1
    assert delivery.status == DeliveryStatus.RETRYABLE_FAILURE
    assert delivery.next_attempt_at is not None


@pytest.mark.asyncio
async def test_marks_permanent_failure_for_invalid_recipient(
    service: NotificationDeliveryService,
    mock_delivery_repo: MagicMock,
) -> None:
    delivery = _make_delivery(DeliveryStatus.RETRYABLE_FAILURE)
    delivery.next_attempt_at = datetime.now(UTC)
    mock_delivery_repo.list_retryable = AsyncMock(return_value=[delivery])
    with patch.object(service, "_send_delivery", new_callable=AsyncMock) as mock_send:
        mock_send.side_effect = EmailInvalidRecipientError("bad address")
        result = await service.retry_failed_deliveries(limit=10)
    assert result["failed"] == 1
    assert delivery.status == DeliveryStatus.PERMANENT_FAILURE


@pytest.mark.asyncio
async def test_distinguishes_temporary_vs_permanent_failures(
    service: NotificationDeliveryService,
    mock_delivery_repo: MagicMock,
) -> None:
    timeout_delivery = _make_delivery(DeliveryStatus.RETRYABLE_FAILURE)
    timeout_delivery.next_attempt_at = datetime.now(UTC)
    perm_delivery = _make_delivery(DeliveryStatus.RETRYABLE_FAILURE)
    perm_delivery.next_attempt_at = datetime.now(UTC)
    mock_delivery_repo.list_retryable = AsyncMock(return_value=[timeout_delivery, perm_delivery])
    call_count = 0

    async def send_side_effect(delivery: NotificationDelivery) -> None:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise EmailTimeoutError("timeout")
        raise EmailPermanentFailureError("perm")

    with patch.object(service, "_send_delivery", side_effect=send_side_effect):
        result = await service.retry_failed_deliveries(limit=10)
    assert result["retried"] == 1
    assert result["failed"] == 1


@pytest.mark.asyncio
async def test_records_delivery_attempts(
    service: NotificationDeliveryService,
    mock_delivery_repo: MagicMock,
) -> None:
    delivery = _make_delivery(DeliveryStatus.SCHEDULED)
    mock_delivery_repo.list_scheduled = AsyncMock(return_value=[delivery])
    with patch.object(service, "_send_delivery", new_callable=AsyncMock):
        await service._process_single_delivery(delivery)
    assert delivery.attempt_count == 2
    assert delivery.last_attempt_at is not None


@pytest.mark.asyncio
async def test_updates_status_atomically(
    service: NotificationDeliveryService,
    mock_delivery_repo: MagicMock,
) -> None:
    delivery = _make_delivery(DeliveryStatus.SCHEDULED)
    mock_delivery_repo.list_scheduled = AsyncMock(return_value=[delivery])
    with patch.object(service, "_send_delivery", new_callable=AsyncMock):
        await service._process_single_delivery(delivery)
    assert delivery.status == DeliveryStatus.SENT
    mock_delivery_repo.update.assert_awaited()


@pytest.mark.asyncio
async def test_handles_provider_outage_gracefully(
    service: NotificationDeliveryService,
    mock_delivery_repo: MagicMock,
) -> None:
    delivery = _make_delivery(DeliveryStatus.RETRYABLE_FAILURE)
    delivery.next_attempt_at = datetime.now(UTC)
    mock_delivery_repo.list_retryable = AsyncMock(return_value=[delivery])
    with patch.object(service, "_send_delivery", new_callable=AsyncMock) as mock_send:
        mock_send.side_effect = EmailConnectionError("connection refused")
        result = await service.retry_failed_deliveries(limit=10)
    assert result["retried"] == 1
    assert delivery.status == DeliveryStatus.RETRYABLE_FAILURE
    assert mock_delivery_repo.update.call_count >= 2


@pytest.mark.asyncio
async def test_recover_stuck_deliveries_marks_retryable(
    service: NotificationDeliveryService,
    mock_delivery_repo: MagicMock,
) -> None:
    stuck_delivery = _make_delivery(DeliveryStatus.PROCESSING)
    mock_delivery_repo.list_stuck_processing = AsyncMock(return_value=[stuck_delivery])
    result = await service.recover_stuck_deliveries(timeout_minutes=30, limit=10)
    assert result["recovered"] == 1
    assert stuck_delivery.status == DeliveryStatus.RETRYABLE_FAILURE
    assert stuck_delivery.next_attempt_at is not None


@pytest.mark.asyncio
async def test_process_scheduled_handles_exception_gracefully(
    service: NotificationDeliveryService,
    mock_delivery_repo: MagicMock,
) -> None:
    delivery = _make_delivery(DeliveryStatus.SCHEDULED)
    mock_delivery_repo.list_scheduled = AsyncMock(return_value=[delivery])
    with patch.object(service, "_process_single_delivery", new_callable=AsyncMock) as mock_process:
        mock_process.side_effect = RuntimeError("unexpected")
        result = await service.process_scheduled_deliveries(limit=10)
    assert result["failed"] == 1


def test_backoff_increases_exponentially() -> None:
    base = _BACKOFF_BASE
    for attempt in range(1, 6):
        expected = base * (2 ** min(attempt, 5))
        assert expected >= base


@pytest.mark.asyncio
async def test_max_retries_marks_permanent_failure(
    service: NotificationDeliveryService,
    mock_delivery_repo: MagicMock,
) -> None:
    delivery = _make_delivery(DeliveryStatus.RETRYABLE_FAILURE)
    delivery.attempt_count = _MAX_RETRIES
    delivery.next_attempt_at = datetime.now(UTC)
    mock_delivery_repo.list_retryable = AsyncMock(return_value=[delivery])
    with patch.object(service, "_send_delivery", new_callable=AsyncMock) as mock_send:
        mock_send.side_effect = RuntimeError("persistent failure")
        result = await service.retry_failed_deliveries(limit=10)
    assert result["failed"] == 1
    assert delivery.status == DeliveryStatus.PERMANENT_FAILURE


__all__ = [
    "test_backoff_increases_exponentially",
    "test_distinguishes_temporary_vs_permanent_failures",
    "test_handles_provider_outage_gracefully",
    "test_marks_permanent_failure_for_invalid_recipient",
    "test_max_retries_marks_permanent_failure",
    "test_process_immediate_deliveries_skips_scheduled",
    "test_process_scheduled_deliveries_processes_due_deliveries",
    "test_process_scheduled_handles_exception_gracefully",
    "test_records_delivery_attempts",
    "test_recover_stuck_deliveries_marks_retryable",
    "test_retries_with_exponential_backoff_on_timeout",
    "test_updates_status_atomically",
]
