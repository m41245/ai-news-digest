from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ai_news_digest.application.ai.embedding_service import EmbeddingService
from ai_news_digest.application.ai.semantic_search_service import (
    SemanticSearchService,
)
from ai_news_digest.application.dto.story_cluster.semantic_match import (
    SemanticMatchResult,
)
from ai_news_digest.application.services.semantic_duplicate_detector import (
    SemanticDuplicateDetector,
)
from ai_news_digest.core.logging import get_logger
from ai_news_digest.domain.models.article import Article
from ai_news_digest.domain.models.story_cluster import StoryCluster

if TYPE_CHECKING:
    from ai_news_digest.application.services.semantic_candidate_finder import (
        SemanticCandidateFinder,
    )

logger = get_logger(__name__)


@dataclass(slots=True)
class RelatedStory:
    cluster_id: str
    title: str
    summary: str | None
    similarity: float
    article_count: int = 0
    source_count: int = 0
    reason: str = "Semantically related"


class RelatedStoryFinder:
    """Discover related story clusters for a given article.

    Uses semantic similarity when available, combined with duplicate
    detection and bounded candidate selection.
    """

    def __init__(
        self,
        embedding_service: EmbeddingService,
        semantic_search: SemanticSearchService,
        duplicate_detector: SemanticDuplicateDetector,
        candidate_finder: SemanticCandidateFinder,
    ) -> None:
        self._embedding_service = embedding_service
        self._semantic_search = semantic_search
        self._duplicate_detector = duplicate_detector
        self._candidate_finder = candidate_finder

    async def find_for_article(
        self,
        article: Article,
        existing_cluster_id: str | None,
        clusters: Sequence[StoryCluster],
        limit: int = 10,
    ) -> list[RelatedStory]:
        if not clusters:
            return []

        candidates = [
            c
            for c in clusters
            if str(c.id) != str(existing_cluster_id)
        ]
        if not candidates:
            return []

        match_results: dict[str, SemanticMatchResult] = {}
        for cluster in candidates:
            try:
                result = await self._duplicate_detector.compare_with_cluster(
                    article, cluster
                )
                match_results[str(cluster.id)] = result
            except Exception as exc:
                logger.warning(
                    "related_stories.duplicate_detector_failed",
                    cluster_id=str(cluster.id),
                    error=str(exc),
                )
                continue

        query_embedding: tuple[float, ...] | None = None
        if self._embedding_service.is_available:
            try:
                doc = SemanticSearchService._article_to_document(article)
                emb = await self._embedding_service.generate(doc)
                query_embedding = emb.embedding
            except Exception as exc:
                logger.warning(
                    "related_stories.query_embedding_failed",
                    error=str(exc),
                )

        scored = await self._semantic_search.search_clusters(
            query=article.title,
            clusters=candidates,
            query_embedding=query_embedding,
        )

        results: list[RelatedStory] = []
        for scored_cluster in scored:
            c = scored_cluster.cluster
            match = match_results.get(str(c.id))
            if match and getattr(match, "match_type", None) is not None:
                match_type_value = (
                    match.match_type.value
                    if hasattr(match.match_type, "value")
                    else str(match.match_type)
                )
                if match_type_value in (
                    "exact_duplicate",
                    "semantic_duplicate",
                ):
                    continue
            reason = "Semantically related to this story"
            if match and getattr(match, "signals", None):
                reason = f"Related ({', '.join(match.signals[:2])})"
            results.append(
                RelatedStory(
                    cluster_id=str(c.id),
                    title=c.title,
                    summary=c.summary,
                    similarity=scored_cluster.similarity,
                    article_count=scored_cluster.article_count,
                    source_count=scored_cluster.source_count,
                    reason=reason,
                )
            )
            if len(results) >= limit:
                break

        if not results and candidates:
            results = [
                RelatedStory(
                    cluster_id=str(c.id),
                    title=c.title,
                    summary=c.summary,
                    similarity=0.0,
                    article_count=getattr(c, "article_count", 0),
                    source_count=getattr(c, "source_count", 0),
                    reason="Related story",
                )
                for c in candidates[:limit]
            ]

        return results


__all__ = ["RelatedStory", "RelatedStoryFinder"]
