from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from ai_news_digest.application.ai.provider_manager import ProviderManager
from ai_news_digest.application.ai.structured_output import validate_structured_output
from ai_news_digest.core.config import get_settings
from ai_news_digest.domain.enums.entity_type import EntityType
from ai_news_digest.domain.enums.relationship_status import RelationshipStatus
from ai_news_digest.domain.enums.relationship_type import RelationshipType
from ai_news_digest.domain.models.relationship import (
    ProvenanceSource,
    Relationship,
)
from ai_news_digest.domain.ports.article_repository import ArticleRepository
from ai_news_digest.domain.ports.company_repository import CompanyRepository
from ai_news_digest.domain.ports.relationship_repository import RelationshipRepository
from ai_news_digest.domain.ports.story_cluster_repository import StoryClusterRepository
from ai_news_digest.domain.ports.topic_repository import TopicRepository

logger = logging.getLogger(__name__)


class KnowledgeGraphExtractionError(Exception):
    """Raised when relationship extraction fails."""


class RelationshipExtractionUseCase:
    """Extract knowledge graph relationships from articles and story clusters."""

    def __init__(
        self,
        relationship_repository: RelationshipRepository,
        article_repository: ArticleRepository,
        story_cluster_repository: StoryClusterRepository,
        company_repository: CompanyRepository,
        topic_repository: TopicRepository,
        provider_manager: ProviderManager | None = None,
    ) -> None:
        self._relationship_repository = relationship_repository
        self._article_repository = article_repository
        self._story_cluster_repository = story_cluster_repository
        self._company_repository = company_repository
        self._topic_repository = topic_repository
        self._provider_manager = provider_manager

    async def extract_for_article(self, article_id: UUID) -> list[Relationship]:
        """Extract relationships from a single article."""
        settings = get_settings()
        if not settings.knowledge_graph_enabled:
            return []

        article = await self._article_repository.get_by_id(article_id)
        if article is None:
            return []

        relationships: list[Relationship] = []

        if article.company_ids or article.topic_ids:
            deterministic = self._build_deterministic_article_relationships(article)
            relationships.extend(deterministic)

        ai_relationships = await self._extract_ai_relationships_for_article(article)
        relationships.extend(ai_relationships)

        deduped = self._deduplicate_relationships(relationships)
        bounded = deduped[: settings.knowledge_graph_max_relationships_per_article]

        if bounded:
            await self._relationship_repository.bulk_create(bounded)

        return bounded

    async def extract_for_story_cluster(self, cluster_id: UUID) -> list[Relationship]:
        """Extract relationships for a story cluster from its articles."""
        settings = get_settings()
        if not settings.knowledge_graph_enabled:
            return []

        cluster = await self._story_cluster_repository.get_by_id(cluster_id)
        if cluster is None:
            return []

        articles = await self._article_repository.list_by_cluster_id(
            cluster_id=cluster_id,
            limit=settings.knowledge_graph_max_relationships_per_story * 2,
        )

        relationships: list[Relationship] = []
        for article in articles:
            article_rels = await self.extract_for_article(article.id)
            relationships.extend(article_rels)

        cluster_rels = self._build_story_cluster_relationships(cluster, articles)
        relationships.extend(cluster_rels)

        deduped = self._deduplicate_relationships(relationships)
        bounded = deduped[: settings.knowledge_graph_max_relationships_per_story]

        if bounded:
            await self._relationship_repository.bulk_create(bounded)

        return bounded

    async def _extract_ai_relationships_for_article(
        self, article: Any
    ) -> list[Relationship]:
        if self._provider_manager is None:
            return []

        settings = get_settings()
        if not settings.ai_enabled:
            return []

        if not article.content and not article.summary:
            return []

        prompt = (
            "Extract up to 3 knowledge graph relationships from the following article. "
            "Return JSON with a 'relationships' array. Each item has: "
            "subject (company/topic name), relationship_type (one of: "
            "related_to, competes_with, partners_with, collaborates_with, "
            "uses_technology, provides_technology_to, announced, mentioned_with, "
            "acquired, acquired_by, invests_in), object (company/topic name), "
            "confidence (0.0-1.0). "
            "Only extract relationships explicitly supported by the text. "
            "Article:\n"
            f"Title: {article.title}\n"
            f"Summary: {article.summary or ''}\n"
            f"Content: {(article.content or '')[:settings.ai_max_content_length]}"
        )

        from ai_news_digest.application.ai.models import AIRequest

        request = AIRequest(
            system_prompt="You are a knowledge graph extraction assistant.",
            user_prompt=prompt,
            max_tokens=512,
            temperature=0.1,
        )

        try:
            response = await self._provider_manager.generate(
                request, capability="analysis"
            )
        except Exception as exc:
            logger.warning("AI relationship extraction failed: %s", str(exc))
            return []

        try:
            import json

            parsed = validate_structured_output(
                json.loads(response.content) if response.content else {}
            )
        except Exception as exc:
            logger.warning("Invalid AI relationship output: %s", str(exc))
            return []

        raw_rels: list[Any] = []
        for attr in ("relationships", "companies", "topics"):
            candidate = getattr(parsed, attr, None)
            if isinstance(candidate, list) and candidate:
                raw_rels = candidate
                break

        if not raw_rels:
            return []

        known_companies = {
            c.name: c.id for c in await self._company_repository.list_all()
        }
        known_topics = {t.name: t.id for t in await self._topic_repository.list_all()}

        relationships: list[Relationship] = []
        for item in raw_rels[: settings.knowledge_graph_max_relationships_per_article]:
            subject_name = getattr(item, "subject", "")
            object_name = getattr(item, "object", "")
            rel_type = getattr(item, "relationship_type", "related_to")
            confidence = getattr(item, "confidence", None)

            subject_id, subject_type = self._resolve_entity(
                subject_name, known_companies, known_topics
            )
            object_id, object_type = self._resolve_entity(
                object_name, known_companies, known_topics
            )

            if (
                subject_id is None
                or object_id is None
                or subject_type is None
                or object_type is None
            ):
                continue

            canonical = await self._relationship_repository.get_canonical(
                subject_entity_type=subject_type,
                subject_entity_id=subject_id,
                relationship_type=rel_type,
                object_entity_type=object_type,
                object_entity_id=object_id,
            )
            if canonical is not None:
                continue

            relationships.append(
                Relationship.create(
                    subject_entity_type=subject_type,
                    subject_entity_id=subject_id,
                    relationship_type=RelationshipType(rel_type),
                    object_entity_type=object_type,
                    object_entity_id=object_id,
                    status=RelationshipStatus.CANDIDATE,
                    confidence=confidence,
                    provenance_source=ProvenanceSource.AI_EXTRACTED,
                    article_id=article.id,
                    ai_provider=response.provider,
                    ai_model=response.model,
                )
            )

        return relationships

    def _resolve_entity(
        self,
        name: str,
        known_companies: dict[str, UUID],
        known_topics: dict[str, UUID],
    ) -> tuple[UUID | None, EntityType | None]:
        cleaned = (name or "").strip()
        if not cleaned:
            return None, None

        if cleaned in known_companies:
            return known_companies[cleaned], EntityType.COMPANY
        if cleaned in known_topics:
            return known_topics[cleaned], EntityType.TOPIC

        return None, None

    def _build_deterministic_article_relationships(
        self, article: Any
    ) -> list[Relationship]:
        relationships: list[Relationship] = []
        for company_id in article.company_ids or []:
            for topic_id in article.topic_ids or []:
                relationships.append(
                    Relationship.create(
                        subject_entity_type=EntityType.COMPANY,
                        subject_entity_id=company_id,
                        relationship_type=RelationshipType.MENTIONED_WITH,
                        object_entity_type=EntityType.TOPIC,
                        object_entity_id=topic_id,
                        status=RelationshipStatus.CANDIDATE,
                        provenance_source=ProvenanceSource.DETERMINISTIC,
                        article_id=article.id,
                    )
                )
        return relationships

    def _build_story_cluster_relationships(
        self, cluster: Any, articles: list[Any]
    ) -> list[Relationship]:
        relationships: list[Relationship] = []
        company_ids: set[UUID] = set()
        topic_ids: set[UUID] = set()
        for article in articles:
            company_ids.update(article.company_ids or [])
            topic_ids.update(article.topic_ids or [])

        for company_id in company_ids:
            relationships.append(
                Relationship.create(
                    subject_entity_type=EntityType.STORY,
                    subject_entity_id=cluster.id,
                    relationship_type=RelationshipType.MENTIONED_WITH,
                    object_entity_type=EntityType.COMPANY,
                    object_entity_id=company_id,
                    status=RelationshipStatus.CANDIDATE,
                    provenance_source=ProvenanceSource.DETERMINISTIC,
                    story_cluster_id=cluster.id,
                )
            )
        for topic_id in topic_ids:
            relationships.append(
                Relationship.create(
                    subject_entity_type=EntityType.STORY,
                    subject_entity_id=cluster.id,
                    relationship_type=RelationshipType.MENTIONED_WITH,
                    object_entity_type=EntityType.TOPIC,
                    object_entity_id=topic_id,
                    status=RelationshipStatus.CANDIDATE,
                    provenance_source=ProvenanceSource.DETERMINISTIC,
                    story_cluster_id=cluster.id,
                )
            )
        return relationships

    def _deduplicate_relationships(
        self, relationships: list[Relationship]
    ) -> list[Relationship]:
        seen: dict[tuple[Any, Any, Any, Any, Any], Relationship] = {}
        for rel in relationships:
            key = (
                rel.subject_entity_type,
                rel.subject_entity_id,
                rel.relationship_type,
                rel.object_entity_type,
                rel.object_entity_id,
            )
            if key not in seen:
                seen[key] = rel
        return list(seen.values())


__all__ = ["KnowledgeGraphExtractionError", "RelationshipExtractionUseCase"]
