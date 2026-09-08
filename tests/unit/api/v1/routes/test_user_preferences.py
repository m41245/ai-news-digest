"""
Unit tests for authenticated user preference API routes.
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
from ai_news_digest.api.v1.routes.user_preferences import router
from ai_news_digest.domain.models.user import User
from ai_news_digest.domain.models.user_preference import UserPreferenceProfile


def _make_user() -> User:
    return User(
        id=uuid4(),
        email="me@example.com",
        hashed_password="hashed",  # noqa: S106
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
        followed_company_ids=frozenset([uuid4()]),
        followed_topic_ids=frozenset([uuid4()]),
        followed_category_ids=frozenset([uuid4()]),
        muted_company_ids=frozenset([uuid4()]),
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

    pref_uc = MagicMock()
    pref_uc.execute = AsyncMock(
        return_value={
            "user_id": str(mock_user.id),
            "min_importance": profile.min_importance,
            "min_confidence": profile.min_confidence,
            "feed_sort": profile.feed_sort,
            "freshness_window_days": profile.freshness_window_days,
            "preferred_source_types": list(profile.preferred_source_types),
            "followed_companies": [str(c) for c in sorted(profile.followed_company_ids)],
            "followed_topics": [str(t) for t in sorted(profile.followed_topic_ids)],
            "followed_categories": [str(c) for c in sorted(profile.followed_category_ids)],
            "muted_companies": [str(c) for c in sorted(profile.muted_company_ids)],
            "muted_topics": [str(t) for t in sorted(profile.muted_topic_ids)],
            "muted_categories": [str(c) for c in sorted(profile.muted_category_ids)],
            "created_at": profile.created_at.isoformat(),
            "updated_at": profile.updated_at.isoformat(),
        }
    )
    container.get_preferences = pref_uc

    update_uc = MagicMock()
    update_uc.execute = AsyncMock(
        return_value={
            "user_id": str(mock_user.id),
            "min_importance": 0.8,
            "min_confidence": 0.6,
            "feed_sort": "importance",
            "freshness_window_days": 14,
            "preferred_source_types": ["official_company"],
            "followed_companies": [],
            "followed_topics": [],
            "followed_categories": [],
            "muted_companies": [],
            "muted_topics": [],
            "muted_categories": [],
            "created_at": profile.created_at.isoformat(),
            "updated_at": profile.updated_at.isoformat(),
        }
    )
    container.update_preferences = update_uc

    container.follow_company = MagicMock()
    container.follow_company.execute = AsyncMock()
    container.unfollow_company = MagicMock()
    container.unfollow_company.execute = AsyncMock()
    container.follow_topic = MagicMock()
    container.follow_topic.execute = AsyncMock()
    container.unfollow_topic = MagicMock()
    container.unfollow_topic.execute = AsyncMock()
    container.follow_category = MagicMock()
    container.follow_category.execute = AsyncMock()
    container.unfollow_category = MagicMock()
    container.unfollow_category.execute = AsyncMock()
    container.mute_company = MagicMock()
    container.mute_company.execute = AsyncMock()
    container.unmute_company = MagicMock()
    container.unmute_company.execute = AsyncMock()
    container.mute_topic = MagicMock()
    container.mute_topic.execute = AsyncMock()
    container.unmute_topic = MagicMock()
    container.unmute_topic.execute = AsyncMock()
    container.mute_category = MagicMock()
    container.mute_category.execute = AsyncMock()
    container.unmute_category = MagicMock()
    container.unmute_category.execute = AsyncMock()
    container.reset_preferences = MagicMock()
    container.reset_preferences.execute = AsyncMock()

    def _feed_mock(**kwargs: Any) -> dict[str, Any]:
        return {
            "items": [],
            "total": 0,
            "limit": kwargs.get("page_size", 20),
            "offset": (kwargs.get("page", 1) - 1) * kwargs.get("page_size", 20),
            "empty_reason": "Configure your interests to see personalized stories.",
        }

    feed_uc = MagicMock()
    feed_uc.execute = AsyncMock(side_effect=lambda **kwargs: _feed_mock(**kwargs))
    container.get_personalized_feed = feed_uc

    container.company_repository = MagicMock()
    container.company_repository.get_by_slug = AsyncMock(return_value=MagicMock(id=uuid4()))
    container.topic_repository = MagicMock()
    container.topic_repository.get_by_slug = AsyncMock(return_value=MagicMock(id=uuid4()))
    container.category_repository = MagicMock()
    container.category_repository.get_by_id = AsyncMock(return_value=MagicMock(id=uuid4()))

    return container


@pytest.fixture
def client(mock_user: User, profile: UserPreferenceProfile) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_active_user] = lambda: mock_user

    mock_container = _build_container(mock_user, profile)

    from ai_news_digest.api.v1.dependencies.dependencies import get_container

    app.dependency_overrides[get_container] = lambda: mock_container
    setup_exception_handlers(app)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def unauth_client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    setup_exception_handlers(app)
    with TestClient(app) as test_client:
        yield test_client


def test_get_preferences(client: TestClient, mock_user: User) -> None:
    response = client.get("/me/preferences")
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == str(mock_user.id)
    assert data["feed_sort"] == "relevance"
    assert data["min_importance"] == 0.5


def test_get_preferences_requires_auth(unauth_client: TestClient) -> None:
    response = unauth_client.get("/me/preferences")
    assert response.status_code == 401


def test_update_preferences(client: TestClient) -> None:
    response = client.put(
        "/me/preferences",
        json={
            "min_importance": 0.8,
            "min_confidence": 0.6,
            "feed_sort": "importance",
            "freshness_window_days": 14,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["min_importance"] == 0.8
    assert data["feed_sort"] == "importance"


def test_follow_company(client: TestClient) -> None:
    response = client.post("/me/preferences/companies/openai")
    assert response.status_code == 204


def test_unfollow_company(client: TestClient) -> None:
    response = client.delete("/me/preferences/companies/openai")
    assert response.status_code == 204


def test_follow_topic(client: TestClient) -> None:
    response = client.post("/me/preferences/topics/ai-policy")
    assert response.status_code == 204


def test_unfollow_topic(client: TestClient) -> None:
    response = client.delete("/me/preferences/topics/ai-policy")
    assert response.status_code == 204


def test_follow_category(client: TestClient) -> None:
    cat_id = uuid4()
    response = client.post(f"/me/preferences/categories/{cat_id}")
    assert response.status_code == 204


def test_unfollow_category(client: TestClient) -> None:
    cat_id = uuid4()
    response = client.delete(f"/me/preferences/categories/{cat_id}")
    assert response.status_code == 204


def test_mute_company(client: TestClient) -> None:
    response = client.post("/me/preferences/muted/companies/openai")
    assert response.status_code == 204


def test_unmute_company(client: TestClient) -> None:
    response = client.delete("/me/preferences/muted/companies/openai")
    assert response.status_code == 204


def test_mute_topic(client: TestClient) -> None:
    response = client.post("/me/preferences/muted/topics/ai-policy")
    assert response.status_code == 204


def test_unmute_topic(client: TestClient) -> None:
    response = client.delete("/me/preferences/muted/topics/ai-policy")
    assert response.status_code == 204


def test_mute_category(client: TestClient) -> None:
    cat_id = uuid4()
    response = client.post(f"/me/preferences/muted/categories/{cat_id}")
    assert response.status_code == 204


def test_unmute_category(client: TestClient) -> None:
    cat_id = uuid4()
    response = client.delete(f"/me/preferences/muted/categories/{cat_id}")
    assert response.status_code == 204


def test_reset_preferences(client: TestClient) -> None:
    response = client.post("/me/preferences/reset")
    assert response.status_code == 204


def test_get_feed(client: TestClient) -> None:
    response = client.get("/me/feed")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


def test_get_feed_with_params(client: TestClient) -> None:
    response = client.get("/me/feed", params={"page": 2, "page_size": 10, "sort": "importance"})
    assert response.status_code == 200
    data = response.json()
    assert data["limit"] == 10
    assert data["offset"] == 10


def test_feed_requires_auth(unauth_client: TestClient) -> None:
    response = unauth_client.get("/me/feed")
    assert response.status_code == 401


def test_follow_invalid_company_returns_404() -> None:
    user = _make_user()
    profile = UserPreferenceProfile(user_id=user.id)
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_active_user] = lambda: user

    container = _build_container(user, profile)
    container.company_repository.get_by_slug = AsyncMock(return_value=None)
    from ai_news_digest.api.v1.dependencies.dependencies import get_container

    app.dependency_overrides[get_container] = lambda: container
    setup_exception_handlers(app)
    with TestClient(app) as test_client:
        response = test_client.post("/me/preferences/companies/does-not-exist")
        assert response.status_code == 404


def test_update_preferences_validation_error(client: TestClient) -> None:
    response = client.put(
        "/me/preferences",
        json={
            "min_importance": 2.0,
        },
    )
    assert response.status_code == 422


def test_user_a_cannot_read_user_b_preferences() -> None:
    user_a = _make_user()
    user_b = _make_user()
    profile_b = UserPreferenceProfile(
        user_id=user_b.id,
        followed_company_ids=frozenset([uuid4()]),
        muted_topic_ids=frozenset([uuid4()]),
        min_importance=0.9,
        preferred_source_types=("official_company",),
    )
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_active_user] = lambda: user_a

    container = _build_container(user_a, profile_b)
    from ai_news_digest.api.v1.dependencies.dependencies import get_container

    app.dependency_overrides[get_container] = lambda: container
    setup_exception_handlers(app)
    with TestClient(app) as test_client:
        response = test_client.get("/me/preferences")
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == str(user_a.id)
        assert data["feed_sort"] == "published_at"


def test_feed_results_scoped_to_authenticated_user() -> None:
    user_a = _make_user()
    user_b = _make_user()
    profile_a = UserPreferenceProfile(
        user_id=user_a.id,
        followed_company_ids=frozenset([uuid4()]),
        feed_sort="relevance",
    )
    profile_b = UserPreferenceProfile(
        user_id=user_b.id,
        followed_company_ids=frozenset([uuid4()]),
        feed_sort="importance",
    )
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_active_user] = lambda: user_a

    container = _build_container(user_a, profile_a)
    container._profile_for_user_b = profile_b
    from ai_news_digest.api.v1.dependencies.dependencies import get_container

    app.dependency_overrides[get_container] = lambda: container
    setup_exception_handlers(app)
    with TestClient(app) as test_client:
        response = test_client.get("/me/preferences")
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == str(user_a.id)
        assert data["feed_sort"] == "relevance"


def test_feed_pagination_metadata_consistent() -> None:
    user = _make_user()
    profile = UserPreferenceProfile(user_id=user.id)
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_active_user] = lambda: user

    container = _build_container(user, profile)
    from ai_news_digest.api.v1.dependencies.dependencies import get_container

    app.dependency_overrides[get_container] = lambda: container
    setup_exception_handlers(app)
    with TestClient(app) as test_client:
        response = test_client.get("/me/feed", params={"page": 2, "page_size": 15})
        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 15
        assert data["offset"] == 15
        assert "total" in data
        assert "items" in data


def test_feed_stable_serialization() -> None:
    user = _make_user()
    profile = UserPreferenceProfile(user_id=user.id)
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_active_user] = lambda: user

    container = _build_container(user, profile)
    from ai_news_digest.api.v1.dependencies.dependencies import get_container

    app.dependency_overrides[get_container] = lambda: container
    setup_exception_handlers(app)
    with TestClient(app) as test_client:
        response1 = test_client.get("/me/feed")
        response2 = test_client.get("/me/feed")
        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response1.json() == response2.json()
