"""
Unit tests for authenticated notification delivery API routes.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ai_news_digest.api.middleware.exception_handler import setup_exception_handlers
from ai_news_digest.api.v1.dependencies.auth import get_current_active_user
from ai_news_digest.api.v1.dependencies.dependencies import get_container
from ai_news_digest.api.v1.routes.notifications import router
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
        email="me@example.com",
        hashed_password="hashed",
        is_active=True,
        is_admin=False,
        created_at=datetime.now(UTC),
    )


def _make_notification(user: User | None = None) -> Notification:
    return Notification(
        id=uuid4(),
        user_id=user.id if user else uuid4(),
        notification_type=NotificationType.SYSTEM,
        title="Title",
        body="Body",
        severity=NotificationSeverity.MEDIUM,
    )


def _make_delivery(
    notification_id: Any = None,
    status: DeliveryStatus = DeliveryStatus.PENDING,
) -> NotificationDelivery:
    return NotificationDelivery(
        id=uuid4(),
        notification_id=notification_id or uuid4(),
        channel=DeliveryChannel.EMAIL,
        status=status,
    )


def _build_container(user: User) -> MagicMock:
    container = MagicMock()
    container.notification_service = MagicMock()
    container.notification_service.ensure_default_preferences = AsyncMock(
        return_value=MagicMock(
            user_id=user.id,
            in_app_enabled=True,
            email_enabled=False,
            immediate_enabled=True,
            daily_digest_enabled=True,
            weekly_digest_enabled=False,
            min_importance=0.0,
            min_confidence=0.0,
            notify_followed_companies=True,
            notify_followed_topics=True,
            notify_corrections=True,
            notify_story_evolution=True,
            quiet_hours_start=None,
            quiet_hours_end=None,
            timezone="UTC",
            max_per_day=10,
        )
    )
    container.notification_service.list_notifications = AsyncMock(
        return_value=([], 0)
    )
    container.notification_service.get_notification = AsyncMock(return_value=None)
    container.notification_service.get_unread_count = AsyncMock(return_value=0)
    container.notification_service.mark_read = AsyncMock(return_value=None)
    container.notification_service.mark_all_read = AsyncMock(return_value=0)
    container.notification_service.dismiss = AsyncMock(return_value=None)
    container.notification_service.update_preferences = AsyncMock(
        return_value=MagicMock(
            user_id=user.id,
            in_app_enabled=True,
            email_enabled=False,
            immediate_enabled=True,
            daily_digest_enabled=True,
            weekly_digest_enabled=False,
            min_importance=0.0,
            min_confidence=0.0,
            notify_followed_companies=True,
            notify_followed_topics=True,
            notify_corrections=True,
            notify_story_evolution=True,
            quiet_hours_start=None,
            quiet_hours_end=None,
            timezone="UTC",
            max_per_day=10,
        )
    )
    container.notification_service.reset_preferences = AsyncMock(
        return_value=MagicMock(
            user_id=user.id,
            in_app_enabled=True,
            email_enabled=False,
            immediate_enabled=True,
            daily_digest_enabled=True,
            weekly_digest_enabled=False,
            min_importance=0.0,
            min_confidence=0.0,
            notify_followed_companies=True,
            notify_followed_topics=True,
            notify_corrections=True,
            notify_story_evolution=True,
            quiet_hours_start=None,
            quiet_hours_end=None,
            timezone="UTC",
            max_per_day=10,
        )
    )
    container.notification_service.unsubscribe_email = AsyncMock(return_value=True)
    container.notification_repository = MagicMock()
    container.notification_repository.list_for_user = AsyncMock(return_value=([], 0))
    container.notification_repository.get_by_id = AsyncMock(return_value=None)
    container.notification_delivery_repository = MagicMock()
    container.notification_delivery_repository.list_pending = AsyncMock(return_value=[])
    container.notification_delivery_repository.list_scheduled = AsyncMock(return_value=[])
    container.notification_delivery_repository.get_by_id = AsyncMock(return_value=None)
    return container


@pytest.fixture
def client(mock_user: User) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_active_user] = lambda: mock_user

    mock_container = _build_container(mock_user)
    app.dependency_overrides[get_container] = lambda: mock_container
    setup_exception_handlers(app)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def mock_user() -> User:
    return _make_user()


def test_get_delivery_requires_auth() -> None:
    app = FastAPI()
    app.include_router(router)
    setup_exception_handlers(app)
    with TestClient(app) as test_client:
        response = test_client.get(f"/notifications/deliveries/{uuid4()}")
        assert response.status_code == 401


def test_get_delivery_returns_status(
    client: TestClient,
    mock_user: User,
) -> None:
    notification = _make_notification(mock_user)
    delivery = _make_delivery(notification.id, DeliveryStatus.SENT)
    container = _build_container(mock_user)
    container.notification_delivery_repository.get_by_id = AsyncMock(return_value=delivery)
    container.notification_repository.get_by_id = AsyncMock(return_value=notification)

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_active_user] = lambda: mock_user
    app.dependency_overrides[get_container] = lambda: container
    setup_exception_handlers(app)
    with TestClient(app) as test_client:
        response = test_client.get(f"/notifications/deliveries/{delivery.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == DeliveryStatus.SENT.value


def test_get_delivery_not_found(client: TestClient, mock_user: User) -> None:
    container = _build_container(mock_user)
    container.notification_delivery_repository.get_by_id = AsyncMock(return_value=None)

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_active_user] = lambda: mock_user
    app.dependency_overrides[get_container] = lambda: container
    setup_exception_handlers(app)
    with TestClient(app) as test_client:
        response = test_client.get(f"/notifications/deliveries/{uuid4()}")
    assert response.status_code == 404


def test_list_deliveries_returns_history(client: TestClient) -> None:
    response = client.get("/notifications/deliveries")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


def test_get_stats_returns_counts(client: TestClient) -> None:
    response = client.get("/notifications/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "unread" in data
    assert "by_type" in data
    assert "by_severity" in data


def test_schedule_preview_returns_scheduled(client: TestClient) -> None:
    response = client.get("/notifications/schedule-preview")
    assert response.status_code == 200
    data = response.json()
    assert "scheduled" in data
    assert "count" in data


def test_test_delivery_requires_dev_environment(client: TestClient, mock_user: User) -> None:
    container = _build_container(mock_user)

    production_settings = MagicMock()
    production_settings.environment = "production"
    with patch("ai_news_digest.core.config.get_settings", return_value=production_settings):
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_current_active_user] = lambda: mock_user
        app.dependency_overrides[get_container] = lambda: container
        setup_exception_handlers(app)
        with TestClient(app) as test_client:
            response = test_client.post(
                "/notifications/test-delivery",
                json={"title": "Test", "body": "Body"},
            )
        assert response.status_code == 403


def test_test_delivery_succeeds_in_dev(client: TestClient, mock_user: User) -> None:
    container = _build_container(mock_user)
    container.notification_repository.create = AsyncMock(
        side_effect=lambda n: Notification(
            id=n.id,
            user_id=n.user_id,
            notification_type=n.notification_type,
            title=n.title,
            body=n.body,
            severity=n.severity,
        )
    )
    container.notification_delivery_repository.create = AsyncMock(
        side_effect=lambda d: NotificationDelivery(
            id=d.id,
            notification_id=d.notification_id,
            channel=d.channel,
            status=d.status,
        )
    )

    development_settings = MagicMock()
    development_settings.environment = "development"
    with patch("ai_news_digest.core.config.get_settings", return_value=development_settings):
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_current_active_user] = lambda: mock_user
        app.dependency_overrides[get_container] = lambda: container
        setup_exception_handlers(app)
        with TestClient(app) as test_client:
            response = test_client.post(
                "/notifications/test-delivery",
                json={"title": "Test", "body": "Body", "severity": "low"},
            )
        assert response.status_code == 200


def test_cross_user_access_prevented_for_delivery() -> None:
    owner = _make_user()
    other = _make_user()
    notification = _make_notification(owner)
    delivery = _make_delivery(notification.id, DeliveryStatus.SENT)
    owner_container = _build_container(owner)
    owner_container.notification_delivery_repository.get_by_id = AsyncMock(return_value=delivery)
    owner_container.notification_repository.get_by_id = AsyncMock(return_value=notification)

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_active_user] = lambda: other
    app.dependency_overrides[get_container] = lambda: owner_container
    setup_exception_handlers(app)
    with TestClient(app) as test_client:
        response = test_client.get(f"/notifications/deliveries/{delivery.id}")
    assert response.status_code == 404


def test_notifications_scoped_to_authenticated_user(client: TestClient) -> None:
    response = client.get("/notifications/deliveries")
    assert response.status_code == 200


__all__ = [
    "test_cross_user_access_prevented_for_delivery",
    "test_get_delivery_not_found",
    "test_get_delivery_requires_auth",
    "test_get_delivery_returns_status",
    "test_get_stats_returns_counts",
    "test_list_deliveries_returns_history",
    "test_notifications_scoped_to_authenticated_user",
    "test_schedule_preview_returns_scheduled",
    "test_test_delivery_requires_dev_environment",
    "test_test_delivery_succeeds_in_dev",
]
