"""Semantic duplicate detection for article clustering.

This module provides a deterministic, configurable similarity detector
that classifies the relationship between a new article and an existing
story cluster or candidate article.

The implementation uses a layered lexical strategy:

Layer 1 - Exact URL deduplication:
    Handled upstream during ingestion via ``CanonicalUrl``. This detector
    does not re-check URLs.

Layer 2 - Lexical/normalized similarity signals:
    * Normalized title token overlap (Jaccard)
    * Shared company entities
    * Shared topics
    * Shared categories
    * Publication time proximity
    * Source domain overlap

Layer 3 - Configurable thresholds:
    All cutoffs are explicit settings so they can be tuned without code
    changes. The defaults are intentionally conservative: false positives
    (merging unrelated stories) are worse than false negatives (leaving
    duplicate stories separate).

The detector does NOT call any LLM provider. If true embedding-based
semantic search is added later, it should be injected as an optional
Layer 3 implementation behind the same ``SemanticDuplicateDetector``
interface.
"""

from __future__ import annotations

import string
from datetime import timedelta
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from ai_news_digest.application.dto.story_cluster.semantic_match import (
    SemanticMatchResult,
)
from ai_news_digest.core.config import get_settings
from ai_news_digest.core.logging import get_logger
from ai_news_digest.domain.enums.semantic_match_type import SemanticMatchType

if TYPE_CHECKING:
    from ai_news_digest.domain.models.article import Article
    from ai_news_digest.domain.models.story_cluster import StoryCluster
    from ai_news_digest.domain.ports.article_repository import ArticleRepository

logger = get_logger(__name__)


def _normalize_title_tokens(title: str) -> tuple[str, ...]:
    """Return deduplicated, lowercased tokens from a title."""
    cleaned = title.lower().strip()
    cleaned = cleaned.translate(str.maketrans("", "", string.punctuation))
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
    return tuple(sorted({t for t in tokens if t not in stopwords and len(t) > 2}))


def _jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    intersection = len(a & b)
    union = len(a | b)
    return intersection / union if union > 0 else 0.0


def _canonical_domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower()
    except Exception:
        return ""


