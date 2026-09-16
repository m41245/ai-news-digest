"""
Unit tests for intelligence quality API routes (M92).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from ai_news_digest.api.middleware.exception_handler import setup_exception_handlers
from ai_news_digest.api.v1.dependencies.dependencies import get_container
from ai_news_digest.api.v1.routes.intelligence_quality import router
from ai_news_digest.domain.models.claim import Claim
from ai_news_digest.domain.models.conflict import Conflict
from ai_news_digest.domain.models.story_cluster import StoryCluster
from ai_news_digest.domain.models.story_activity import StoryActivity


def _make_claim(claim_id=None) -> Claim:
    return Claim(
        id=claim_id or uuid4(),
        article_id=uuid4(),
        source_id=uuid4(),
        claim_text="Test claim",
        claim_type="fact",
        confidence=0.9,
        status="supported",
    )


def _make_cluster(cluster_id=None) -> StoryCluster:
    return StoryCluster(
        id=cluster_id or uuid4(),
        title="Test Story",
        slug="test-story",
        importance_score=0.8,
        confidence=0.9,
    )


@pytest.fixture
def mock_container() -> MagicMock:
    container = MagicMock()
    container.claim_repository.get_by_id = AsyncMock()
    container.claim_repository.list_evidence_by_claim_id = AsyncMock(return_value=[])
    container.conflict_repository.list_recent = AsyncMock(return_value=[])
    container.relationship_repository.get_by_id = AsyncMock()
    container.story_cluster_repository.get_by_id = AsyncMock()
    container.story_cluster_repository.get_by_ids = AsyncMock(return_value=[])
    container.article_repository.list_by_cluster_id = AsyncMock(return_value=[])
    container.article_repository.list_public_articles = AsyncMock(return_value=[])
    container.trend_repository.get_by_id = AsyncMock()
    return container


@pytest.fixture
def client(mock_container: MagicMock) -> TestClient:
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_container] = lambda: mock_container
    setup_exception_handlers(app)
    with TestClient(app) as test_client:
        yield test_client


class TestIntelligenceQualityRoutes:
    def test_get_claim_provenance(self, client: TestClient, mock_container: MagicMock) -> None:
        claim = _make_claim()
        mock_container.claim_repository.get_by_id.return_value = claim
        claim_id = claim.id
        response = client.get(f"/api/v1/intelligence/provenance/claim/{claim_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["intelligence_type"] == "claim"
        assert data["entity_id"] == str(claim_id)

    def test_get_claim_quality(self, client: TestClient, mock_container: MagicMock) -> None:
        claim = _make_claim()
        mock_container.claim_repository.get_by_id.return_value = claim
        claim_id = claim.id
        response = client.get(f"/api/v1/intelligence/quality/claim/{claim_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["entity_type"] == "claim"
        assert data["entity_id"] == str(claim_id)
        assert "flags" in data
        assert "overall_score" in data

    def test_get_relationship_quality(self, client: TestClient, mock_container: MagicMock) -> None:
        from ai_news_digest.domain.models.relationship import (
            ProvenanceSource,
            Relationship,
        )
        from ai_news_digest.domain.enums.entity_type import EntityType
        from ai_news_digest.domain.enums.relationship_type import RelationshipType
        from ai_news_digest.domain.enums.relationship_status import RelationshipStatus

        rel = Relationship.create(
            subject_entity_type=EntityType("company"),
            subject_entity_id=uuid4(),
            relationship_type=RelationshipType("partners_with"),
            object_entity_type=EntityType("company"),
            object_entity_id=uuid4(),
            status=RelationshipStatus.VERIFIED,
            confidence=0.9,
            provenance_source=ProvenanceSource.DETERMINISTIC,
        )
        mock_container.relationship_repository.get_by_id.return_value = rel
        response = client.get(f"/api/v1/intelligence/quality/relationship/{rel.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["entity_type"] == "relationship"

    def test_get_story_cluster_quality(self, client: TestClient, mock_container: MagicMock) -> None:
        cluster = _make_cluster()
        mock_container.story_cluster_repository.get_by_id.return_value = cluster
        mock_container.article_repository.list_by_cluster_id.return_value = []
        mock_container.conflict_repository.list_recent.return_value = []
        response = client.get(f"/api/v1/intelligence/quality/story_cluster/{cluster.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["entity_type"] == "story_cluster"

    def test_get_entity_not_found(self, client: TestClient, mock_container: MagicMock) -> None:
        mock_container.claim_repository.get_by_id.return_value = None
        response = client.get(f"/api/v1/intelligence/provenance/claim/{uuid4()}")
        assert response.status_code == 404

    def test_get_unsupported_entity_type(self, client: TestClient) -> None:
        response = client.get(f"/api/v1/intelligence/provenance/unknown/{uuid4()}")
        assert response.status_code == 400

    def test_get_invalid_entity_id(self, client: TestClient) -> None:
        response = client.get("/api/v1/intelligence/provenance/claim/not-a-uuid")
        assert response.status_code == 400


__all__ = ["TestIntelligenceQualityRoutes"]
