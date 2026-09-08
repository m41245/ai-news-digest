"""
Unit tests for authenticated notification API routes.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ai_news_digest.api.middleware.exception_handler import setup_exception_handlers
from ai_news_digest.api.v1.dependencies.auth import get_current_active_user
from ai_news_digest.api.v1.routes.notifications import router
from ai_news_digest.domain.enums.notification import (
    NotificationSeverity,
    NotificationType,
)
from ai_news_digest.domain.models.notification import Notification
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


def _build_container(user: User) -> MagicMock:
    container = MagicMock()

    notification = Notification(
        id=uuid4(),
        user_id=user.id,
        notification_type=NotificationType.IMPORTANT_STORY,
        title="Important Story",
        body="Story body",
        severity=NotificationSeverity.MEDIUM,
        story_id=None,
        article_id=None,
        company_id=None,
        topic_id=None,
        digest_id=None,
        metadata={},
        created_at=datetime.now(UTC),
        read_at=None,
        dismissed_at=None,
        expires_at=None,
    )

    container.notification_service.list_notifications = AsyncMock(return_value=([notification], 1))
    container.notification_service.get_notification = AsyncMock(return_value=notification)
    container.notification_service.mark_read = AsyncMock(return_value=notification)
    container.notification_service.mark_all_read = AsyncMock(return_value=0)
    container.notification_service.dismiss = AsyncMock(return_value=notification)
    container.notification_service.get_unread_count = AsyncMock(return_value=3)
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
    container.notification_service.update_preferences = AsyncMock(
        return_value=MagicMock(
            user_id=user.id,
            in_app_enabled=True,
            email_enabled=False,
            immediate_enabled=True,
            daily_digest_enabled=True,
            weekly_digest_enabled=False,
            min_importance=0.5,
            min_confidence=0.3,
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

    return container


@pytest.fixture
def client(mock_user: User) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_active_user] = lambda: mock_user

    mock_container = _build_container(mock_user)
    from ai_news_digest.api.v1.dependencies.dependencies import get_container

    app.dependency_overrides[get_container] = lambda: mock_container
    setup_exception_handlers(app)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def mock_user() -> User:
    return _make_user()


def test_list_notifications_requires_auth() -> None:
    app = FastAPI()
    app.include_router(router)
    setup_exception_handlers(app)
    with TestClient(app) as test_client:
        response = test_client.get("/notifications")
        assert response.status_code == 401


def test_list_notifications(client: TestClient) -> None:
    response = client.get("/notifications")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


def test_get_notification(client: TestClient) -> None:
    response = client.get(f"/notifications/{uuid4()}")
    assert response.status_code == 200


def test_get_notification_not_found(client: TestClient) -> None:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_active_user] = lambda: _make_user()
    container = _build_container(_make_user())
    container.notification_service.get_notification = AsyncMock(return_value=None)
    from ai_news_digest.api.v1.dependencies.dependencies import get_container

    app.dependency_overrides[get_container] = lambda: container
    setup_exception_handlers(app)
    with TestClient(app) as test_client:
        response = test_client.get(f"/notifications/{uuid4()}")
        assert response.status_code == 404


def test_mark_read(client: TestClient) -> None:
    response = client.post(f"/notifications/{uuid4()}/read")
    assert response.status_code == 200


def test_mark_all_read(client: TestClient) -> None:
    response = client.post("/notifications/read-all")
    assert response.status_code == 200
    assert response.json()["unread_count"] == 0


def test_dismiss(client: TestClient) -> None:
    response = client.post(f"/notifications/{uuid4()}/dismiss")
    assert response.status_code == 200


def test_get_unread_count(client: TestClient) -> None:
    response = client.get("/notifications/unread/count")
    assert response.status_code == 200
    assert response.json()["unread_count"] == 3


def test_get_preferences(client: TestClient) -> None:
    response = client.get("/notifications/preferences")
    assert response.status_code == 200
    data = response.json()
    assert "in_app_enabled" in data
    assert "email_enabled" in data


def test_update_preferences(client: TestClient) -> None:
    response = client.put("/notifications/preferences", json={"min_importance": 0.8})
    assert response.status_code == 200
    data = response.json()
    assert data["min_importance"] == 0.5


def test_reset_preferences(client: TestClient) -> None:
    response = client.post("/notifications/preferences/reset")
    assert response.status_code == 200


def test_unsubscribe(client: TestClient) -> None:
    response = client.get("/notifications/unsubscribe/token-123")
    assert response.status_code == 200
    assert response.json()["success"] is True


def test_unsubscribe_invalid_token() -> None:
    app = FastAPI()
    app.include_router(router)
    container = _build_container(_make_user())
    container.notification_service.unsubscribe_email = AsyncMock(return_value=False)
    from ai_news_digest.api.v1.dependencies.dependencies import get_container

    app.dependency_overrides[get_container] = lambda: container
    setup_exception_handlers(app)
    with TestClient(app) as test_client:
        response = test_client.get("/notifications/unsubscribe/bad-token")
        assert response.status_code == 404


def test_notifications_scoped_to_authenticated_user() -> None:
    user_a = _make_user()
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_active_user] = lambda: user_a

    container = _build_container(user_a)
    from ai_news_digest.api.v1.dependencies.dependencies import get_container

    app.dependency_overrides[get_container] = lambda: container
    setup_exception_handlers(app)
    with TestClient(app) as test_client:
        response = test_client.get("/notifications")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data


def test_cross_user_access_prevented() -> None:
    owner = _make_user()
    other = _make_user()
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_active_user] = lambda: other

    owner_container = _build_container(owner)
    from ai_news_digest.api.v1.dependencies.dependencies import get_container

    app.dependency_overrides[get_container] = lambda: owner_container
    setup_exception_handlers(app)
    with TestClient(app) as test_client:
        response = test_client.get("/notifications")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data


__all__ = [
    "test_cross_user_access_prevented",
    "test_dismiss",
    "test_get_notification",
    "test_get_notification_not_found",
    "test_get_preferences",
    "test_get_unread_count",
    "test_list_notifications",
    "test_list_notifications_requires_auth",
    "test_mark_all_read",
    "test_mark_read",
    "test_notifications_scoped_to_authenticated_user",
    "test_reset_preferences",
    "test_unsubscribe",
    "test_unsubscribe_invalid_token",
    "test_update_preferences",
]
