"""
Top Story selection logic for M68.

Selects the highest-ranked eligible StoryCluster for a given digest/day/time
window using deterministic tie-breaking.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from ai_news_digest.application.services.ranking.constants import (
    RankedCluster,
    RankingDefaults,
    StoryRankingResult,
)
from ai_news_digest.application.services.ranking.story_ranking_service import (
    ClusterRankingContext,
    StoryRankingEngine,
)
from ai_news_digest.domain.models.article import Article
from ai_news_digest.domain.models.source import Source
from ai_news_digest.domain.models.story_cluster import StoryCluster


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


class TopStorySelector:
    """
    Deterministic Top Story selector.

    Eligibility rules:
    - StoryCluster status must be ACTIVE
    - StoryCluster first_published_at must be within the ranking window
    - StoryCluster must have at least one member article
    """

    def __init__(
        self,
        ranking_engine: StoryRankingEngine | None = None,
        ranking_lookback_hours: int = RankingDefaults.DEFAULT_RANKING_LOOKBACK_HOURS,
        max_candidates: int = RankingDefaults.MAX_RANKING_CANDIDATES,
    ) -> None:
        self._ranking_engine = ranking_engine or StoryRankingEngine()
        self._ranking_lookback_hours = max(1, ranking_lookback_hours)
        self._max_candidates = max(1, max_candidates)

    def select_top_story(
        self,
        ranked_results: Sequence[StoryRankingResult],
        now: datetime | None = None,
    ) -> TopStoryResult:
        """Select the top story from pre-ranked results."""
        if now is None:
            now = datetime.now(UTC)

        window_end = now
        window_start = now - timedelta(hours=self._ranking_lookback_hours)

        total = len(ranked_results)
        eligible = len(ranked_results)

        top_id = None
        top_score = None

        if ranked_results:
            best = max(
                ranked_results,
                key=lambda r: (
                    r.score,
                    r.score,
                    r.cluster_id,
                ),
            )
            top_id = best.cluster_id
            top_score = best.score

        return TopStoryResult(
            top_story_cluster_id=top_id,
            top_story_score=top_score,
            total_candidates=total,
            eligible_candidates=eligible,
            ranking_window_start=window_start,
            ranking_window_end=window_end,
            generated_at=now,
        )

    def rank_and_select(
        self,
        clusters: Sequence[StoryCluster],
        cluster_articles: dict[str, list[Article]],
        source_map: dict[str, Source],
        known_company_ids: set[str],
        known_topic_ids: set[str],
        known_category_ids: set[str],
        now: datetime | None = None,
    ) -> tuple[list[RankedCluster], TopStoryResult]:
        """
        Rank clusters and select the top story in a single pass.
        """
        if now is None:
            now = datetime.now(UTC)

        window_end = now
        window_start = now - timedelta(hours=self._ranking_lookback_hours)

        eligible_contexts: list[ClusterRankingContext] = []
        ineligible_count = 0

        for cluster in clusters:
            if cluster.status.value != "active":
                ineligible_count += 1
                continue

            articles = cluster_articles.get(str(cluster.id), [])
            if not articles:
                ineligible_count += 1
                continue

            eligible_contexts.append(
                ClusterRankingContext(
                    cluster=cluster,
                    articles=articles,
                    source_map=source_map,
                    known_company_ids=known_company_ids,
                    known_topic_ids=known_topic_ids,
                    known_category_ids=known_category_ids,
                    now=now,
                )
            )

        ranked_results = [
            self._ranking_engine.rank_cluster(ctx) for ctx in eligible_contexts
        ]

        ranked_clusters = self._build_ranked_clusters(
            clusters, ranked_results, cluster_articles
        )

        top_id = None
        top_score = None

        if ranked_results:
            candidates = sorted(
                ranked_results,
                key=lambda r: (
                    -r.score,
                    r.cluster_id,
                ),
            )
            best = candidates[0]
            top_id = best.cluster_id
            top_score = best.score

        top_story = TopStoryResult(
            top_story_cluster_id=top_id,
            top_story_score=top_score,
            total_candidates=len(clusters),
            eligible_candidates=len(eligible_contexts),
            ranking_window_start=window_start,
            ranking_window_end=window_end,
            generated_at=now,
        )

        return ranked_clusters, top_story

    def _build_ranked_clusters(
        self,
        clusters: Sequence[StoryCluster],
        ranked_results: list[StoryRankingResult],
        cluster_articles: dict[str, list[Article]],
    ) -> list[RankedCluster]:
        """Build RankedCluster objects from ranking results."""
        result_by_id = {r.cluster_id: r for r in ranked_results}

        cluster_list = list(clusters)
        cluster_list.sort(
            key=lambda c: (
                -(result_by_id[str(c.id)].score if str(c.id) in result_by_id else 0.0),
                str(c.id),
            )
        )

        ranked: list[RankedCluster] = []
        for idx, cluster in enumerate(cluster_list, start=1):
            result = result_by_id.get(str(cluster.id))
            if result is None:
                continue
            ranked.append(
                RankedCluster(
                    cluster=cluster,
                    score=result.score,
                    rank=idx,
                    signals=result.signals,
                    explanation=result.explanation,
                )
            )

        return ranked


__all__ = ["TopStoryResult", "TopStorySelector"]
