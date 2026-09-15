from __future__ import annotations

from dataclasses import dataclass


class RecommendationWeights:
    """
    Score weights and thresholds for deterministic recommendation scoring.

    All scores are bounded to 0-100. Each signal contributes a fixed amount.
    """

    BASE_SCORE: float = 30.0

    FOLLOWED_COMPANY: float = 12.0
    FOLLOWED_TOPIC: float = 10.0
    FOLLOWED_CATEGORY: float = 8.0
    FOLLOWED_SOURCE: float = 6.0
    PREFERRED_SOURCE_TYPE: float = 4.0

    HIGH_IMPORTANCE: float = 10.0
    STRONG_CONFIDENCE: float = 6.0
    MULTIPLE_SOURCES: float = 4.0

    FRESH_COVERAGE: float = 6.0
    RECENTLY_UPDATED: float = 4.0

    BREAKING_STORY: float = 12.0
    DEVELOPING_STORY: float = 8.0
    ONGOING_STORY: float = 4.0
    STALE_PENALTY: float = -6.0

    TREND_STRONG_MOMENTUM: float = 8.0
    TREND_MOMENTUM: float = 4.0

    RECENT_EVENT: float = 4.0
    MULTIPLE_EVENTS: float = 2.0

    MAX_SCORE: float = 100.0
    MIN_SCORE: float = 0.0


class RecommendationDefaults:
    """
    Default values and bounds for recommendation retrieval.
    """

    DEFAULT_RECOMMENDATION_LIMIT: int = 20
    MAX_RECOMMENDATION_LIMIT: int = 100
    CANDIDATE_LIMIT: int = 200

    MAX_SAME_COMPANY: int = 2
    MAX_SAME_TOPIC: int = 2
    MAX_SAME_CATEGORY: int = 2
    MAX_SAME_SOURCE: int = 3
    DIVERSITY_PENALTY: float = -15.0

    RECENT_EVENT_HOURS: int = 48
    MAX_EVENTS_PER_CLUSTER: int = 5


@dataclass
class RecommendationSignal:
    """Individual signal contribution to a cluster's recommendation score."""

    name: str
    raw_value: float
    contribution: float
    explanation: str


@dataclass
class ScoredCluster:
    """A story cluster with its computed recommendation score and metadata."""

    cluster_id: str
    article_id: str
    score: float
    signals: list[RecommendationSignal]
    reasons: list[str]
    company_ids: set[str]
    topic_ids: set[str]
    category_ids: set[str]
    source_id: str | None = None


__all__ = [
    "RecommendationDefaults",
    "RecommendationSignal",
    "RecommendationWeights",
    "ScoredCluster",
]
