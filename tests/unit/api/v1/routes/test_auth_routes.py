"""
Unit tests for authentication API routes (login, register, me, logout).
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ai_news_digest.api.middleware.exception_handler import setup_exception_handlers
from ai_news_digest.api.middleware.rate_limit import RateLimitMiddleware
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


@contextmanager
def _build_app(
    *,
    user_repo: MagicMock,
    active_user: User | None = None,
) -> Iterator[TestClient]:
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
    original_container = getattr(auth_module, "Container", None)
    auth_module.Container = lambda s: mock_container  # type: ignore[misc]

    if active_user is not None:
        app.dependency_overrides[get_current_active_user] = lambda: active_user

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        if original_container is not None:
            setattr(auth_module, "Container", original_container)  # noqa: B010
        else:
            delattr(auth_module, "Container")


class FakeCacheStore:
    """In-memory async cache store for exercising rate-limit middleware."""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}
        self._expires: dict[str, float | None] = {}
        self._clock_offset = 0.0

    def _now(self) -> float:
        return time.time() + self._clock_offset

    def advance_time(self, seconds: float) -> None:
        """Deterministically simulate the passage of time for TTLs."""
        self._clock_offset += seconds

    def _is_expired(self, key: str) -> bool:
        exp = self._expires.get(key)
        return exp is not None and exp <= self._now()

    async def get(self, key: str) -> str | None:
        if self._is_expired(key):
            self._store.pop(key, None)
            self._expires.pop(key, None)
            return None
        return self._store.get(key)

    async def set(self, key: str, value: str | int, ttl: int | None = None) -> None:
        self._store[key] = str(value)
        self._expires[key] = (self._now() + ttl) if ttl else None

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)
        self._expires.pop(key, None)

    async def exists(self, key: str) -> bool:
        return key in self._store and not self._is_expired(key)

    async def clear(self) -> None:
        self._store.clear()
        self._expires.clear()

    async def ttl(self, key: str) -> int | None:
        exp = self._expires.get(key)
        if exp is None:
            return None
        remaining = exp - self._now()
        return int(remaining) if remaining > 0 else None


@contextmanager
def _build_app_with_middleware(
    *,
    user_repo: MagicMock,
    cache_store: FakeCacheStore,
    **mw_kwargs: object,
) -> Iterator[TestClient]:
    """Build the auth app with the rate-limit/brute-force middleware installed."""
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
    original_container = getattr(auth_module, "Container", None)
    auth_module.Container = lambda s: mock_container  # type: ignore[misc]

    app.add_middleware(RateLimitMiddleware, cache_store=cache_store, **mw_kwargs)

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        if original_container is not None:
            setattr(auth_module, "Container", original_container)  # noqa: B010
        else:
            delattr(auth_module, "Container")


def test_auth_rate_limit_blocks_after_limit(real_user: User) -> None:
    """Auth endpoints enforce a stricter rate limit than general endpoints."""
    user_repo = MagicMock()
    user_repo.get_by_email = AsyncMock(return_value=real_user)
    cache = FakeCacheStore()

    with _build_app_with_middleware(
        user_repo=user_repo,
        cache_store=cache,
        auth_requests_per_window=3,
        auth_max_failed_attempts=100,
    ) as client:
        responses = [
            client.post(
                "/auth/login",
                json={"username": real_user.email, "password": "Password123"},
            )
            for _ in range(4)
        ]

    assert responses[0].status_code == 200
    assert responses[1].status_code == 200
    assert responses[2].status_code == 200
    assert responses[3].status_code == 429


def test_brute_force_locks_account_after_failures(real_user: User) -> None:
    """Repeated failed logins lock the account (and correct creds) temporarily."""
    user_repo = MagicMock()
    user_repo.get_by_email = AsyncMock(return_value=real_user)
    cache = FakeCacheStore()

    with _build_app_with_middleware(
        user_repo=user_repo,
        cache_store=cache,
        auth_requests_per_window=1000,
        auth_max_failed_attempts=3,
        auth_lockout_seconds=300,
    ) as client:
        first = client.post(
            "/auth/login",
            json={"username": real_user.email, "password": "WrongPassword1"},
        )
        second = client.post(
            "/auth/login",
            json={"username": real_user.email, "password": "WrongPassword1"},
        )
        third = client.post(
            "/auth/login",
            json={"username": real_user.email, "password": "WrongPassword1"},
        )
        locked_wrong = client.post(
            "/auth/login",
            json={"username": real_user.email, "password": "WrongPassword1"},
        )
        locked_correct = client.post(
            "/auth/login",
            json={"username": real_user.email, "password": "Password123"},
        )

    assert first.status_code == 401
    assert second.status_code == 401
    assert third.status_code == 401
    assert locked_wrong.status_code == 429
    assert "Retry-After" in locked_wrong.headers
    assert locked_correct.status_code == 429


def test_brute_force_lockout_expires(real_user: User) -> None:
    """Account becomes usable again once the lockout TTL elapses."""
    user_repo = MagicMock()
    user_repo.get_by_email = AsyncMock(return_value=real_user)
    cache = FakeCacheStore()

    with _build_app_with_middleware(
        user_repo=user_repo,
        cache_store=cache,
        auth_requests_per_window=1000,
        auth_max_failed_attempts=3,
        auth_lockout_seconds=300,
    ) as client:
        for _ in range(3):
            client.post(
                "/auth/login",
                json={"username": real_user.email, "password": "WrongPassword1"},
            )
        locked = client.post(
            "/auth/login",
            json={"username": real_user.email, "password": "WrongPassword1"},
        )
        assert locked.status_code == 429

        cache.advance_time(301)

        recovered = client.post(
            "/auth/login",
            json={"username": real_user.email, "password": "Password123"},
        )

    assert recovered.status_code == 200


def test_brute_force_resets_after_success(real_user: User) -> None:
    """A successful login resets the failed-attempt counter for the account."""
    user_repo = MagicMock()
    user_repo.get_by_email = AsyncMock(return_value=real_user)
    cache = FakeCacheStore()

    with _build_app_with_middleware(
        user_repo=user_repo,
        cache_store=cache,
        auth_requests_per_window=1000,
        auth_max_failed_attempts=5,
    ) as client:
        # Two failures, then a success which should clear the counter.
        client.post(
            "/auth/login",
            json={"username": real_user.email, "password": "WrongPassword1"},
        )
        client.post(
            "/auth/login",
            json={"username": real_user.email, "password": "WrongPassword1"},
        )
        success = client.post(
            "/auth/login",
            json={"username": real_user.email, "password": "Password123"},
        )
        # After the reset, the next failure must still be allowed (401, not 429).
        after_reset = client.post(
            "/auth/login",
            json={"username": real_user.email, "password": "WrongPassword1"},
        )

    assert success.status_code == 200
    assert after_reset.status_code == 401


def test_login_success(real_user: User) -> None:
    user_repo = MagicMock()
    user_repo.get_by_email = AsyncMock(return_value=real_user)
    with _build_app(user_repo=user_repo) as client:
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
    with _build_app(user_repo=user_repo) as client:
        response = client.post(
            "/auth/login",
            json={"username": real_user.email, "password": "WrongPassword1"},
        )

    assert response.status_code == 401


def test_login_unknown_user() -> None:
    user_repo = MagicMock()
    user_repo.get_by_email = AsyncMock(return_value=None)
    with _build_app(user_repo=user_repo) as client:
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
    with _build_app(user_repo=user_repo) as client:
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
    with _build_app(user_repo=user_repo) as client:
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
    with _build_app(user_repo=user_repo) as client:
        response = client.post(
            "/auth/register",
            json={"email": "dup@example.com", "password": "Password123"},
        )

    assert response.status_code == 400


def test_me_returns_profile(real_user: User) -> None:
    with _build_app(user_repo=MagicMock(), active_user=real_user) as client:
        response = client.get("/auth/me")

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == real_user.email
    assert "hashed_password" not in data


def test_logout_requires_auth() -> None:
    with _build_app(user_repo=MagicMock()) as client:
        response = client.post("/auth/logout")

    assert response.status_code == 401


def test_logout_success(real_user: User) -> None:
    with _build_app(user_repo=MagicMock(), active_user=real_user) as client:
        response = client.post("/auth/logout")

    assert response.status_code == 200
    assert response.json()["message"]


def test_me_malformed_token() -> None:
    with _build_app(user_repo=MagicMock()) as client:
        response = client.get(
            "/auth/me",
            headers={"Authorization": "Bearer not-a-valid-jwt-token"},
        )

    assert response.status_code == 401
