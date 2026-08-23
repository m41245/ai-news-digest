"""
Unit tests for the digest deliveries API route.
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
from ai_news_digest.api.v1.dependencies.dependencies import get_container
from ai_news_digest.api.v1.routes.digests import router
from ai_news_digest.domain.enums.delivery_status import DeliveryStatus
from ai_news_digest.domain.models.digest import Digest
from ai_news_digest.domain.models.digest_delivery import DigestDelivery
from ai_news_digest.domain.models.user import User


@pytest.fixture
def mock_user() -> User:
    return User(
        id=uuid4(),
        email="test@example.com",
        hashed_password="hashed",
        is_active=True,
        is_admin=False,
        created_at=datetime.now(UTC),
    )


@pytest.fixture
def mock_digest_id() -> object:
    return uuid4()


def _client(container: MagicMock, mock_user: User) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_container] = lambda: container
    app.dependency_overrides[get_current_active_user] = lambda: mock_user
    setup_exception_handlers(app)
    return TestClient(app)


def test_list_deliveries(
    mock_user: User,
    mock_digest_id: object,
) -> None:
    delivery = DigestDelivery(
        id=uuid4(),
        digest_id=mock_digest_id,  # type: ignore[arg-type]
        recipient="reader@example.com",
        status=DeliveryStatus.SENT,
        attempt_count=1,
        sent_at=datetime.now(UTC),
        failed_at=None,
        failure_reason=None,
        provider_message_id="msg-1",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    digest = Digest(
        id=mock_digest_id,  # type: ignore[arg-type]
        title="Daily Digest",
        content="content",
        generated_at=datetime.now(UTC),
        format="markdown",
    )
    container = MagicMock()
    container.digest_repository.get_by_id = AsyncMock(return_value=digest)
    container.delivery_repository.list_by_digest = AsyncMock(return_value=[delivery])

    client = _client(container, mock_user)
    response = client.get(f"/digests/{mock_digest_id}/deliveries")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["recipient"] == "reader@example.com"
    assert data[0]["status"] == "sent"


def test_list_deliveries_unknown_digest(
    mock_user: User,
    mock_digest_id: object,
) -> None:
    container = MagicMock()
    container.digest_repository.get_by_id = AsyncMock(return_value=None)

    client = _client(container, mock_user)
    response = client.get(f"/digests/{mock_digest_id}/deliveries")

    assert response.status_code == 404


def test_list_deliveries_requires_auth(mock_digest_id: object) -> None:
    app = FastAPI()
    app.include_router(router)
    setup_exception_handlers(app)
    client = TestClient(app)

    response = client.get(f"/digests/{mock_digest_id}/deliveries")

    assert response.status_code == 401
