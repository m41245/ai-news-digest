"""
Unit tests for authentication API routes (login, register, me, logout).
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
from ai_news_digest.api.v1.routes.auth import router
from ai_news_digest.domain.models.user import User
from ai_news_digest.infrastructure.auth.password import hash_password


@pytest.fixture
def real_user() -> User:
    return User(
        id=uuid4(),
        email="alice@example.com",
        hashed_password=hash_password("Password123"),
        is_active=True,
        is_admin=False,
        created_at=datetime.now(UTC),
    )


def _build_app(
    *,
    user_repo: MagicMock,
    active_user: User | None = None,
) -> TestClient:
    from ai_news_digest.api.v1.routes import auth as auth_module

    app = FastAPI()
    app.include_router(router)
    setup_exception_handlers(app)

    mock_session = MagicMock()
    mock_container = MagicMock()
    mock_container.user_repository = user_repo

    async def _mock_session() -> MagicMock:
        yield mock_session

    app.dependency_overrides[auth_module.get_db_session] = lambda: _mock_session()
    auth_module.Container = lambda s: mock_container  # type: ignore[misc]

    if active_user is not None:
        app.dependency_overrides[get_current_active_user] = lambda: active_user

    return TestClient(app)


def test_login_success(real_user: User) -> None:
    user_repo = MagicMock()
    user_repo.get_by_email = AsyncMock(return_value=real_user)
    client = _build_app(user_repo=user_repo)

    response = client.post(
        "/auth/login",
        json={"username": real_user.email, "password": "Password123"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert data["access_token"]


def test_login_wrong_password(real_user: User) -> None:
    user_repo = MagicMock()
    user_repo.get_by_email = AsyncMock(return_value=real_user)
    client = _build_app(user_repo=user_repo)

    response = client.post(
        "/auth/login",
        json={"username": real_user.email, "password": "WrongPassword1"},
    )

    assert response.status_code == 401


def test_login_unknown_user() -> None:
    user_repo = MagicMock()
    user_repo.get_by_email = AsyncMock(return_value=None)
    client = _build_app(user_repo=user_repo)

    response = client.post(
        "/auth/login",
        json={"username": "nobody@example.com", "password": "Password123"},
    )

    assert response.status_code == 401


def test_login_inactive_user() -> None:
    user = User(
        id=uuid4(),
        email="inactive@example.com",
        hashed_password=hash_password("Password123"),
        is_active=False,
        is_admin=False,
        created_at=datetime.now(UTC),
    )
    user_repo = MagicMock()
    user_repo.get_by_email = AsyncMock(return_value=user)
    client = _build_app(user_repo=user_repo)

    response = client.post(
        "/auth/login",
        json={"username": user.email, "password": "Password123"},
    )

    assert response.status_code == 401


def test_register_success() -> None:
    created = User(
        id=uuid4(),
        email="new@example.com",
        hashed_password="hashed",
        is_active=True,
        is_admin=False,
        created_at=datetime.now(UTC),
    )
    user_repo = MagicMock()
    user_repo.get_by_email = AsyncMock(return_value=None)
    user_repo.create = AsyncMock(return_value=created)
    client = _build_app(user_repo=user_repo)

    response = client.post(
        "/auth/register",
        json={"email": "new@example.com", "password": "Password123"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "new@example.com"
    assert data["is_admin"] is False
    assert "hashed_password" not in data


def test_register_duplicate_email() -> None:
    existing = User(
        id=uuid4(),
        email="dup@example.com",
        hashed_password="h",
        is_active=True,
        is_admin=False,
        created_at=datetime.now(UTC),
    )
    user_repo = MagicMock()
    user_repo.get_by_email = AsyncMock(return_value=existing)
    client = _build_app(user_repo=user_repo)

    response = client.post(
        "/auth/register",
        json={"email": "dup@example.com", "password": "Password123"},
    )

    assert response.status_code == 400


def test_me_returns_profile(real_user: User) -> None:
    client = _build_app(user_repo=MagicMock(), active_user=real_user)

    response = client.get("/auth/me")

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == real_user.email
    assert "hashed_password" not in data


def test_logout_requires_auth() -> None:
    client = _build_app(user_repo=MagicMock())

    response = client.post("/auth/logout")

    assert response.status_code == 401


def test_logout_success(real_user: User) -> None:
    client = _build_app(user_repo=MagicMock(), active_user=real_user)

    response = client.post("/auth/logout")

    assert response.status_code == 200
    assert response.json()["message"]


def test_me_malformed_token() -> None:
    client = _build_app(user_repo=MagicMock())

    response = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer not-a-valid-jwt-token"},
    )

    assert response.status_code == 401
