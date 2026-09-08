from __future__ import annotations

from dataclasses import dataclass, field


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
