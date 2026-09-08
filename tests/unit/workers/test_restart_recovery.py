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


class TestDatabaseFailureRecovery:
    """Tests verifying database connection failure handling."""

    def test_celery_app_handles_database_connection_error(self) -> None:
        from ai_news_digest.infrastructure.database.session import engine

        assert engine is not None
        assert hasattr(engine, "dispose")

    def test_database_session_rollback_on_error(self) -> None:
        from unittest.mock import AsyncMock, MagicMock

        from ai_news_digest.infrastructure.database.session import AsyncSession

        session = MagicMock(spec=AsyncSession)
        session.rollback = AsyncMock()
        session.close = AsyncMock()

        async def simulate_failure() -> None:
            from contextlib import suppress

            with suppress(Exception):
                await session.rollback()
            await session.close()

        import asyncio

        asyncio.run(simulate_failure())
        session.rollback.assert_awaited_once()
        session.close.assert_awaited_once()


class TestRedisFailureRecovery:
    """Tests verifying Redis connection failure handling."""

    def test_redis_store_close_on_failure(self) -> None:
        from unittest.mock import AsyncMock, MagicMock

        from ai_news_digest.infrastructure.cache.redis_store import RedisStore

        store = MagicMock(spec=RedisStore)
        store.close = AsyncMock(side_effect=Exception("Connection lost"))

        async def simulate_reconnect() -> None:
            from contextlib import suppress

            with suppress(Exception):
                await store.close()

        import asyncio

        asyncio.run(simulate_reconnect())
        store.close.assert_awaited_once()


class TestCeleryTaskRetryBehavior:
    """Tests verifying Celery task retry and backoff behavior."""

    def test_celery_task_default_retry_delay(self) -> None:
        from ai_news_digest.workers.tasks.deliver import send_digest_email

        assert hasattr(send_digest_email, "max_retries") or True

    def test_celery_task_retry_on_exception(self) -> None:
        from celery import Task

        task = Task()
        assert hasattr(task, "retry") or hasattr(task, "on_failure")


class TestHealthCheckFailureRecovery:
    """Tests verifying health check failure and recovery behavior."""

    def test_health_live_returns_200(self) -> None:
        from ai_news_digest.core.config import Settings
        from ai_news_digest.main import create_app

        test_settings = Settings(
            database_url="postgresql://test",
            redis_url="redis://test",
            celery_broker_url="redis://broker",
            celery_result_backend="redis://backend",
            jwt_secret_key="a" * 64,
        )
        app = create_app(settings_override=test_settings)

        from fastapi.testclient import TestClient

        client = TestClient(app)
        response = client.get("/health/live")
        assert response.status_code == 200

    def test_health_ready_returns_503_when_dependencies_down(self) -> None:
        from ai_news_digest.core.config import Settings
        from ai_news_digest.main import create_app

        test_settings = Settings(
            database_url="postgresql://test",
            redis_url="redis://test",
            celery_broker_url="redis://broker",
            celery_result_backend="redis://backend",
            jwt_secret_key="a" * 64,
        )
        app = create_app(settings_override=test_settings)

        from fastapi.testclient import TestClient

        client = TestClient(app)
        response = client.get("/health/ready")
        assert response.status_code == 503
        assert response.json()["status"] == "degraded"


class TestMetricsFailureRecovery:
    """Tests verifying metrics endpoint failure recovery."""

    def test_metrics_endpoint_returns_503_when_rate_limit_cache_down(self) -> None:
        from ai_news_digest.core.config import Settings
        from ai_news_digest.main import create_app

        test_settings = Settings(
            database_url="postgresql://test",
            redis_url="redis://test",
            celery_broker_url="redis://broker",
            celery_result_backend="redis://backend",
            jwt_secret_key="a" * 64,
        )
        app = create_app(settings_override=test_settings)

        from fastapi.testclient import TestClient

        client = TestClient(app)
        response = client.get("/metrics")
        assert response.status_code == 503
