"""Bounded candidate selection for story clustering.

This module provides ``SemanticCandidateFinder`` which selects a bounded
set of candidate clusters and articles for similarity comparison. It is
designed to avoid O(n²) all-pairs comparisons while still surfacing
likely matches.

Candidate selection strategy:
1. Recent clusters/articles within the configured time window.
2. Shared category (when the article has one).
3. Shared company or topic entities.
4. Title token overlap pre-filter.
5. Hard limit on total candidates.
"""

from __future__ import annotations

import string
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from ai_news_digest.core.config import get_settings
from ai_news_digest.core.logging import get_logger
from ai_news_digest.domain.models.article import Article
from ai_news_digest.domain.models.story_cluster import StoryCluster

if TYPE_CHECKING:
    from ai_news_digest.domain.ports.article_repository import ArticleRepository
    from ai_news_digest.domain.ports.story_cluster_repository import StoryClusterRepository

logger = get_logger(__name__)


class SemanticCandidateFinder:
    """
    Select bounded candidate clusters and articles for similarity scoring.

    The finder queries the database using lightweight filters and returns
    domain ``StoryCluster`` and ``Article`` objects. The caller is
    responsible for converting these to the format required by the
    detector.
    """

    def __init__(
        self,
        article_repository: ArticleRepository,
        cluster_repository: StoryClusterRepository,
        *,
        time_window_hours: int | None = None,
        candidate_limit: int | None = None,
    ) -> None:
        self._article_repository = article_repository
        self._cluster_repository = cluster_repository
        settings = get_settings()
        self._time_window_hours = (
            time_window_hours
            if time_window_hours is not None
            else settings.story_time_window_hours
        )
        self._candidate_limit = (
            candidate_limit
            if candidate_limit is not None
            else settings.story_candidate_limit
        )

    async def find_candidates(
        self,
        article: Article,
    ) -> tuple[list[StoryCluster], list[Article]]:
        """
        Return candidate clusters and articles that might match the article.

        The search is bounded by ``story_time_window_hours`` and
        ``story_candidate_limit``. Returns a tuple of
        ``(candidate_clusters, candidate_articles)`` where standalone
        articles (those without a cluster) are returned as ``Article``
        instances.
        """
        cutoff = datetime.now(UTC) - timedelta(hours=self._time_window_hours)

        candidate_clusters = await self._find_cluster_candidates(article, cutoff)
        candidate_articles = await self._find_article_candidates(article, cutoff)

        total = len(candidate_clusters) + len(candidate_articles)
        if total > self._candidate_limit:
            logger.debug(
                "Candidate limit exceeded, truncating",
                article_id=str(article.id),
                total_candidates=total,
                limit=self._candidate_limit,
            )
            candidate_clusters = candidate_clusters[: self._candidate_limit // 2]
            candidate_articles = candidate_articles[: self._candidate_limit // 2]

        return candidate_clusters, candidate_articles

    async def _find_cluster_candidates(
        self,
        article: Article,
        cutoff: datetime,
    ) -> list[StoryCluster]:
        return await self._cluster_repository.find_recent_active_clusters(
            cutoff=cutoff,
            category_id=article.category_id,
            company_ids=list(article.company_ids or ()),
            topic_ids=list(article.topic_ids or ()),
            title_tokens=list(
                _normalize_title_tokens(article.title) if article.title else []
            ),
            limit=self._candidate_limit,
        )

    async def _find_article_candidates(
        self,
        article: Article,
        cutoff: datetime,
    ) -> list[Article]:
        return await self._article_repository.find_recent_candidate_articles(
            cutoff=cutoff,
            exclude_article_id=article.id,
            category_id=article.category_id,
            company_ids=list(article.company_ids or ()),
            topic_ids=list(article.topic_ids or ()),
            title_tokens=list(
                _normalize_title_tokens(article.title) if article.title else []
            ),
            limit=self._candidate_limit,
        )


def _normalize_title_tokens(title: str) -> list[str]:
    """Return deduplicated, lowercased tokens from a title, excluding stopwords."""
    cleaned = title.lower().strip()
    cleaned = cleaned.translate(str.maketrans("", "", "".join(string.punctuation)))
    tokens = cleaned.split()
    stopwords = frozenset(
        {
            "a",
            "an",
            "the",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "from",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "shall",
            "can",
            "it",
            "its",
            "this",
            "that",
            "these",
            "those",
            "i",
            "you",
            "he",
            "she",
            "we",
            "they",
            "what",
            "which",
            "who",
            "when",
            "where",
            "why",
            "how",
            "not",
            "no",
            "nor",
            "as",
            "up",
            "out",
            "about",
            "into",
            "over",
            "after",
            "new",
            "just",
            "more",
            "most",
            "some",
            "any",
            "all",
            "each",
            "every",
            "both",
            "few",
            "many",
            "much",
            "own",
            "same",
            "so",
            "than",
            "too",
            "very",
            "s",
            "t",
            "re",
            "ve",
            "ll",
            "d",
            "m",
        }
    )
    return sorted({t for t in tokens if t not in stopwords and len(t) > 2})


__all__ = ["SemanticCandidateFinder"]
