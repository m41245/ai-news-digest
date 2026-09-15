"""
DetectTrendsUseCase for M85.

Orchestrates deterministic trend detection and emerging story intelligence:
1. Select bounded candidates from companies, topics, categories, and story clusters
2. Gather recent and baseline activity signals per candidate
3. Compute deterministic trend score and momentum score
4. Derive trend status (EMERGING, RISING, SUSTAINED, COOLING, STALE)
5. Upsert trend records for public API consumption
"""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID

from ai_news_digest.core.config import get_settings
from ai_news_digest.core.logging import get_logger
from ai_news_digest.domain.enums.story_activity_status import StoryActivityStatus
from ai_news_digest.domain.enums.trend_status import TrendStatus
from ai_news_digest.domain.enums.trend_type import TrendType
from ai_news_digest.domain.models.article import Article
from ai_news_digest.domain.models.trend import Trend
from ai_news_digest.domain.ports.article_repository import ArticleRepository
from ai_news_digest.domain.ports.category_repository import CategoryRepository
from ai_news_digest.domain.ports.company_repository import CompanyRepository
from ai_news_digest.domain.ports.story_activity_repository import StoryActivityRepository
from ai_news_digest.domain.ports.story_cluster_repository import StoryClusterRepository
from ai_news_digest.domain.ports.story_event_repository import StoryEventRepository
from ai_news_digest.domain.ports.topic_repository import TopicRepository
from ai_news_digest.domain.ports.trend_repository import TrendRepository

if TYPE_CHECKING:
    from ai_news_digest.application.ai.provider_manager import ProviderManager


logger = get_logger(__name__)

_DETECTION_VERSION = "v1"


