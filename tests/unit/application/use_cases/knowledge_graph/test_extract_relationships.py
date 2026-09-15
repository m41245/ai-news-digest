"""
Unit tests for M89 relationship extraction use case.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from ai_news_digest.domain.enums.entity_type import EntityType
from ai_news_digest.domain.enums.relationship_type import RelationshipType
from ai_news_digest.domain.models.article import Article
from ai_news_digest.domain.models.relationship import (
    ProvenanceSource,
    Relationship,
)
from ai_news_digest.domain.models.story_cluster import StoryCluster


class FakeCompanyRepository:
    def __init__(self, companies: list) -> None:
        self._companies = {c.id: c for c in companies}

    async def list_all(self) -> list:
        return list(self._companies.values())

    async def list_by_ids(self, ids: list[str]) -> list:
        return [self._companies[UUID(i)] for i in ids if UUID(i) in self._companies]


class FakeTopicRepository:
    def __init__(self, topics: list) -> None:
        self._topics = {t.id: t for t in topics}

    async def list_all(self) -> list:
        return list(self._topics.values())

    async def list_by_ids(self, ids: list[str]) -> list:
        return [self._topics[UUID(i)] for i in ids if UUID(i) in self._topics]


class FakeArticleRepository:
    def __init__(self, articles: list) -> None:
        self._articles = {a.id: a for a in articles}

    async def get_by_id(self, article_id):
        return self._articles.get(article_id)

    async def list_by_cluster_id(self, cluster_id, limit=50):
        return [a for a in self._articles.values() if a.cluster_id == cluster_id][:limit]


class FakeStoryClusterRepository:
    def __init__(self, clusters: list) -> None:
        self._clusters = {c.id: c for c in clusters}

    async def get_by_id(self, cluster_id):
        return self._clusters.get(cluster_id)


class FakeRelationshipRepository:
    def __init__(self) -> None:
        self._relationships: list[Relationship] = []

    async def list_for_entity(self, entity_type, entity_id, status=None, limit=50, offset=0):
        return [
            r for r in self._relationships
            if r.subject_entity_type.value == entity_type and r.subject_entity_id == entity_id
        ][offset:offset + limit]

    async def bulk_create(self, relationships: list[Relationship]) -> list[Relationship]:
        self._relationships.extend(relationships)
        return relationships

    async def get_canonical(self, **kwargs):
        for r in self._relationships:
            if (
                r.subject_entity_type.value == kwargs["subject_entity_type"]
                and r.subject_entity_id == kwargs["subject_entity_id"]
                and r.relationship_type.value == kwargs["relationship_type"]
                and r.object_entity_type.value == kwargs["object_entity_type"]
                and r.object_entity_id == kwargs["object_entity_id"]
            ):
                return r
        return None


def _make_article(article_id, company_ids=(), topic_ids=(), cluster_id=None):
    return Article(
        id=article_id,
        title="Test Article",
        url="https://example.com",
        summary="Summary",
        content="Content",
        source_id=uuid4(),
        category_id=None,
        published_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        fetched_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        status=__import__("ai_news_digest.domain.enums.article_status", fromlist=["ArticleStatus"]).ArticleStatus.READY,  # noqa: E501
        company_ids=company_ids,
        topic_ids=topic_ids,
        cluster_id=cluster_id,
    )


def _make_cluster(cluster_id):
    return StoryCluster(
        id=cluster_id,
        title="Test Cluster",
        slug="test-cluster",
    )


class TestRelationshipExtractionUseCase:
    @pytest.mark.asyncio
    async def test_deterministic_article_relationships(self, monkeypatch):
        from ai_news_digest.application.use_cases.knowledge_graph.extract_relationships import (
            RelationshipExtractionUseCase,
        )

        company_id = uuid4()
        topic_id = uuid4()
        article = _make_article(
            article_id=uuid4(),
            company_ids=(company_id,),
            topic_ids=(topic_id,),
        )

        rel_repo = FakeRelationshipRepository()
        article_repo = FakeArticleRepository([article])
        cluster_repo = FakeStoryClusterRepository([])
        company_repo = FakeCompanyRepository([])
        topic_repo = FakeTopicRepository([])

        use_case = RelationshipExtractionUseCase(
            relationship_repository=rel_repo,
            article_repository=article_repo,
            story_cluster_repository=cluster_repo,
            company_repository=company_repo,
            topic_repository=topic_repo,
            provider_manager=None,
        )

        monkeypatch.setattr(
            "ai_news_digest.application.use_cases.knowledge_graph.extract_relationships.get_settings",
            lambda: type("Settings", (), {"knowledge_graph_enabled": True, "knowledge_graph_max_relationships_per_article": 10})(),  # noqa: E501
        )

        result = await use_case.extract_for_article(article.id)
        assert len(result) == 1
        assert result[0].subject_entity_type == EntityType.COMPANY
        assert result[0].object_entity_type == EntityType.TOPIC
        assert result[0].relationship_type == RelationshipType.MENTIONED_WITH
        assert result[0].provenance_source == ProvenanceSource.DETERMINISTIC

    @pytest.mark.asyncio
    async def test_disabled_when_flag_off(self, monkeypatch):
        from ai_news_digest.application.use_cases.knowledge_graph.extract_relationships import (
            RelationshipExtractionUseCase,
        )

        article = _make_article(article_id=uuid4())
        rel_repo = FakeRelationshipRepository()
        article_repo = FakeArticleRepository([article])
        cluster_repo = FakeStoryClusterRepository([])
        company_repo = FakeCompanyRepository([])
        topic_repo = FakeTopicRepository([])

        use_case = RelationshipExtractionUseCase(
            relationship_repository=rel_repo,
            article_repository=article_repo,
            story_cluster_repository=cluster_repo,
            company_repository=company_repo,
            topic_repository=topic_repo,
        )

        monkeypatch.setattr(
            "ai_news_digest.application.use_cases.knowledge_graph.extract_relationships.get_settings",
            lambda: type("Settings", (), {"knowledge_graph_enabled": False})(),
        )

        result = await use_case.extract_for_article(article.id)
        assert result == []

    @pytest.mark.asyncio
    async def test_deduplication(self, monkeypatch):
        from ai_news_digest.application.use_cases.knowledge_graph.extract_relationships import (
            RelationshipExtractionUseCase,
        )

        company_id = uuid4()
        topic_id = uuid4()
        article = _make_article(
            article_id=uuid4(),
            company_ids=(company_id,),
            topic_ids=(topic_id,),
        )

        rel_repo = FakeRelationshipRepository()
        article_repo = FakeArticleRepository([article])
        cluster_repo = FakeStoryClusterRepository([])
        company_repo = FakeCompanyRepository([])
        topic_repo = FakeTopicRepository([])

        use_case = RelationshipExtractionUseCase(
            relationship_repository=rel_repo,
            article_repository=article_repo,
            story_cluster_repository=cluster_repo,
            company_repository=company_repo,
            topic_repository=topic_repo,
        )

        monkeypatch.setattr(
            "ai_news_digest.application.use_cases.knowledge_graph.extract_relationships.get_settings",
            lambda: type("Settings", (), {"knowledge_graph_enabled": True, "knowledge_graph_max_relationships_per_article": 10})(),  # noqa: E501
        )

        result1 = await use_case.extract_for_article(article.id)
        result2 = await use_case.extract_for_article(article.id)
        assert len(result1) == 1
        assert len(result2) == 1


__all__ = ["TestRelationshipExtractionUseCase"]
