from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from ai_news_digest.api.middleware.exception_handler import setup_exception_handlers
from ai_news_digest.api.v1.dependencies.auth import get_current_admin_user
from ai_news_digest.api.v1.dependencies.dependencies import get_container
from ai_news_digest.api.v1.routes.admin import router
from ai_news_digest.domain.enums.source_status import SourceStatus
from ai_news_digest.domain.models.source import Source
from ai_news_digest.domain.models.user import User


@pytest.fixture
def mock_source() -> Source:
    return Source.create(
        name="Test Source",
        feed_url="https://example.com/feed.xml",
        status=SourceStatus.PENDING_REVIEW,
        is_active=True,
    )


@pytest.fixture
def mock_admin_user() -> User:
    return User.create(
        email="admin@example.com",
        hashed_password="hashed",  # noqa: S106
        is_active=True,
        is_admin=True,
    )


@pytest.fixture
def client(mock_source: Source, mock_admin_user: User) -> TestClient:
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    setup_exception_handlers(app)

    mock_container = MagicMock()
    mock_container.source_repository.get_by_id = AsyncMock(return_value=mock_source)
    mock_container.source_repository.update = AsyncMock(return_value=mock_source)
    mock_container.source_repository.commit = AsyncMock()
    mock_container.source_repository.rollback = AsyncMock()
    mock_container.source_trust_decision_repository.create = AsyncMock()
    mock_container.source_trust_decision_repository.commit = AsyncMock()
    mock_container.source_trust_decision_repository.rollback = AsyncMock()
    mock_fetcher = AsyncMock()
    mock_fetcher.fetch = AsyncMock(return_value=[MagicMock()])
    mock_container.rss_fetcher = mock_fetcher

    from unittest.mock import MagicMock as _MagicMock

    def _make_result(decision: str) -> _MagicMock:
        result = _MagicMock()
        result.id = mock_source.id
        result.name = mock_source.name
        result.feed_url = mock_source.feed_url
        result.website_url = mock_source.website_url
        result.description = mock_source.description
        result.is_active = mock_source.is_active
        result.status = mock_source.status.value
        result.decision = decision
        result.previous_status = mock_source.status.value
        result.previous_is_active = mock_source.is_active
        result.reason = "reason"
        result.validation_outcome = None
        result.changed = True
        return result

    for decision, attr in (
        ("APPROVE", "approve_source"),
        ("REJECT", "reject_source"),
        ("DEACTIVATE", "deactivate_source"),
    ):
        uc = _MagicMock()
        uc.execute = AsyncMock(return_value=_make_result(decision))
        setattr(mock_container, attr, uc)

    app.dependency_overrides[get_container] = lambda: mock_container
    app.dependency_overrides[get_current_admin_user] = lambda: mock_admin_user
    with TestClient(app) as test_client:
        yield test_client


def test_admin_approve_source(client: TestClient) -> None:
    source_id = uuid4()
    response = client.post(
        f"/admin/sources/{source_id}/approve",
        json={"reason": "approved"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "APPROVE"
    assert data["changed"] is True


def test_admin_reject_source(client: TestClient) -> None:
    source_id = uuid4()
    response = client.post(
        f"/admin/sources/{source_id}/reject",
        json={"reason": "rejected"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "REJECT"


def test_admin_deactivate_source(client: TestClient) -> None:
    source_id = uuid4()
    response = client.post(
        f"/admin/sources/{source_id}/deactivate",
        json={"reason": "deactivated"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "DEACTIVATE"


def test_admin_approve_propagates_authenticated_actor(
    client: TestClient, mock_admin_user: User
) -> None:
    source_id = uuid4()
    response = client.post(
        f"/admin/sources/{source_id}/approve",
        json={"reason": "approved"},
    )

    assert response.status_code == 200
    mock_container = client.app.dependency_overrides[get_container]()
    call = mock_container.approve_source.execute.call_args
    assert call.kwargs.get("actor_user_id") == mock_admin_user.id


def test_admin_source_decision_requires_admin() -> None:
    from fastapi import FastAPI

    from ai_news_digest.api.v1.dependencies.auth import get_current_active_user
    from ai_news_digest.api.v1.dependencies.dependencies import get_container

    app = FastAPI()
    app.include_router(router)
    setup_exception_handlers(app)

    non_admin = User.create(
        email="user@example.com",
        hashed_password="hashed",  # noqa: S106
        is_active=True,
        is_admin=False,
    )

    mock_container = MagicMock()
    app.dependency_overrides[get_container] = lambda: mock_container
    app.dependency_overrides[get_current_active_user] = lambda: non_admin

    with TestClient(app) as test_client:
        response = test_client.post(
            f"/admin/sources/{uuid4()}/approve",
            json={"reason": "approved"},
        )

    assert response.status_code == 403


def test_admin_source_decision_unauthenticated() -> None:
    from fastapi import FastAPI

    from ai_news_digest.api.v1.dependencies.dependencies import get_container

    app = FastAPI()
    app.include_router(router)
    setup_exception_handlers(app)

    mock_container = MagicMock()
    app.dependency_overrides[get_container] = lambda: mock_container

    with TestClient(app) as test_client:
        response = test_client.post(
            f"/admin/sources/{uuid4()}/approve",
            json={"reason": "approved"},
        )

    assert response.status_code == 401
