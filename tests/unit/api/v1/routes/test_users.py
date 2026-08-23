"""
Unit tests for the authenticated user API routes.
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
from ai_news_digest.api.v1.routes.users import router
from ai_news_digest.domain.models.user import User


@pytest.fixture
def mock_user() -> User:
    return User(
        id=uuid4(),
        email="me@example.com",
        hashed_password="hashed",
        is_active=True,
        is_admin=False,
        created_at=datetime.now(UTC),
    )


@pytest.fixture
def client(mock_user: User) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_active_user] = lambda: mock_user
    setup_exception_handlers(app)
    return TestClient(app)


@pytest.fixture
def unauth_client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    setup_exception_handlers(app)
    return TestClient(app)


def test_get_me(client: TestClient, mock_user: User) -> None:
    response = client.get("/users/me")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(mock_user.id)
    assert data["email"] == mock_user.email
    assert data["is_admin"] is False
    assert "hashed_password" not in data


def test_get_me_requires_auth(unauth_client: TestClient) -> None:
    response = unauth_client.get("/users/me")

    assert response.status_code == 401


def _patch_users_deps(
    client: TestClient,
    mock_session: MagicMock,
    mock_container: MagicMock,
) -> None:
    import ai_news_digest.api.v1.routes.users as users_module

    async def _gen() -> MagicMock:
        yield mock_session

    client.app.dependency_overrides[users_module.get_db_session] = lambda: _gen()
    users_module.Container = lambda s: mock_container  # type: ignore[misc]


def test_update_me_password(client: TestClient, mock_user: User) -> None:
    updated = User(
        id=mock_user.id,
        email=mock_user.email,
        hashed_password="newhash",
        is_active=True,
        is_admin=False,
        created_at=mock_user.created_at,
    )

    mock_session = MagicMock()
    mock_container = MagicMock()
    mock_container.user_repository.get_by_id = AsyncMock(return_value=mock_user)
    mock_container.user_repository.update = AsyncMock(return_value=updated)
    _patch_users_deps(client, mock_session, mock_container)

    response = client.patch("/users/me", json={"password": "NewPassword123"})

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == mock_user.email
    mock_container.user_repository.update.assert_awaited_once()


def test_update_me_duplicate_email(client: TestClient, mock_user: User) -> None:
    other = User(
        id=uuid4(),
        email="taken@example.com",
        hashed_password="h",
        is_active=True,
        is_admin=False,
        created_at=datetime.now(UTC),
    )

    mock_session = MagicMock()
    mock_container = MagicMock()
    mock_container.user_repository.get_by_id = AsyncMock(return_value=mock_user)
    mock_container.user_repository.get_by_email = AsyncMock(return_value=other)
    _patch_users_deps(client, mock_session, mock_container)

    response = client.patch("/users/me", json={"email": "taken@example.com"})

    assert response.status_code == 409


def test_update_me_weak_password(client: TestClient, mock_user: User) -> None:
    mock_session = MagicMock()
    mock_container = MagicMock()
    mock_container.user_repository.get_by_id = AsyncMock(return_value=mock_user)
    mock_container.user_repository.get_by_email = AsyncMock(return_value=None)
    _patch_users_deps(client, mock_session, mock_container)

    response = client.patch("/users/me", json={"password": "short"})

    assert response.status_code == 422
