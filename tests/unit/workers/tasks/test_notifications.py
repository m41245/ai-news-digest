"""
Unit tests for ``workers/tasks/notifications.py``.

Covers ``evaluate_notifications``, ``expire_old_notifications``, and all
Milestone 41 delivery/cleanup tasks.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from ai_news_digest.domain.models.story_cluster import StoryCluster
from ai_news_digest.domain.models.user import User
from ai_news_digest.workers.tasks import notifications as notifications_tasks
from tests.unit.workers.tasks.conftest import container_generator


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
        summary="A test story summary.",
        importance_score=0.9,
        confidence=0.9,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def mock_container() -> MagicMock:
    container = MagicMock()
    container.notification_eligibility_engine = MagicMock()
    container.notification_eligibility_engine.evaluate_story = AsyncMock()
    container.notification_service = MagicMock()
    container.notification_service.create_notification = AsyncMock()
    container.story_cluster_repository = MagicMock()
    container.user_repository = MagicMock()
    container.notification_repository = MagicMock()
    container.notification_repository.expire_old = AsyncMock(return_value=0)
    container.notification_repository.list_old = AsyncMock(return_value=[])
    container.notification_repository.get_by_id = AsyncMock(return_value=None)
    container.notification_scheduling_service = MagicMock()
    container.notification_scheduling_service.batch_schedule_pending = AsyncMock(
        return_value={"scheduled": 1}
    )
    container.notification_delivery_service = MagicMock()
    container.notification_delivery_service.process_scheduled_deliveries = AsyncMock(
        return_value={"processed": 1, "failed": 0}
    )
    container.notification_delivery_service.process_immediate_deliveries = AsyncMock(
        return_value={"processed": 1, "failed": 0}
    )
    container.notification_delivery_service.retry_failed_deliveries = AsyncMock(
        return_value={"retried": 1, "failed": 0}
    )
    container.notification_delivery_service.recover_stuck_deliveries = AsyncMock(
        return_value={"recovered": 1}
    )
    container.notification_delivery_service.cleanup_old_deliveries = AsyncMock(
        return_value={"deleted": 10}
    )
    container.notification_delivery_repository = MagicMock()
    container.notification_delivery_repository.list_pending = AsyncMock(return_value=[])
    container.notification_delivery_repository.get_by_id = AsyncMock(return_value=None)
    container.notification_delivery_repository._session = MagicMock()
    container.notification_delivery_repository._commit = AsyncMock()
    return container


async def test_evaluate_notifications_creates_notifications_for_eligible_users(
    mock_container: MagicMock,
) -> None:
    user = _make_user()
    story = _make_story()
    mock_container.story_cluster_repository.get_by_id = AsyncMock(return_value=story)
    mock_container.user_repository.list_all = AsyncMock(return_value=[user])
    mock_container.notification_eligibility_engine.evaluate_story = AsyncMock(
        return_value=(True, None, {})
    )
    mock_container.notification_service.create_notification = AsyncMock()

    with patch.object(notifications_tasks, "get_container", container_generator(mock_container)):
        result = await notifications_tasks.evaluate_notifications(str(story.id))

    assert result["evaluated"] == 1
    assert result["created"] == 1
    assert result["suppressed"] == 0
    mock_container.notification_service.create_notification.assert_awaited_once()


async def test_evaluate_notifications_suppresses_ineligible_users(
    mock_container: MagicMock,
) -> None:
    user = _make_user()
    story = _make_story()
    mock_container.story_cluster_repository.get_by_id = AsyncMock(return_value=story)
    mock_container.user_repository.list_all = AsyncMock(return_value=[user])
    mock_container.notification_eligibility_engine.evaluate_story = AsyncMock(
        return_value=(False, "below_importance_threshold", {})
    )
    mock_container.notification_service.create_notification = AsyncMock()

    with patch.object(notifications_tasks, "get_container", container_generator(mock_container)):
        result = await notifications_tasks.evaluate_notifications(str(story.id))

    assert result["evaluated"] == 1
    assert result["created"] == 0
    assert result["suppressed"] == 1
    mock_container.notification_service.create_notification.assert_not_called()


async def test_evaluate_notifications_skips_inactive_users(
    mock_container: MagicMock,
) -> None:
    active_user = _make_user()
    inactive_user = _make_user()
    inactive_user.is_active = False
    story = _make_story()
    mock_container.story_cluster_repository.get_by_id = AsyncMock(return_value=story)
    mock_container.user_repository.list_all = AsyncMock(return_value=[active_user, inactive_user])
    mock_container.notification_eligibility_engine.evaluate_story = AsyncMock(
        return_value=(True, None, {})
    )

    with patch.object(notifications_tasks, "get_container", container_generator(mock_container)):
        result = await notifications_tasks.evaluate_notifications(str(story.id))

    assert result["evaluated"] == 1
    mock_container.notification_eligibility_engine.evaluate_story.assert_awaited_once()


async def test_evaluate_notifications_missing_story_returns_zero(
    mock_container: MagicMock,
) -> None:
    mock_container.story_cluster_repository.get_by_id = AsyncMock(return_value=None)

    with patch.object(notifications_tasks, "get_container", container_generator(mock_container)):
        result = await notifications_tasks.evaluate_notifications(str(uuid4()))

    assert result == {"evaluated": 0, "created": 0, "suppressed": 0}


async def test_expire_old_notifications_expires_records(
    mock_container: MagicMock,
) -> None:
    mock_container.notification_repository.expire_old = AsyncMock(return_value=5)

    with patch.object(notifications_tasks, "get_container", container_generator(mock_container)):
        result = await notifications_tasks.expire_old_notifications()

    assert result == {"expired": 5}
    mock_container.notification_repository.expire_old.assert_awaited_once()


async def test_expire_old_notifications_none_expired(
    mock_container: MagicMock,
) -> None:
    mock_container.notification_repository.expire_old = AsyncMock(return_value=0)

    with patch.object(notifications_tasks, "get_container", container_generator(mock_container)):
        result = await notifications_tasks.expire_old_notifications()

    assert result == {"expired": 0}


async def test_schedule_notifications_batches_pending(
    mock_container: MagicMock,
) -> None:
    with patch.object(notifications_tasks, "get_container", container_generator(mock_container)):
        result = await notifications_tasks.schedule_notifications()

    assert result["scheduled"] == 1
    mock_container.notification_scheduling_service.batch_schedule_pending.assert_awaited_once()


async def test_process_scheduled_deliveries_processes_ready(
    mock_container: MagicMock,
) -> None:
    with patch.object(notifications_tasks, "get_container", container_generator(mock_container)):
        result = await notifications_tasks.process_scheduled_deliveries()

    assert result["processed"] == 1
    mock_container.notification_delivery_service.process_scheduled_deliveries.assert_awaited_once()


async def test_process_immediate_deliveries_processes_ready(
    mock_container: MagicMock,
) -> None:
    with patch.object(notifications_tasks, "get_container", container_generator(mock_container)):
        result = await notifications_tasks.process_immediate_deliveries()

    assert result["processed"] == 1
    mock_container.notification_delivery_service.process_immediate_deliveries.assert_awaited_once()


async def test_retry_failed_deliveries_retries_ready(
    mock_container: MagicMock,
) -> None:
    with patch.object(notifications_tasks, "get_container", container_generator(mock_container)):
        result = await notifications_tasks.retry_failed_deliveries()

    assert result["retried"] == 1
    mock_container.notification_delivery_service.retry_failed_deliveries.assert_awaited_once()


async def test_recover_stuck_deliveries_recovers_stuck(
    mock_container: MagicMock,
) -> None:
    with patch.object(notifications_tasks, "get_container", container_generator(mock_container)):
        result = await notifications_tasks.recover_stuck_deliveries()

    assert result["recovered"] == 1
    mock_container.notification_delivery_service.recover_stuck_deliveries.assert_awaited_once()


async def test_cleanup_old_notification_deliveries_deletes_old(
    mock_container: MagicMock,
) -> None:
    old_delivery = MagicMock()
    old_delivery.id = uuid4()
    old_delivery.created_at = datetime.now(UTC) - timedelta(days=60)
    mock_container.notification_delivery_repository.list_pending = AsyncMock(
        return_value=[old_delivery]
    )
    mock_container.notification_delivery_repository.get_by_id = AsyncMock(return_value=old_delivery)
    mock_container.notification_delivery_repository._session = MagicMock()
    mock_container.notification_delivery_repository._session.execute = AsyncMock()
    mock_container.notification_delivery_repository._commit = AsyncMock()

    with patch.object(notifications_tasks, "get_container", container_generator(mock_container)):
        result = await notifications_tasks.cleanup_old_notification_deliveries(days=30)

    assert result["deleted"] == 1
    assert result["days"] == 30
    mock_container.notification_delivery_repository._commit.assert_awaited()


async def test_cleanup_old_notifications_deletes_old(
    mock_container: MagicMock,
) -> None:
    old_notification = MagicMock()
    old_notification.id = uuid4()
    old_notification.created_at = datetime.now(UTC) - timedelta(days=120)
    mock_container.notification_repository.list_old = AsyncMock(return_value=[old_notification])
    mock_container.notification_repository.get_by_id = AsyncMock(return_value=old_notification)
    mock_container.notification_repository._session = MagicMock()
    mock_container.notification_repository._session.delete = AsyncMock()
    mock_container.notification_repository._commit = AsyncMock()

    with patch.object(notifications_tasks, "get_container", container_generator(mock_container)):
        result = await notifications_tasks.cleanup_old_notifications(days=90)

    assert result["deleted"] == 1
    assert result["days"] == 90


__all__ = [
    "test_cleanup_old_notification_deliveries_deletes_old",
    "test_cleanup_old_notifications_deletes_old",
    "test_evaluate_notifications_creates_notifications_for_eligible_users",
    "test_evaluate_notifications_missing_story_returns_zero",
    "test_evaluate_notifications_skips_inactive_users",
    "test_evaluate_notifications_suppresses_ineligible_users",
    "test_expire_old_notifications_expires_records",
    "test_expire_old_notifications_none_expired",
    "test_process_immediate_deliveries_processes_ready",
    "test_process_scheduled_deliveries_processes_ready",
    "test_recover_stuck_deliveries_recovers_stuck",
    "test_retry_failed_deliveries_retries_ready",
    "test_schedule_notifications_batches_pending",
]
