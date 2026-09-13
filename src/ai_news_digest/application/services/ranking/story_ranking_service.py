"""
Story cluster ranking engine for M68.

Implements deterministic, explainable ranking of StoryClusters using
normalized signals combined with configurable weights.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from ai_news_digest.application.services.ranking.constants import (
    ExtractionQualityScoreDefaults,
    RankingDefaults,
    SourceTrustDefaults,
    SourceTypeScoreDefaults,
    StoryRankingResult,
    StoryRankingSignal,
    StoryRankingWeights,
)
from ai_news_digest.domain.enums.extraction_quality import ExtractionQuality
from ai_news_digest.domain.enums.source_status import SourceStatus
from ai_news_digest.domain.enums.source_type import SourceType
from ai_news_digest.domain.models.article import Article
from ai_news_digest.domain.models.source import Source
from ai_news_digest.domain.models.story_cluster import StoryCluster

if TYPE_CHECKING:
    pass


@dataclass
class ClusterRankingContext:
    """Pre-computed context for ranking a single StoryCluster."""

    cluster: StoryCluster
    articles: list[Article]
    source_map: dict[str, Source]
    known_company_ids: set[str]
    known_topic_ids: set[str]
    known_category_ids: set[str]
    now: datetime


class StoryRankingEngine:
    """
    Deterministic story cluster ranking engine.

    Ranking is purely metadata-driven and produces a bounded score in
    [RankingDefaults.MIN_SCORE, RankingDefaults.MAX_SCORE].
    """

    def __init__(
        self,
        recency_weight: float = StoryRankingWeights.RECENCY,
        source_trust_weight: float = StoryRankingWeights.SOURCE_TRUST,
        source_diversity_weight: float = StoryRankingWeights.SOURCE_DIVERSITY,
        corroboration_weight: float = StoryRankingWeights.CORROBORATION,
        company_relevance_weight: float = StoryRankingWeights.COMPANY_RELEVANCE,
        category_topic_relevance_weight: float = StoryRankingWeights.CATEGORY_TOPIC_RELEVANCE,
        article_quality_weight: float = StoryRankingWeights.ARTICLE_QUALITY,
        official_announcement_weight: float = StoryRankingWeights.OFFICIAL_ANNOUNCEMENT,
        recency_decay_hours: float = RankingDefaults.RECENCY_DECAY_HOURS,
        max_unique_sources_diversity: int = RankingDefaults.MAX_UNIQUE_SOURCES_DIVERSITY,
        max_company_relevance: int = RankingDefaults.MAX_COMPANY_RELEVANCE,
        max_category_topic_relevance: int = RankingDefaults.MAX_CATEGORY_TOPIC_RELEVANCE,
    ) -> None:
        weight_sum = (
            recency_weight
            + source_trust_weight
            + source_diversity_weight
            + corroboration_weight
            + company_relevance_weight
            + category_topic_relevance_weight
            + article_quality_weight
            + official_announcement_weight
        )
        if weight_sum <= 0:
            raise ValueError("Ranking weights must sum to a positive value.")

        self._recency_weight = recency_weight / weight_sum
        self._source_trust_weight = source_trust_weight / weight_sum
        self._source_diversity_weight = source_diversity_weight / weight_sum
        self._corroboration_weight = corroboration_weight / weight_sum
        self._company_relevance_weight = company_relevance_weight / weight_sum
        self._category_topic_relevance_weight = category_topic_relevance_weight / weight_sum
        self._article_quality_weight = article_quality_weight / weight_sum
        self._official_announcement_weight = official_announcement_weight / weight_sum

        self._recency_decay_hours = recency_decay_hours
        self._max_unique_sources_diversity = max(1, max_unique_sources_diversity)
        self._max_company_relevance = max(1, max_company_relevance)
        self._max_category_topic_relevance = max(1, max_category_topic_relevance)

    def rank_cluster(self, ctx: ClusterRankingContext) -> StoryRankingResult:
        """Compute a deterministic ranking result for a single StoryCluster."""
        signals = [
            self._recency_signal(ctx),
            self._source_trust_signal(ctx),
            self._source_diversity_signal(ctx),
            self._corroboration_signal(ctx),
            self._company_relevance_signal(ctx),
            self._category_topic_relevance_signal(ctx),
            self._article_quality_signal(ctx),
            self._official_announcement_signal(ctx),
        ]

        weighted_sum = sum(s.contribution for s in signals)
        final_score = self._clamp(
            weighted_sum * RankingDefaults.MAX_SCORE,
            RankingDefaults.MIN_SCORE,
            RankingDefaults.MAX_SCORE,
        )

        explanation_parts = [s.explanation for s in signals if s.explanation]
        explanation = "; ".join(explanation_parts) if explanation_parts else "No ranking signals."

        return StoryRankingResult(
            cluster_id=str(ctx.cluster.id),
            score=final_score,
            signals=signals,
            explanation=explanation,
        )

    def _clamp(self, value: float, min_value: float, max_value: float) -> float:
        return max(min_value, min(max_value, value))

    def _safe_age_hours(self, published_at: datetime, now: datetime) -> float:
        delta = now - published_at
        total_seconds = max(delta.total_seconds(), 0.0)
        return total_seconds / 3600.0

    def _recency_signal(self, ctx: ClusterRankingContext) -> StoryRankingSignal:
        weight = self._recency_weight
        age_hours = self._safe_age_hours(ctx.cluster.first_published_at, ctx.now)
        decay_hours = self._recency_decay_hours
        normalized = math.exp(-age_hours / decay_hours) if decay_hours > 0 else 1.0
        normalized = self._clamp(normalized, 0.0, 1.0)
        contribution = weight * normalized

        explanation = ""
        if age_hours < 1.0:
            explanation = "Very recent story"
        elif age_hours < 6.0:
            explanation = "Recent story"
        elif age_hours < 24.0:
            explanation = "Within 24 hours"
        else:
            explanation = f"Published {age_hours:.1f} hours ago"

        return StoryRankingSignal(
            name="recency",
            raw_value=age_hours,
            normalized_value=normalized,
            weight=weight,
            contribution=contribution,
            explanation=explanation,
        )

    def _source_trust_signal(self, ctx: ClusterRankingContext) -> StoryRankingSignal:
        weight = self._source_trust_weight
        if not ctx.articles:
            return StoryRankingSignal(
                name="source_trust",
                raw_value=0.0,
                normalized_value=0.0,
                weight=weight,
                contribution=0.0,
                explanation="No sources",
            )

        scores: list[float] = []
        for article in ctx.articles:
            source = ctx.source_map.get(str(article.source_id))
            if source is None:
                scores.append(0.0)
                continue
            status_score = SourceTrustDefaults.VERIFIED
            try:
                status_score = {
                    SourceStatus.VERIFIED: SourceTrustDefaults.VERIFIED,
                    SourceStatus.PENDING_REVIEW: SourceTrustDefaults.PENDING_REVIEW,
                    SourceStatus.REJECTED: SourceTrustDefaults.REJECTED,
                    SourceStatus.INACTIVE: SourceTrustDefaults.INACTIVE,
                }[source.status]
            except KeyError:
                status_score = 0.0

            type_score = SourceTypeScoreDefaults.OTHER
            try:
                type_score = {
                    SourceType.OFFICIAL_COMPANY: SourceTypeScoreDefaults.OFFICIAL_COMPANY,
                    SourceType.TECH_PUBLICATION: SourceTypeScoreDefaults.TECH_PUBLICATION,
                    SourceType.RESEARCH_ORG: SourceTypeScoreDefaults.RESEARCH_ORG,
                    SourceType.BUSINESS_NEWS: SourceTypeScoreDefaults.BUSINESS_NEWS,
                    SourceType.OTHER: SourceTypeScoreDefaults.OTHER,
                }[source.source_type]
            except KeyError:
                type_score = SourceTypeScoreDefaults.OTHER

            scores.append(status_score * type_score)

        avg_trust = sum(scores) / len(scores)
        normalized = self._clamp(avg_trust, 0.0, 1.0)
        contribution = weight * normalized

        explanation = f"Average source trust score: {avg_trust:.2f}"
        return StoryRankingSignal(
            name="source_trust",
            raw_value=avg_trust,
            normalized_value=normalized,
            weight=weight,
            contribution=contribution,
            explanation=explanation,
        )

    def _source_diversity_signal(self, ctx: ClusterRankingContext) -> StoryRankingSignal:
        weight = self._source_diversity_weight
        unique_source_ids = {a.source_id for a in ctx.articles if a.source_id}
        unique_count = len(unique_source_ids)
        max_diversity = self._max_unique_sources_diversity
        normalized = math.log(unique_count + 1) / math.log(max_diversity + 1)
        normalized = self._clamp(normalized, 0.0, 1.0)
        contribution = weight * normalized

        explanation = f"{unique_count} unique source(s)"
        return StoryRankingSignal(
            name="source_diversity",
            raw_value=float(unique_count),
            normalized_value=normalized,
            weight=weight,
            contribution=contribution,
            explanation=explanation,
        )

    def _corroboration_signal(self, ctx: ClusterRankingContext) -> StoryRankingSignal:
        weight = self._corroboration_weight
        unique_source_ids = {a.source_id for a in ctx.articles if a.source_id}
        unique_count = len(unique_source_ids)
        max_sources = 5.0
        normalized = min(unique_count / max_sources, 1.0)
        contribution = weight * normalized

        if unique_count >= 5:
            explanation = "Strong corroboration (5+ sources)"
        elif unique_count >= 3:
            explanation = "Good corroboration (3+ sources)"
        elif unique_count >= 2:
            explanation = "Multiple sources"
        else:
            explanation = "Single source"

        return StoryRankingSignal(
            name="corroboration",
            raw_value=float(unique_count),
            normalized_value=normalized,
            weight=weight,
            contribution=contribution,
            explanation=explanation,
        )

    def _company_relevance_signal(self, ctx: ClusterRankingContext) -> StoryRankingSignal:
        weight = self._company_relevance_weight
        article_company_ids = {cid for a in ctx.articles for cid in a.company_ids}
        unique_companies = len(article_company_ids & ctx.known_company_ids)
        max_companies = self._max_company_relevance
        normalized = min(unique_companies / max_companies, 1.0) if max_companies > 0 else 0.0
        contribution = weight * normalized

        explanation = f"{unique_companies} known company/companies mentioned"
        return StoryRankingSignal(
            name="company_relevance",
            raw_value=float(unique_companies),
            normalized_value=normalized,
            weight=weight,
            contribution=contribution,
            explanation=explanation,
        )

    def _category_topic_relevance_signal(
        self, ctx: ClusterRankingContext
    ) -> StoryRankingSignal:
        weight = self._category_topic_relevance_weight

        article_category_ids = {cid for a in ctx.articles for cid in a.category_ids}
        article_topic_ids = {tid for a in ctx.articles for tid in a.topic_ids}
        if ctx.cluster and ctx.cluster.representative_article_id:
            for article in ctx.articles:
                if article.id == ctx.cluster.representative_article_id and article.category_id:
                    article_category_ids.add(article.category_id)

        known_categories = len(article_category_ids & ctx.known_category_ids)
        known_topics = len(article_topic_ids & ctx.known_topic_ids)
        total_known = known_categories + known_topics
        max_total = self._max_category_topic_relevance
        normalized = min(total_known / max_total, 1.0) if max_total > 0 else 0.0
        contribution = weight * normalized

        explanation = f"{known_categories} category(ies), {known_topics} topic(s)"
        return StoryRankingSignal(
            name="category_topic_relevance",
            raw_value=float(total_known),
            normalized_value=normalized,
            weight=weight,
            contribution=contribution,
            explanation=explanation,
        )

    def _article_quality_signal(self, ctx: ClusterRankingContext) -> StoryRankingSignal:
        weight = self._article_quality_weight
        if not ctx.articles:
            return StoryRankingSignal(
                name="article_quality",
                raw_value=0.0,
                normalized_value=0.0,
                weight=weight,
                contribution=0.0,
                explanation="No articles",
            )

        quality_scores = {
            ExtractionQuality.NONE: ExtractionQualityScoreDefaults.NONE,
            ExtractionQuality.LOW: ExtractionQualityScoreDefaults.LOW,
            ExtractionQuality.MEDIUM: ExtractionQualityScoreDefaults.MEDIUM,
            ExtractionQuality.HIGH: ExtractionQualityScoreDefaults.HIGH,
            ExtractionQuality.FULL: ExtractionQualityScoreDefaults.FULL,
        }

        scores: list[float] = []
        for article in ctx.articles:
            scores.append(quality_scores.get(article.extraction_quality, 0.0))

        avg_quality = sum(scores) / len(scores)
        normalized = self._clamp(avg_quality, 0.0, 1.0)
        contribution = weight * normalized

        explanation = f"Average extraction quality: {avg_quality:.2f}"
        return StoryRankingSignal(
            name="article_quality",
            raw_value=avg_quality,
            normalized_value=normalized,
            weight=weight,
            contribution=contribution,
            explanation=explanation,
        )

    def _official_announcement_signal(
        self, ctx: ClusterRankingContext
    ) -> StoryRankingSignal:
        weight = self._official_announcement_weight
        has_official = False
        for article in ctx.articles:
            source = ctx.source_map.get(str(article.source_id))
            if source is not None and source.source_type == SourceType.OFFICIAL_COMPANY:
                has_official = True
                break

        normalized = 1.0 if has_official else 0.0
        contribution = weight * normalized

        explanation = (
            "Official company announcement" if has_official else "No official announcement"
        )
        return StoryRankingSignal(
            name="official_announcement",
            raw_value=1.0 if has_official else 0.0,
            normalized_value=normalized,
            weight=weight,
            contribution=contribution,
            explanation=explanation,
        )


__all__ = ["ClusterRankingContext", "StoryRankingEngine"]
