from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ai_news_digest.api.middleware.exception_handler import setup_exception_handlers
from ai_news_digest.api.v1.dependencies.dependencies import get_container
from ai_news_digest.api.v1.routes.timeline import router as timeline_router
from ai_news_digest.domain.enums.cluster_status import ClusterStatus
from ai_news_digest.domain.models.story_cluster import StoryCluster


@pytest.fixture
def app() -> FastAPI:
    app = FastAPI()
    app.include_router(timeline_router, prefix="/api/v1/public")
    return app


@pytest.fixture
def mock_container() -> MagicMock:
    container = MagicMock()
    container.story_cluster_repository.get_by_id = AsyncMock()
    container.story_event_repository.list_by_cluster_id = AsyncMock(return_value=[])
    return container


@pytest.fixture
def client(app: FastAPI, mock_container: MagicMock) -> TestClient:
    app.dependency_overrides[get_container] = lambda: mock_container
    setup_exception_handlers(app)
    return TestClient(app)


def test_get_timeline_success(
    client: TestClient,
    mock_container: MagicMock,
) -> None:
    cluster = StoryCluster(
        id=uuid4(),
        title="Test Cluster",
        slug="test-cluster",
        first_published_at=datetime(2026, 9, 1, tzinfo=UTC),
        last_updated_at=datetime(2026, 9, 1, tzinfo=UTC),
        status=ClusterStatus.ACTIVE,
    )
    mock_container.story_cluster_repository.get_by_id.return_value = cluster
    mock_container.story_event_repository.list_by_cluster_id.return_value = []
    response = client.get(f"/api/v1/public/story-clusters/{cluster.id}/timeline")
    assert response.status_code == 200
    data = response.json()
    assert data["cluster_id"] == str(cluster.id)
    assert data["events"] == []


def test_get_timeline_cluster_not_found(
    client: TestClient,
    mock_container: MagicMock,
) -> None:
    mock_container.story_cluster_repository.get_by_id.return_value = None
    response = client.get(f"/api/v1/public/story-clusters/{uuid4()}/timeline")
    assert response.status_code == 404


__all__ = [
    "test_get_timeline_cluster_not_found",
    "test_get_timeline_success",
]
