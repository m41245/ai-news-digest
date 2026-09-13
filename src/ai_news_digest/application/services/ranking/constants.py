from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ai_news_digest.domain.models.story_cluster import StoryCluster


class PreferenceValidation:
    """
    Validation bounds for user preference fields.
    """

    MIN_IMPORTANCE_MIN: float = 0.0
    MIN_IMPORTANCE_MAX: float = 1.0
    MIN_CONFIDENCE_MIN: float = 0.0
    MIN_CONFIDENCE_MAX: float = 1.0
    VALID_SORT_VALUES: tuple[str, ...] = ("published_at", "importance", "relevance")
    FRESHNESS_WINDOW_MIN: int = 1
    FRESHNESS_WINDOW_MAX: int = 365


class SourceTypePreferenceBehavior:
    """
    Behavior configuration for preferred source types.
    """

    VALID_TYPES: frozenset[str] = frozenset(
        {
            "official_company",
            "tech_publication",
            "business_news",
            "research_org",
            "other",
        }
    )

    @classmethod
    def normalize(cls, source_types: list[str]) -> list[str]:
        seen: set[str] = set()
        normalized: list[str] = []
        for source_type in source_types:
            if source_type in cls.VALID_TYPES and source_type not in seen:
                seen.add(source_type)
                normalized.append(source_type)
        return normalized


class FeedDefaults:
    """
    Default values for personalized feed pagination and sorting.
    """

    DEFAULT_PAGE_SIZE: int = 20
    DEFAULT_SORT: str = "published_at"
    MAX_PAGE_SIZE: int = 100
    CANDIDATE_LIMIT: int = 200


class RankingDefaults:
    """
    Default values and bounds for story cluster ranking.
    """

    MIN_SCORE: float = 0.0
    MAX_SCORE: float = 100.0
    DEFAULT_RANKING_LOOKBACK_HOURS: int = 24
    MAX_RANKING_CANDIDATES: int = 200
    MAX_UNIQUE_SOURCES_DIVERSITY: int = 10
    MAX_COMPANY_RELEVANCE: int = 3
    MAX_CATEGORY_TOPIC_RELEVANCE: int = 5
    RECENCY_DECAY_HOURS: float = 24.0


class SourceTrustDefaults:
    """
    Source trust scores by verification status.
    """

    VERIFIED: float = 1.0
    PENDING_REVIEW: float = 0.5
    REJECTED: float = 0.0
    INACTIVE: float = 0.0


class SourceTypeScoreDefaults:
    """
    Base trust multipliers by source type.
    """

    OFFICIAL_COMPANY: float = 1.0
    TECH_PUBLICATION: float = 0.9
    RESEARCH_ORG: float = 0.85
    BUSINESS_NEWS: float = 0.8
    OTHER: float = 0.6


class ExtractionQualityScoreDefaults:
    """
    Quality scores mapped to article extraction quality levels.
    """

    NONE: float = 0.0
    LOW: float = 0.3
    MEDIUM: float = 0.6
    HIGH: float = 0.8
    FULL: float = 1.0


class StoryRankingWeights:
    """
    Score weights and thresholds for deterministic story cluster ranking.
    All weights are relative; final score is normalized to 0-100.
    """

    RECENCY: float = 0.15
    SOURCE_TRUST: float = 0.20
    SOURCE_DIVERSITY: float = 0.10
    CORROBORATION: float = 0.15
    COMPANY_RELEVANCE: float = 0.15
    CATEGORY_TOPIC_RELEVANCE: float = 0.10
    ARTICLE_QUALITY: float = 0.10
    OFFICIAL_ANNOUNCEMENT: float = 0.05


class RankingWeights:
    """
    Score weights and thresholds for personalized feed ranking.
    """

    FOLLOWED_COMPANY: float = 0.5
    FOLLOWED_TOPIC: float = 0.3
    FOLLOWED_CATEGORY: float = 0.2
    HIGH_IMPORTANCE_THRESHOLD: float = 0.8
    HIGH_IMPORTANCE: float = 0.4
    MULTIPLE_SOURCES_MIN: int = 3
    MULTIPLE_SOURCES: float = 0.3
    RECENTLY_UPDATED_DAYS: int = 7
    RECENTLY_UPDATED: float = 0.2
    STRONG_CONFIDENCE_THRESHOLD: float = 0.9
    STRONG_CONFIDENCE: float = 0.3
    FRESH_COVERAGE_HOURS: int = 24
    FRESH_COVERAGE: float = 0.2
    PREFERRED_SOURCE_TYPE: float = 0.3


@dataclass
class RankingExplanation:
    """
    Structured explanation for why an article/cluster was included in the feed.
    """

    score: float = 0.0
    personalization: list[str] = field(default_factory=list)
    quality: list[str] = field(default_factory=list)
    freshness: list[str] = field(default_factory=list)
    fallback: list[str] = field(default_factory=list)

    def add_personalization(self, reason: str, weight: float = 0.0) -> None:
        self.personalization.append(reason)
        self.score += weight

    def add_quality(self, reason: str, weight: float = 0.0) -> None:
        self.quality.append(reason)
        self.score += weight

    def add_freshness(self, reason: str, weight: float = 0.0) -> None:
        self.freshness.append(reason)
        self.score += weight

    def add_fallback(self, reason: str) -> None:
        self.fallback.append(reason)

    @property
    def all_reasons(self) -> list[str]:
        return self.personalization + self.quality + self.freshness + self.fallback


@dataclass
class StoryRankingSignal:
    """Individual signal contribution to a cluster's ranking score."""

    name: str
    raw_value: float
    normalized_value: float
    weight: float
    contribution: float
    explanation: str


@dataclass
class StoryRankingResult:
    """Deterministic ranking result for a single StoryCluster."""

    cluster_id: str
    score: float
    signals: list[StoryRankingSignal]
    explanation: str


@dataclass
class RankedCluster:
    """A StoryCluster with its computed ranking."""

    cluster: StoryCluster
    score: float
    rank: int
    signals: list[StoryRankingSignal]
    explanation: str


@dataclass
class TopStoryResult:
    """Result of Top Story selection."""

    top_story_cluster_id: str | None
    top_story_score: float | None
    total_candidates: int
    eligible_candidates: int
    ranking_window_start: datetime
    ranking_window_end: datetime
    generated_at: datetime


__all__ = [
    "ExtractionQualityScoreDefaults",
    "FeedDefaults",
    "PreferenceValidation",
    "RankedCluster",
    "RankingDefaults",
    "RankingExplanation",
    "RankingWeights",
    "SourceTrustDefaults",
    "SourceTypePreferenceBehavior",
    "SourceTypeScoreDefaults",
    "StoryRankingResult",
    "StoryRankingSignal",
    "StoryRankingWeights",
    "TopStoryResult",
]