class DetectTrendsUseCase:
    """
    Use case for deterministic trend detection and emerging story intelligence.

    Operates without requiring an LLM. AI may optionally be used for trend
    naming or explanation, but the core signals and scores remain deterministic.
    """

    def __init__(
        self,
        article_repository: ArticleRepository,
        source_repository: Any,
        topic_repository: TopicRepository,
        company_repository: CompanyRepository,
        category_repository: CategoryRepository,
        story_cluster_repository: StoryClusterRepository,
        story_activity_repository: StoryActivityRepository,
        story_event_repository: StoryEventRepository,
        trend_repository: TrendRepository,
        provider_manager: ProviderManager | None = None,
    ) -> None:
        self._article_repository = article_repository
        self._source_repository = source_repository
        self._topic_repository = topic_repository
        self._company_repository = company_repository
        self._category_repository = category_repository
        self._story_cluster_repository = story_cluster_repository
        self._story_activity_repository = story_activity_repository
        self._story_event_repository = story_event_repository
        self._trend_repository = trend_repository
        self._provider_manager = provider_manager
        self._settings = get_settings()

    async def execute(self) -> dict[str, Any]:
        """
        Run bounded trend detection.

        Returns a summary dict with counts per trend type and status.
        """
        start = time.monotonic()
        settings = self._settings

        if not settings.trend_detection_enabled:
            logger.info("Trend detection is disabled")
            return {"status": "disabled"}

        now = datetime.now(UTC)
        recent_cutoff = now - timedelta(hours=settings.trend_recent_window_hours)
        baseline_cutoff = now - timedelta(hours=settings.trend_baseline_window_hours)

        trusted_source_ids = await self._build_trusted_source_ids()
        activity_map = await self._build_activity_map(recent_cutoff)

        article_limit = settings.trend_max_total_candidates * 10
        recent_articles = await self._article_repository.list_public_articles_for_feed(
            published_from=recent_cutoff,
            limit=article_limit,
        )
        baseline_articles = await self._article_repository.list_public_articles_for_feed(
            published_from=baseline_cutoff,
            published_to=recent_cutoff,
            limit=article_limit,
        )

        candidates: list[dict[str, Any]] = []
        candidates.extend(
            await self._collect_company_candidates(
                recent_cutoff,
                baseline_cutoff,
                trusted_source_ids,
                recent_articles,
                baseline_articles,
            )
        )
        candidates.extend(
            await self._collect_topic_candidates(
                recent_cutoff,
                baseline_cutoff,
                trusted_source_ids,
                recent_articles,
                baseline_articles,
            )
        )
        candidates.extend(
            await self._collect_category_candidates(
                recent_cutoff,
                baseline_cutoff,
                trusted_source_ids,
                recent_articles,
                baseline_articles,
            )
        )
        candidates.extend(
            await self._collect_story_cluster_candidates(
                recent_cutoff,
                baseline_cutoff,
                trusted_source_ids,
                recent_articles,
                baseline_articles,
            )
        )

        if not candidates:
            logger.info("No trend candidates found")
            return {"status": "completed", "evaluated": 0}

        candidates = candidates[: settings.trend_max_total_candidates]

        detected: dict[str, int] = {}
        evaluated = 0

        for candidate in candidates:
            trend = await self._evaluate_candidate(
                candidate=candidate,
                now=now,
                recent_cutoff=recent_cutoff,
                baseline_cutoff=baseline_cutoff,
                trusted_source_ids=trusted_source_ids,
                activity_map=activity_map,
            )
            evaluated += 1
            await self._trend_repository.upsert(trend)
            detected[trend.status.value] = detected.get(trend.status.value, 0) + 1

        duration = time.monotonic() - start
        logger.info(
            "Trend detection completed",
            evaluated=evaluated,
            detected=detected,
            duration_seconds=round(duration, 3),
        )

        return {
            "status": "completed",
            "evaluated": evaluated,
            "detected": detected,
            "duration_seconds": float(round(duration, 3)),
        }

    async def _build_trusted_source_ids(self) -> set[str]:
        sources = await self._source_repository.list_all()
        return {
            str(s.id)
            for s in sources
            if s.is_active and s.status.value == "verified"
        }

    async def _build_activity_map(
        self,
        recent_cutoff: datetime,
    ) -> dict[str, Any]:
        activities = await self._story_activity_repository.list_recent(
            evaluated_since=recent_cutoff,
            limit=1000,
        )
        activity_map: dict[str, Any] = {}
        for activity in activities:
            activity_map[str(activity.story_cluster_id)] = {
                "status": activity.status.value,
                "activity_score": activity.activity_score,
            }
        return activity_map

    @staticmethod
    def _filter_articles_by_company(
        articles: list[Article],
        company_id: str,
    ) -> list[Article]:
        return [a for a in articles if UUID(company_id) in (a.company_ids or ())]

    @staticmethod
    def _filter_articles_by_topic(
        articles: list[Article],
        topic_id: str,
    ) -> list[Article]:
        return [a for a in articles if UUID(topic_id) in (a.topic_ids or ())]

    @staticmethod
    def _filter_articles_by_category(
        articles: list[Article],
        category_id: str,
    ) -> list[Article]:
        return [
            a
            for a in articles
            if a.category_id is not None and str(a.category_id) == category_id
        ]

    async def _collect_company_candidates(
        self,
        recent_cutoff: datetime,
        baseline_cutoff: datetime,
        trusted_source_ids: set[str],
        recent_articles: list[Article],
        baseline_articles: list[Article],
    ) -> list[dict[str, Any]]:
        settings = self._settings
        companies = await self._company_repository.list_all_with_counts()
        candidates: list[dict[str, Any]] = []
        for company in companies:
            company_id = str(company.id)
            company_recent_articles = self._filter_articles_by_company(recent_articles, company_id)
            if len(company_recent_articles) < settings.trend_min_recent_activity:
                continue
            company_baseline_articles = (
                self._filter_articles_by_company(baseline_articles, company_id)
            )
            unique_sources = {
                str(a.source_id) for a in company_recent_articles
                if str(a.source_id) in trusted_source_ids
            }
            if len(unique_sources) < settings.trend_min_sources:
                continue
            cluster_ids = {str(a.cluster_id) for a in company_recent_articles if a.cluster_id}
            candidates.append({
                "type": TrendType.COMPANY_TREND,
                "canonical_key": f"company:{company.name.lower()}",
                "display_name": company.name,
                "recent_activity": len(company_recent_articles),
                "baseline_activity": len(company_baseline_articles),
                "source_count": len(unique_sources),
                "story_count": len(cluster_ids),
                "cluster_ids": cluster_ids,
                "related_company_ids": frozenset([company.id]),
            })
        return candidates[: settings.trend_max_candidates_per_type]

    async def _collect_topic_candidates(
        self,
        recent_cutoff: datetime,
        baseline_cutoff: datetime,
        trusted_source_ids: set[str],
        recent_articles: list[Article],
        baseline_articles: list[Article],
    ) -> list[dict[str, Any]]:
        settings = self._settings
        topics = await self._topic_repository.list_all_with_counts()
        candidates: list[dict[str, Any]] = []
        for topic in topics:
            topic_id = str(topic.id)
            topic_recent_articles = self._filter_articles_by_topic(recent_articles, topic_id)
            if len(topic_recent_articles) < settings.trend_min_recent_activity:
                continue
            topic_baseline_articles = self._filter_articles_by_topic(baseline_articles, topic_id)
            unique_sources = {
                str(a.source_id) for a in topic_recent_articles
                if str(a.source_id) in trusted_source_ids
            }
            if len(unique_sources) < settings.trend_min_sources:
                continue
            cluster_ids = {str(a.cluster_id) for a in topic_recent_articles if a.cluster_id}
            candidates.append({
                "type": TrendType.TOPIC_TREND,
                "canonical_key": f"topic:{topic.name.lower()}",
                "display_name": topic.name,
                "recent_activity": len(topic_recent_articles),
                "baseline_activity": len(topic_baseline_articles),
                "source_count": len(unique_sources),
                "story_count": len(cluster_ids),
                "cluster_ids": cluster_ids,
                "related_topic_ids": frozenset([topic.id]),
            })
        return candidates[: settings.trend_max_candidates_per_type]

    async def _collect_category_candidates(
        self,
        recent_cutoff: datetime,
        baseline_cutoff: datetime,
        trusted_source_ids: set[str],
        recent_articles: list[Article],
        baseline_articles: list[Article],
    ) -> list[dict[str, Any]]:
        settings = self._settings
        categories = await self._category_repository.list_all()
        candidates: list[dict[str, Any]] = []
        for category in categories:
            category_id = str(category.id)
            category_recent_articles = (
                self._filter_articles_by_category(recent_articles, category_id)
            )
            if len(category_recent_articles) < settings.trend_min_recent_activity:
                continue
            category_baseline_articles = (
                self._filter_articles_by_category(baseline_articles, category_id)
            )
            unique_sources = {
                str(a.source_id) for a in category_recent_articles
                if str(a.source_id) in trusted_source_ids
            }
            if len(unique_sources) < settings.trend_min_sources:
                continue
            cluster_ids = {str(a.cluster_id) for a in category_recent_articles if a.cluster_id}
            candidates.append({
                "type": TrendType.CATEGORY_TREND,
                "canonical_key": f"category:{category.name.lower()}",
                "display_name": category.name,
                "recent_activity": len(category_recent_articles),
                "baseline_activity": len(category_baseline_articles),
                "source_count": len(unique_sources),
                "story_count": len(cluster_ids),
                "cluster_ids": cluster_ids,
                "related_category_ids": frozenset([category.id]),
            })
        return candidates[: settings.trend_max_candidates_per_type]

    async def _collect_story_cluster_candidates(
        self,
        recent_cutoff: datetime,
        baseline_cutoff: datetime,
        trusted_source_ids: set[str],
        recent_articles: list[Article],
        baseline_articles: list[Article],
    ) -> list[dict[str, Any]]:
        settings = self._settings
        clusters = await self._story_cluster_repository.find_recent_active_clusters(
            cutoff=recent_cutoff,
            limit=settings.trend_max_candidates_per_type,
        )
        candidates: list[dict[str, Any]] = []
        for cluster in clusters:
            cluster_recent_articles = [
                a for a in recent_articles
                if a.cluster_id == cluster.id
            ]
            if len(cluster_recent_articles) < settings.trend_min_recent_activity:
                continue
            cluster_baseline_articles = [
                a for a in baseline_articles
                if a.cluster_id == cluster.id
            ]
            unique_sources = {
                str(a.source_id) for a in cluster_recent_articles
                if str(a.source_id) in trusted_source_ids
            }
            if len(unique_sources) < settings.trend_min_sources:
                continue
            candidates.append({
                "type": TrendType.STORY_TREND,
                "canonical_key": f"story:{cluster.slug}",
                "display_name": cluster.title,
                "recent_activity": len(cluster_recent_articles),
                "baseline_activity": len(cluster_baseline_articles),
                "source_count": len(unique_sources),
                "story_count": 1,
                "cluster_ids": {str(cluster.id)},
            })
        return candidates

    async def _evaluate_candidate(
        self,
        *,
        candidate: dict[str, Any],
        now: datetime,
        recent_cutoff: datetime,
        baseline_cutoff: datetime,
        trusted_source_ids: set[str],
        activity_map: dict[str, Any],
    ) -> Trend:
        settings = self._settings

        recent_activity = candidate["recent_activity"]
        baseline_activity = candidate["baseline_activity"]
        source_count = candidate["source_count"]
        story_count = candidate["story_count"]

        event_count = 0
        for cid in candidate.get("cluster_ids", set()):
            try:
                events = await self._story_event_repository.list_by_cluster_id(
                    UUID(cid), limit=100
                )
                event_count += sum(
                    1 for e in events if e.created_at >= recent_cutoff
                )
            except Exception:
                logger.debug(
                    "Failed to load story events",
                    cluster_id=cid,
                    exc_info=True,
                )

        growth_ratio = (recent_activity - baseline_activity) / max(baseline_activity, 1)

        activity_boost = 0.0
        for cid in candidate.get("cluster_ids", set()):
            activity = activity_map.get(cid)
            if activity and activity["status"] in (
                StoryActivityStatus.BREAKING.value,
                StoryActivityStatus.DEVELOPING.value,
            ):
                activity_boost = max(activity_boost, activity["activity_score"])

        latest_article_at = None
        try:
            cid = (
                next(iter(candidate.get("cluster_ids", set())))
                if candidate.get("cluster_ids")
                else None
            )
            if cid:
                articles = await self._article_repository.list_by_cluster_id(UUID(cid), limit=1)
                if articles:
                    latest_article_at = articles[0].published_at
        except Exception:
            latest_article_at = None

        hours_since_latest = None
        if latest_article_at is not None:
            hours_since_latest = (now - latest_article_at).total_seconds() / 3600.0

        activity_signal = min(recent_activity / 20.0, 1.0)
        growth_signal = min(max(growth_ratio, 0.0), 2.0) / 2.0
        source_diversity_signal = min(source_count / 10.0, 1.0)
        story_growth_signal = min(story_count / 5.0, 1.0)
        event_signal = min(event_count / 5.0, 1.0)
        recency_signal = (
            max(0.0, 1.0 - (hours_since_latest or 24.0) / 24.0)
            if hours_since_latest is not None
            else 0.0
        )

        trend_score = (
            settings.trend_activity_weight * activity_signal
            + settings.trend_growth_weight * growth_signal
            + settings.trend_source_diversity_weight * source_diversity_signal
            + settings.trend_story_growth_weight * story_growth_signal
            + settings.trend_event_weight * event_signal
            + settings.trend_recency_weight * recency_signal
            + settings.trend_activity_boost_weight * activity_boost
        ) * 100.0

        momentum_score = (
            0.5 * growth_signal
            + 0.3 * recency_signal
            + 0.2 * activity_boost
        ) * 100.0

        if recent_activity == 0:
            status = TrendStatus.STALE
        elif trend_score >= 65:
            status = TrendStatus.EMERGING
        elif trend_score >= 50:
            status = TrendStatus.RISING
        elif trend_score >= 35:
            status = TrendStatus.SUSTAINED
        elif trend_score >= 20:
            status = TrendStatus.COOLING
        else:
            status = TrendStatus.STALE

        explanation_parts = [
            f"recent={recent_activity}",
            f"baseline={baseline_activity}",
            f"growth={growth_ratio:+.2f}",
            f"sources={source_count}",
            f"stories={story_count}",
            f"events={event_count}",
        ]
        if hours_since_latest is not None:
            explanation_parts.append(f"latest={hours_since_latest:.1f}h")
        explanation = "; ".join(explanation_parts)

        trend_metadata: dict[str, str] = {
            "growth_ratio": f"{growth_ratio:.2f}",
            "activity_boost": f"{activity_boost:.2f}",
        }
        if hours_since_latest is not None:
            trend_metadata["hours_since_latest"] = f"{hours_since_latest:.1f}"

        first_detected_at = now
        existing = await self._trend_repository.get_by_canonical_key(candidate["canonical_key"])
        if existing is not None:
            first_detected_at = existing.first_detected_at

        return Trend.create(
            trend_type=candidate["type"],
            canonical_key=candidate["canonical_key"],
            display_name=candidate["display_name"],
            status=status,
            trend_score=trend_score,
            momentum_score=momentum_score,
            first_detected_at=first_detected_at,
            last_detected_at=now,
            recent_activity=recent_activity,
            baseline_activity=baseline_activity,
            source_count=source_count,
            story_count=story_count,
            event_count=event_count,
            explanation=explanation,
            trend_metadata=trend_metadata,
            related_company_ids=candidate.get("related_company_ids"),
            related_topic_ids=candidate.get("related_topic_ids"),
            related_category_ids=candidate.get("related_category_ids"),
        )


__all__ = ["DetectTrendsUseCase"]
