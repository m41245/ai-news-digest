"""
Unit tests for graph intelligence API routes.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from ai_news_digest.api.middleware.exception_handler import setup_exception_handlers
from ai_news_digest.api.v1.dependencies.dependencies import get_container
from ai_news_digest.api.v1.routes.graph import router
from ai_news_digest.domain.enums.entity_type import EntityType
from ai_news_digest.domain.enums.relationship_status import RelationshipStatus
from ai_news_digest.domain.enums.relationship_type import RelationshipType
from ai_news_digest.domain.models.relationship import (
    ProvenanceSource,
    Relationship,
)
from ai_news_digest.domain.models.story_cluster import StoryCluster


def _make_relationship(
    subject_type: str = "story",
    subject_id: str | None = None,
    rel_type: str = "related_to",
    object_type: str = "company",
    object_id: str | None = None,
    status: str = "verified",
    confidence: float | None = 0.9,
    provenance: str = "deterministic",
    article_id: str | None = None,
) -> Relationship:
    subj_id = uuid4()
    obj_id = uuid4()
    return Relationship.create(
        subject_entity_type=EntityType(subject_type),
        subject_entity_id=subj_id,
        relationship_type=RelationshipType(rel_type),
        object_entity_type=EntityType(object_type),
        object_entity_id=obj_id,
        status=RelationshipStatus(status),
        confidence=confidence,
        provenance_source=ProvenanceSource(provenance),
        article_id=uuid4(),
    )


def _make_story_cluster(cluster_id: str | None = None) -> StoryCluster:
    return StoryCluster(
        id=uuid4(),
        title="Test Story",
        slug="test-story",
        status="active",
        importance_score=0.8,
        confidence=0.9,
    )


@pytest.fixture
def mock_container() -> MagicMock:
    container = MagicMock()
    container.relationship_repository.list_for_entity = AsyncMock(return_value=[])
    container.relationship_repository.list_for_entity_with_temporal = AsyncMock(
        return_value=[]
    )
    container.relationship_repository.get_entity_relationship_history = (
        AsyncMock(return_value=[])
    )
    container.story_cluster_repository.get_by_id = AsyncMock(
        return_value=_make_story_cluster()
    )
    container.company_repository.list_by_ids = AsyncMock(return_value=[])
    container.topic_repository.list_by_ids = AsyncMock(return_value=[])
    container.category_repository.list_by_ids = AsyncMock(return_value=[])
    container.story_cluster_repository.get_by_ids = AsyncMock(return_value=[])
    return container


@pytest.fixture
def client(mock_container: MagicMock) -> TestClient:
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/public")
    app.dependency_overrides[get_container] = lambda: mock_container
    setup_exception_handlers(app)
    with TestClient(app) as test_client:
        yield test_client


class TestGraphRoutes:
    """Tests for graph intelligence API routes."""

    def test_get_entity_connections_enabled(
        self, client: TestClient, mock_container: MagicMock
    ) -> None:
        """When knowledge_graph_enabled is True, return connections."""
        with patch("ai_news_digest.api.v1.routes.graph.get_settings") as mock_settings:
            mock_settings.return_value.knowledge_graph_enabled = True
            entity_id = uuid4()
            response = client.get(
                f"/api/v1/public/graph/entities/company/{entity_id}/connections"
            )
            assert response.status_code == 200
            data = response.json()
            assert "connections" in data
            assert data["total"] == 0

    def test_get_entity_connections_invalid_type(
        self, client: TestClient
    ) -> None:
        """Invalid entity type should return empty."""
        with patch("ai_news_digest.api.v1.routes.graph.get_settings") as mock_settings:
            mock_settings.return_value.knowledge_graph_enabled = True
            entity_id = uuid4()
            response = client.get(
                f"/api/v1/public/graph/entities/invalid/{entity_id}/connections"
            )
            assert response.status_code == 200
            data = response.json()
            assert data["connections"] == []

    def test_get_story_cluster_connections_not_found(
        self, client: TestClient, mock_container: MagicMock
    ) -> None:
        """Non-existent story cluster should return 404."""
        mock_container.story_cluster_repository.get_by_id = AsyncMock(
            return_value=None
        )
        with patch("ai_news_digest.api.v1.routes.graph.get_settings") as mock_settings:
            mock_settings.return_value.knowledge_graph_enabled = True
            response = client.get(
                f"/api/v1/public/graph/story-clusters/{uuid4()}/connections"
            )
            assert response.status_code == 404

    def test_find_graph_path_enabled(self, client: TestClient) -> None:
        """When knowledge_graph_enabled is True, return path response."""
        with patch("ai_news_digest.api.v1.routes.graph.get_settings") as mock_settings:
            mock_settings.return_value.knowledge_graph_enabled = True
            response = client.get(
                f"/api/v1/public/graph/path/story/{uuid4()}/company/{uuid4()}"
            )
            assert response.status_code == 200
            data = response.json()
            assert "length" in data
            assert "explanation" in data

    def test_find_graph_path_no_path(self, client: TestClient) -> None:
        """Unconnected entities should return empty path."""
        with patch("ai_news_digest.api.v1.routes.graph.get_settings") as mock_settings:
            mock_settings.return_value.knowledge_graph_enabled = True
            response = client.get(
                f"/api/v1/public/graph/path/story/{uuid4()}/company/{uuid4()}"
            )
            assert response.status_code == 200
            data = response.json()
            assert data["length"] == 0


__all__ = ["TestGraphRoutes"]
