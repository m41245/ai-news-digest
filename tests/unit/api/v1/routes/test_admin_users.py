"""
Unit tests for admin user-management API routes.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ai_news_digest.api.middleware.exception_handler import setup_exception_handlers
from ai_news_digest.api.v1.dependencies.auth import (
    get_current_active_user,
    get_current_admin_user,
)
from ai_news_digest.api.v1.dependencies.dependencies import get_container
from ai_news_digest.api.v1.routes.admin import router
from ai_news_digest.domain.models.user import User


@pytest.fixture
def admin_user() -> User:
    return User(
        id=uuid4(),
        email="admin@example.com",
        hashed_password="hashed",
        is_active=True,
        is_admin=True,
        created_at=datetime.now(UTC),
    )


@pytest.fixture
def normal_user() -> User:
    return User(
        id=uuid4(),
        email="user@example.com",
        hashed_password="hashed",
        is_active=True,
        is_admin=False,
        created_at=datetime.now(UTC),
    )


def _client(
    *,
    container: MagicMock,
    auth_override: User,
) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_container] = lambda: container
    app.dependency_overrides[get_current_admin_user] = lambda: auth_override
    setup_exception_handlers(app)
    return TestClient(app)


def test_list_users(admin_user: User) -> None:
    other = User(
        id=uuid4(),
        email="other@example.com",
        hashed_password="h",
        is_active=True,
        is_admin=False,
        created_at=datetime.now(UTC),
    )
    container = MagicMock()
    container.user_repository.list_all = AsyncMock(return_value=[admin_user, other])

    client = _client(container=container, auth_override=admin_user)
    response = client.get("/admin/users")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all("hashed_password" not in u for u in data)


def test_get_user(admin_user: User) -> None:
    container = MagicMock()
    container.user_repository.get_by_id = AsyncMock(return_value=admin_user)

    client = _client(container=container, auth_override=admin_user)
    response = client.get(f"/admin/users/{admin_user.id}")

    assert response.status_code == 200
    assert response.json()["email"] == admin_user.email


def test_get_user_not_found(admin_user: User) -> None:
    container = MagicMock()
    container.user_repository.get_by_id = AsyncMock(return_value=None)

    client = _client(container=container, auth_override=admin_user)
    response = client.get(f"/admin/users/{uuid4()}")

    assert response.status_code == 404


def test_patch_user(admin_user: User) -> None:
    updated = User(
        id=admin_user.id,
        email="changed@example.com",
        hashed_password="h",
        is_active=False,
        is_admin=True,
        created_at=datetime.now(UTC),
    )
    container = MagicMock()
    container.user_repository.get_by_id = AsyncMock(return_value=admin_user)
    container.user_repository.get_by_email = AsyncMock(return_value=None)
    container.user_repository.update = AsyncMock(return_value=updated)

    client = _client(container=container, auth_override=admin_user)
    response = client.patch(
        f"/admin/users/{admin_user.id}",
        json={"is_active": False, "email": "changed@example.com"},
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is False


def test_delete_user(admin_user: User) -> None:
    container = MagicMock()
    container.user_repository.get_by_id = AsyncMock(return_value=admin_user)
    container.user_repository.delete = AsyncMock()

    client = _client(container=container, auth_override=admin_user)
    response = client.delete(f"/admin/users/{admin_user.id}")

    assert response.status_code == 204
    container.user_repository.delete.assert_awaited_once()


def test_normal_user_forbidden(normal_user: User) -> None:
    """A non-admin authenticated user must be denied admin endpoints (403)."""
    from ai_news_digest.api.v1.dependencies.auth import (
        get_current_admin_user as real_admin_check,
    )

    container = MagicMock()
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_container] = lambda: container
    app.dependency_overrides[get_current_active_user] = lambda: normal_user
    app.dependency_overrides[get_current_admin_user] = real_admin_check
    setup_exception_handlers(app)
    client = TestClient(app)

    response = client.get("/admin/users")

    assert response.status_code == 403


def test_admin_endpoint_requires_auth() -> None:
    """An unauthenticated request must be denied (401)."""
    app = FastAPI()
    app.include_router(router)
    setup_exception_handlers(app)
    client = TestClient(app)

    response = client.get("/admin/users")

    assert response.status_code == 401


def test_dashboard_admin(admin_user: User) -> None:
    """Admin can access the server-rendered dashboard."""
    container = MagicMock()
    container.article_repository.list_recent = AsyncMock(return_value=[])
    container.digest_repository.list_recent = AsyncMock(return_value=[])
    container.user_repository.list_all = AsyncMock(return_value=[admin_user])
    container.source_repository.list_all = AsyncMock(return_value=[])
    client = _client(container=container, auth_override=admin_user)

    response = client.get("/admin/dashboard")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "hashed_password" not in response.text


def test_dashboard_forbidden(normal_user: User) -> None:
    """Non-admin users are denied the dashboard (403)."""
    from ai_news_digest.api.v1.dependencies.auth import (
        get_current_admin_user as real_admin_check,
    )

    container = MagicMock()
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_container] = lambda: container
    app.dependency_overrides[get_current_active_user] = lambda: normal_user
    app.dependency_overrides[get_current_admin_user] = real_admin_check
    setup_exception_handlers(app)
    client = TestClient(app)

    response = client.get("/admin/dashboard")

    assert response.status_code == 403
