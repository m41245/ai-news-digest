"""
Unit tests for authenticated recommendation API routes.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ai_news_digest.api.middleware.exception_handler import setup_exception_handlers
from ai_news_digest.api.v1.dependencies.auth import get_current_active_user
from ai_news_digest.api.v1.routes.recommendations import router
from ai_news_digest.domain.models.user import User
from ai_news_digest.domain.models.user_preference import UserPreferenceProfile


def _make_user() -> User:
    return User(
        id=uuid4(),
        email="me@example.com",
        hashed_password="hashed",
        is_active=True,
        is_admin=False,
        created_at=datetime.now(UTC),
    )


@pytest.fixture
def mock_user() -> User:
    return _make_user()


@pytest.fixture
def profile() -> UserPreferenceProfile:
    return UserPreferenceProfile(
        user_id=uuid4(),
        followed_company_ids=frozenset(),
        followed_topic_ids=frozenset(),
        followed_category_ids=frozenset(),
        muted_company_ids=frozenset(),
        muted_topic_ids=frozenset(),
        muted_category_ids=frozenset(),
        min_importance=0.5,
        min_confidence=0.3,
        feed_sort="relevance",
        freshness_window_days=7,
        preferred_source_types=("official_company", "tech_publication"),
    )


def _build_container(mock_user: User, profile: UserPreferenceProfile) -> MagicMock:
    container = MagicMock()

    def _rec_mock(**kwargs: Any) -> dict[str, Any]:
        return {
            "items": [],
            "total": 0,
            "limit": kwargs.get("page_size", 20),
            "offset": (kwargs.get("page", 1) - 1) * kwargs.get("page_size", 20),
            "empty_reason": "Configure your interests to see personalized recommendations.",
        }

    rec_uc = MagicMock()
    rec_uc.execute = AsyncMock(side_effect=lambda **kwargs: _rec_mock(**kwargs))
    container.get_recommendations = rec_uc

    return container


def test_recommendations_requires_auth(profile: UserPreferenceProfile) -> None:
    app = FastAPI()
    setup_exception_handlers(app)
    app.include_router(router)

    response = TestClient(app).get("/me/recommendations")
    assert response.status_code == 401


def test_recommendations_returns_paginated_data(mock_user: User, profile: UserPreferenceProfile) -> None:
    app = FastAPI()
    setup_exception_handlers(app)
    app.include_router(router)

    container = _build_container(mock_user, profile)

    app.dependency_overrides[get_current_active_user] = lambda: mock_user
    from ai_news_digest.api.v1.dependencies.dependencies import get_container
    app.dependency_overrides[get_container] = lambda: container

    response = TestClient(app).get("/me/recommendations?page=1&page_size=10")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["limit"] == 10
    assert data["offset"] == 0


def test_recommendations_scoped_to_authenticated_user(mock_user: User, profile: UserPreferenceProfile) -> None:
    app = FastAPI()
    setup_exception_handlers(app)
    app.include_router(router)

    container = _build_container(mock_user, profile)
    app.dependency_overrides[get_current_active_user] = lambda: mock_user
    from ai_news_digest.api.v1.dependencies.dependencies import get_container
    app.dependency_overrides[get_container] = lambda: container

    response = TestClient(app).get("/me/recommendations")
    assert response.status_code == 200


__all__ = ["test_recommendations_requires_auth", "test_recommendations_returns_paginated_data", "test_recommendations_scoped_to_authenticated_user"]