class SemanticDuplicateDetector:
    """
    Deterministic semantic duplicate detector for article clustering.

    The detector compares a new article against candidate clusters or
    articles and returns a ``SemanticMatchResult`` classifying the
    relationship. It does not perform any external HTTP requests or LLM
    calls.

    Usage::

        detector = SemanticDuplicateDetector()
        result = await detector.compare_with_cluster(article, cluster)
        if result.should_cluster():
            ...
    """

    def __init__(
        self,
        *,
        semantic_duplicate_threshold: float | None = None,
        related_story_threshold: float | None = None,
        story_time_window_hours: int | None = None,
    ) -> None:
        settings = get_settings()
        self._semantic_duplicate_threshold = (
            semantic_duplicate_threshold
            if semantic_duplicate_threshold is not None
            else settings.story_semantic_duplicate_threshold
        )
        self._related_story_threshold = (
            related_story_threshold
            if related_story_threshold is not None
            else settings.story_related_story_threshold
        )
        self._story_time_window_hours = (
            story_time_window_hours
            if story_time_window_hours is not None
            else settings.story_time_window_hours
        )
        self._time_window = timedelta(hours=self._story_time_window_hours)

    async def compare_with_cluster(
        self,
        article: Article,
        cluster: StoryCluster,
        article_repository: ArticleRepository | None = None,
    ) -> SemanticMatchResult:
        """
        Compare an article against a story cluster and return the match result.

        If ``article_repository`` is provided and the cluster has a
        representative article, the representative's entity metadata is
        loaded to improve scoring accuracy.
        """
        score, signals = await self._compute_similarity(article, cluster, article_repository)
        match_type = self._classify(score)

        return SemanticMatchResult(
            match_type=match_type,
            score=score,
            candidate_id=cluster.id,
            candidate_title=cluster.title,
            signals=signals,
        )

    async def compare_with_article(
        self,
        article: Article,
        candidate: Article,
    ) -> SemanticMatchResult:
        """
        Compare an article against a candidate article and return the match result.
        """
        score, signals = self._compute_similarity_article(article, candidate)
        match_type = self._classify(score)

        return SemanticMatchResult(
            match_type=match_type,
            score=score,
            candidate_id=candidate.id,
            candidate_title=candidate.title,
            signals=signals,
        )

    def _classify(self, score: float) -> SemanticMatchType:
        if score >= self._semantic_duplicate_threshold:
            return SemanticMatchType.SEMANTIC_DUPLICATE
        if score >= self._related_story_threshold:
            return SemanticMatchType.RELATED_BUT_DISTINCT
        return SemanticMatchType.NEW_STORY

    async def _compute_similarity(
        self,
        article: Article,
        cluster: StoryCluster,
        article_repository: ArticleRepository | None = None,
    ) -> tuple[float, tuple[str, ...]]:
        signals: list[str] = []
        score = 0.0

        article_tokens = frozenset(
            _normalize_title_tokens(article.title) if article.title else []
        )
        cluster_tokens = frozenset(
            _normalize_title_tokens(cluster.title) if cluster.title else []
        )
        jaccard = _jaccard(article_tokens, cluster_tokens)

        if jaccard >= 0.7:
            score += 0.45
            signals.append(f"high_title_jaccard:{jaccard:.2f}")
        elif jaccard >= 0.4:
            score += 0.2
            signals.append(f"medium_title_jaccard:{jaccard:.2f}")
        elif jaccard >= 0.2:
            score += 0.05
            signals.append(f"low_title_jaccard:{jaccard:.2f}")

        cluster_companies: set[str] = set()
        cluster_topics: set[str] = set()
        cluster_categories: set[str] = set()
        cluster_domain = ""

        if (
            cluster.representative_article_id is not None
            and article_repository is not None
        ):
            try:
                representative = await article_repository.get_by_id(
                    cluster.representative_article_id
                )
            except Exception:
                representative = None

            if representative is not None:
                cluster_companies = {c.lower().strip() for c in representative.companies}
                cluster_topics = {t.lower().strip() for t in representative.topics}
                cluster_categories = {c.lower().strip() for c in representative.categories}
                cluster_domain = _canonical_domain(representative.url)

        article_companies = {c.lower().strip() for c in article.companies}
        article_topics = {t.lower().strip() for t in article.topics}
        article_categories = {c.lower().strip() for c in article.categories}

        shared_companies = len(article_companies & cluster_companies)
        shared_topics = len(article_topics & cluster_topics)
        shared_categories = len(article_categories & cluster_categories)

        if shared_companies >= 2:
            score += 0.2
            signals.append(f"shared_companies:{shared_companies}")
        elif shared_companies == 1:
            score += 0.1
            signals.append("shared_company:1")

        if shared_topics >= 2:
            score += 0.15
            signals.append(f"shared_topics:{shared_topics}")
        elif shared_topics == 1:
            score += 0.05
            signals.append("shared_topic:1")

        if shared_categories >= 1 and shared_companies == 0:
            score += 0.05
            signals.append(f"shared_category:{shared_categories}")

        time_diff = None
        if article.published_at and cluster.first_published_at:
            time_diff = abs((article.published_at - cluster.first_published_at).total_seconds())
        if time_diff is not None:
            if time_diff <= 24 * 3600:
                score += 0.2
                signals.append("within_24h")
            elif time_diff <= self._time_window.total_seconds():
                score += 0.1
                signals.append("within_window")
            elif time_diff <= 7 * 24 * 3600:
                score += 0.05
                signals.append("within_7d")
            else:
                signals.append("outside_time_window")

        article_domain = _canonical_domain(article.url) if article.url else ""
        if article_domain and cluster_domain and article_domain == cluster_domain:
            score += 0.05
            signals.append("same_domain")

        return min(score, 1.0), tuple(signals)

    def _compute_similarity_article(
        self,
        article: Article,
        candidate: Article,
    ) -> tuple[float, tuple[str, ...]]:
        signals: list[str] = []
        score = 0.0

        article_tokens = frozenset(
            _normalize_title_tokens(article.title) if article.title else []
        )
        candidate_tokens = frozenset(
            _normalize_title_tokens(candidate.title) if candidate.title else []
        )
        jaccard = _jaccard(article_tokens, candidate_tokens)

        if jaccard >= 0.7:
            score += 0.45
            signals.append(f"high_title_jaccard:{jaccard:.2f}")
        elif jaccard >= 0.4:
            score += 0.2
            signals.append(f"medium_title_jaccard:{jaccard:.2f}")
        elif jaccard >= 0.2:
            score += 0.05
            signals.append(f"low_title_jaccard:{jaccard:.2f}")

        article_companies = {c.lower().strip() for c in article.companies}
        article_topics = {t.lower().strip() for t in article.topics}
        article_categories = {c.lower().strip() for c in article.categories}

        candidate_companies = {c.lower().strip() for c in candidate.companies}
        candidate_topics = {t.lower().strip() for t in candidate.topics}
        candidate_categories = {c.lower().strip() for c in candidate.categories}

        shared_companies = len(article_companies & candidate_companies)
        shared_topics = len(article_topics & candidate_topics)
        shared_categories = len(article_categories & candidate_categories)

        if shared_companies >= 2:
            score += 0.2
            signals.append(f"shared_companies:{shared_companies}")
        elif shared_companies == 1:
            score += 0.1
            signals.append("shared_company:1")

        if shared_topics >= 2:
            score += 0.15
            signals.append(f"shared_topics:{shared_topics}")
        elif shared_topics == 1:
            score += 0.05
            signals.append("shared_topic:1")

        if shared_categories >= 1 and shared_companies == 0:
            score += 0.05
            signals.append(f"shared_category:{shared_categories}")

        time_diff = None
        if article.published_at and candidate.published_at:
            time_diff = abs((article.published_at - candidate.published_at).total_seconds())
        if time_diff is not None:
            if time_diff <= 24 * 3600:
                score += 0.2
                signals.append("within_24h")
            elif time_diff <= self._time_window.total_seconds():
                score += 0.1
                signals.append("within_window")
            elif time_diff <= 7 * 24 * 3600:
                score += 0.05
                signals.append("within_7d")
            else:
                signals.append("outside_time_window")

        article_domain = _canonical_domain(article.url) if article.url else ""
        candidate_domain = _canonical_domain(candidate.url) if candidate.url else ""
        if article_domain and candidate_domain and article_domain == candidate_domain:
            score += 0.05
            signals.append("same_domain")

        return min(score, 1.0), tuple(signals)


__all__ = ["SemanticDuplicateDetector"]
