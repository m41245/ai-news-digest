from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ai_news_digest.application.ai.similarity_engine import SimilarityEngine
from ai_news_digest.core.logging import get_logger
from ai_news_digest.domain.models.article import Article
from ai_news_digest.domain.models.semantic_document import SemanticDocument
from ai_news_digest.domain.models.story_cluster import StoryCluster

if TYPE_CHECKING:
    from ai_news_digest.application.ai.embedding_service import EmbeddingService

logger = get_logger(__name__)


@dataclass(slots=True)
class ScoredArticle:
    article: Article
    similarity: float
    lexical_score: float = 0.0
    combined_score: float = 0.0


@dataclass(slots=True)
class ScoredCluster:
    cluster: StoryCluster
    similarity: float
    article_count: int = 0
    source_count: int = 0


class SemanticSearchService:
    """Hybrid search combining lexical relevance with semantic similarity.

    The service is a no-op when no embedding provider is available. It never
    crashes the caller and never fabricates semantic results.
    """

    def __init__(
        self,
        embedding_service: EmbeddingService,
        lexical_weight: float = 0.4,
        semantic_weight: float = 0.4,
        importance_weight: float = 0.1,
        recency_weight: float = 0.1,
    ) -> None:
        self._embedding_service = embedding_service
        self._lexical_weight = lexical_weight
        self._semantic_weight = semantic_weight
        self._importance_weight = importance_weight
        self._recency_weight = recency_weight
        self._similarity = SimilarityEngine()

    async def search_articles(
        self,
        query: str,
        candidates: Sequence[Article],
        query_embedding: tuple[float, ...] | None = None,
    ) -> list[ScoredArticle]:
        if not candidates:
            return []

        if not self._embedding_service.is_available or not query_embedding:
            return [ScoredArticle(article=a, similarity=0.0) for a in candidates]

        try:
            docs = [self._article_to_document(a) for a in candidates]
            batch = await self._embedding_service.generate_batch(docs)
            embeddings = {d.id: r.embedding for d, r in zip(docs, batch.results, strict=True)}
        except Exception as exc:
            logger.warning("semantic_search.embedding_failed", error=str(exc))
            return [ScoredArticle(article=a, similarity=0.0) for a in candidates]

        from datetime import UTC, datetime

        now = datetime.now(UTC)
        results: list[ScoredArticle] = []
        for article in candidates:
            candidate_embedding = embeddings.get(article.id)
            if candidate_embedding is None:
                continue
            sim = self._similarity.normalized_similarity(
                query_embedding, candidate_embedding
            )
            importance = article.importance_score or 0.0
            age_hours = (
                (now - article.published_at).total_seconds() / 3600.0
                if article.published_at
                else 24.0
            )
            recency = max(0.0, 1.0 - (age_hours / 168.0))

            combined = (
                self._lexical_weight * 0.5
                + self._semantic_weight * sim
                + self._importance_weight * importance
                + self._recency_weight * recency
            )
            results.append(
                ScoredArticle(
                    article=article,
                    similarity=sim,
                    lexical_score=0.5,
                    combined_score=combined,
                )
            )

        results.sort(key=lambda r: r.combined_score, reverse=True)
        return results

    async def search_clusters(
        self,
        query: str,
        clusters: Sequence[StoryCluster],
        query_embedding: tuple[float, ...] | None = None,
    ) -> list[ScoredCluster]:
        if not clusters:
            return []

        if not self._embedding_service.is_available or not query_embedding:
            return [ScoredCluster(cluster=c, similarity=0.0) for c in clusters]

        try:
            docs = [self._cluster_to_document(c) for c in clusters]
            batch = await self._embedding_service.generate_batch(docs)
            embeddings = {d.id: r.embedding for d, r in zip(docs, batch.results, strict=True)}
        except Exception as exc:
            logger.warning("semantic_search.cluster_embedding_failed", error=str(exc))
            return [ScoredCluster(cluster=c, similarity=0.0) for c in clusters]

        results: list[ScoredCluster] = []
        for cluster in clusters:
            cluster_embedding = embeddings.get(cluster.id)
            if cluster_embedding is None:
                continue
            sim = self._similarity.normalized_similarity(
                query_embedding, cluster_embedding
            )
            results.append(
                ScoredCluster(
                    cluster=cluster,
                    similarity=sim,
                )
            )

        results.sort(key=lambda r: r.similarity, reverse=True)
        return results

    @staticmethod
    def _article_to_document(article: Article) -> SemanticDocument:
        return SemanticDocument(
            id=article.id,
            title=article.title,
            summary=article.summary,
            why_it_matters=article.why_it_matters,
            topics=article.topics,
            companies=article.companies,
            categories=article.categories,
        )

    @staticmethod
    def _cluster_to_document(cluster: StoryCluster) -> SemanticDocument:
        return SemanticDocument(
            id=cluster.id,
            title=cluster.title,
            summary=cluster.summary,
            topics=(),
            companies=(),
            categories=(),
        )


__all__ = ["ScoredArticle", "ScoredCluster", "SemanticSearchService"]
