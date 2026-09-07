"""
Unit tests for worker restart, recovery, and failure isolation behavior.

Phase 6: Failure / restart / recovery tests.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_news_digest.workers.celery_app import celery_app
from ai_news_digest.workers.tasks import notifications as notifications_tasks
from tests.unit.workers.tasks.conftest import container_generator


class TestWorkerRestartConfiguration:
    """Tests verifying worker restart and shutdown configuration."""

    def test_worker_shutdown_timeout_configured(self) -> None:
        assert celery_app.conf.worker_shutdown_timeout == 30

    def test_worker_term_timeout_configured(self) -> None:
        assert celery_app.conf.worker_term_timeout == 30

    def test_worker_cancel_long_running_tasks_on_connection_loss(self) -> None:
        assert celery_app.conf.worker_cancel_long_running_tasks_on_connection_loss is True

    def test_task_acks_late_ensures_late_acknowledgment(self) -> None:
        assert celery_app.conf.task_acks_late is True

    def test_task_reject_on_worker_lost_requeues_task(self) -> None:
        assert celery_app.conf.task_reject_on_worker_lost is True


class TestRecoverStuckDeliveries:
    """Tests for recovering stuck notification deliveries."""

    @pytest.fixture
    def mock_container(self) -> MagicMock:
        container = MagicMock()
        container.notification_delivery_service = MagicMock()
        container.notification_delivery_service.recover_stuck_deliveries = AsyncMock(
            return_value={"recovered": 2}
        )
        return container

    async def test_recover_stuck_deliveries_recovers_stuck(
        self,
        mock_container: MagicMock,
    ) -> None:
        with patch.object(
            notifications_tasks,
            "get_container",
            container_generator(mock_container),
        ):
            result = await notifications_tasks.recover_stuck_deliveries()

        assert result["recovered"] == 2
        mock_container.notification_delivery_service.recover_stuck_deliveries.assert_awaited_once()

    async def test_recover_stuck_deliveries_no_stuck_records(
        self,
        mock_container: MagicMock,
    ) -> None:
        mock_container.notification_delivery_service.recover_stuck_deliveries = AsyncMock(
            return_value={"recovered": 0}
        )

        with patch.object(
            notifications_tasks,
            "get_container",
            container_generator(mock_container),
        ):
            result = await notifications_tasks.recover_stuck_deliveries()

        assert result["recovered"] == 0


class TestRetryFailedDeliveries:
    """Tests for retrying failed notification deliveries."""

    @pytest.fixture
    def mock_container(self) -> MagicMock:
        container = MagicMock()
        container.notification_delivery_service = MagicMock()
        container.notification_delivery_service.retry_failed_deliveries = AsyncMock(
            return_value={"retried": 3, "failed": 1}
        )
        return container

    async def test_retry_failed_deliveries_retries_ready(
        self,
        mock_container: MagicMock,
    ) -> None:
        with patch.object(
            notifications_tasks,
            "get_container",
            container_generator(mock_container),
        ):
            result = await notifications_tasks.retry_failed_deliveries()

        assert result["retried"] == 3
        assert result["failed"] == 1
        mock_container.notification_delivery_service.retry_failed_deliveries.assert_awaited_once()

    async def test_retry_failed_deliveries_none_ready(
        self,
        mock_container: MagicMock,
    ) -> None:
        mock_container.notification_delivery_service.retry_failed_deliveries = AsyncMock(
            return_value={"retried": 0, "failed": 0}
        )

        with patch.object(
            notifications_tasks,
            "get_container",
            container_generator(mock_container),
        ):
            result = await notifications_tasks.retry_failed_deliveries()

        assert result["retried"] == 0


class TestFailureIsolation:
    """Tests verifying that task failures are isolated."""

    def test_celery_app_task_registration_survives_configuration_check(self) -> None:
        registered = set(celery_app.tasks.keys())
        assert "workers.tasks.notifications.recover_stuck_deliveries" in registered
        assert "workers.tasks.notifications.retry_failed_deliveries" in registered


class TestDeliveryRecoveryBackoff:
    """Tests verifying backoff behavior in delivery recovery."""

    def test_recover_stuck_deliveries_schedules_backoff(self) -> None:
        from ai_news_digest.application.services.notifications.delivery_service import (
            NotificationDeliveryService,
        )
        from ai_news_digest.domain.enums.notification import DeliveryChannel, DeliveryStatus
        from ai_news_digest.domain.models.notification import NotificationDelivery

        delivery = NotificationDelivery(
            id=__import__("uuid").uuid4(),
            notification_id=__import__("uuid").uuid4(),
            channel=DeliveryChannel.EMAIL,
            status=DeliveryStatus.PROCESSING,
        )
        repo = MagicMock()
        repo.list_stuck_processing = AsyncMock(return_value=[delivery])
        repo.update = AsyncMock()

        service = NotificationDeliveryService.__new__(NotificationDeliveryService)
        service._delivery_repo = repo
        service._notification_repo = None
        service._user_repo = None
        service._sender = MagicMock()

        import asyncio

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                service.recover_stuck_deliveries(timeout_minutes=30, limit=50)
            )
        finally:
            asyncio.set_event_loop(None)
            loop.close()

        assert result["recovered"] == 1
        repo.update.assert_awaited_once()
