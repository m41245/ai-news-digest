"""
DetectStoryActivityUseCase for M83.

Orchestrates breaking and developing story detection:
1. Select bounded candidate story clusters with recent articles
2. Gather recent activity signals per cluster
3. Compute deterministic activity score
4. Classify into BREAKING / DEVELOPING / ONGOING / STALE
5. Optionally invoke LLM for ambiguous cases
6. Persist activity records
"""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from ai_news_digest.core.config import get_settings
from ai_news_digest.core.logging import get_logger
from ai_news_digest.domain.enums.source_status import SourceStatus
from ai_news_digest.domain.enums.story_activity_status import StoryActivityStatus
from ai_news_digest.domain.models.story_activity import StoryActivity
from ai_news_digest.domain.ports.article_repository import ArticleRepository
from ai_news_digest.domain.ports.claim_repository import ClaimRepository
from ai_news_digest.domain.ports.conflict_repository import ConflictRepository
from ai_news_digest.domain.ports.source_repository import SourceRepository
from ai_news_digest.domain.ports.story_activity_repository import (
    StoryActivityRepository,
)
from ai_news_digest.domain.ports.story_cluster_repository import (
    StoryClusterRepository,
)

if TYPE_CHECKING:
    from ai_news_digest.application.ai.provider_manager import ProviderManager


logger = get_logger(__name__)

_DETECTION_VERSION = "v1"


class DetectStoryActivityUseCase:
    """
    Use case for detecting breaking and developing story activity.

    Operates deterministically. LLM assistance is optional and only used
    for ambiguous activity near classification thresholds.
    """

    def __init__(
        self,
        article_repository: ArticleRepository,
        source_repository: SourceRepository,
        claim_repository: ClaimRepository,
        conflict_repository: ConflictRepository,
        story_activity_repository: StoryActivityRepository,
        story_cluster_repository: StoryClusterRepository,
        provider_manager: ProviderManager | None = None,
    ) -> None:
        self._article_repository = article_repository
        self._source_repository = source_repository
        self._claim_repository = claim_repository
        self._conflict_repository = conflict_repository
        self._story_activity_repository = story_activity_repository
        self._story_cluster_repository = story_cluster_repository
        self._provider_manager = provider_manager
        self._settings = get_settings()

    async def execute(self) -> dict[str, Any]:
        """
        Run bounded story activity detection.

        Returns a summary dict with counts.
        """
        start = time.monotonic()
        settings = self._settings

        if not settings.breaking_detection_enabled:
            logger.info("Breaking detection is disabled")
            return {"status": "disabled"}

        now = datetime.now(UTC)
        stale_cutoff = now - timedelta(hours=settings.stale_window_hours)

        candidates = await self._get_candidates(stale_cutoff=stale_cutoff)
        if not candidates:
            logger.info("No candidate story clusters for activity detection")
            return {"status": "completed", "evaluated": 0}

        source_map = await self._build_trusted_source_map()
        trusted_source_ids = set(source_map.keys())

        breaking = 0
        developing = 0
        ongoing = 0
        stale_count = 0
        llm_calls = 0
        evaluated = 0

        for cluster in candidates:
            activity = await self._evaluate_cluster(
                cluster=cluster,
                now=now,
                trusted_source_ids=trusted_source_ids,
                source_map=source_map,
            )
            evaluated += 1

            if activity.status == StoryActivityStatus.BREAKING:
                breaking += 1
            elif activity.status == StoryActivityStatus.DEVELOPING:
                developing += 1
            elif activity.status == StoryActivityStatus.ONGOING:
                ongoing += 1
            else:
                stale_count += 1

            if (
                self._provider_manager is not None
                and settings.ai_enabled
                and llm_calls < settings.max_llm_evaluations
                and self._is_ambiguous(activity)
            ):
                llm_status = await self._maybe_llm_check(activity, cluster)
                if llm_status is not None:
                    activity.status = llm_status
                    llm_calls += 1

            await self._story_activity_repository.upsert(activity)

        duration = time.monotonic() - start
        logger.info(
            "Story activity detection completed",
            evaluated=evaluated,
            breaking=breaking,
            developing=developing,
            ongoing=ongoing,
            stale=stale_count,
            llm_calls=llm_calls,
            duration_seconds=round(duration, 3),
        )

        return {
            "status": "completed",
            "evaluated": evaluated,
            "breaking": breaking,
            "developing": developing,
            "ongoing": ongoing,
            "stale": stale_count,
            "llm_calls": llm_calls,
            "duration_seconds": float(round(duration, 3)),
        }

    async def _get_candidates(
        self,
        *,
        stale_cutoff: datetime,
    ) -> list[Any]:
        """Return bounded candidate clusters for activity detection."""
        settings = self._settings
        recent_articles = await self._article_repository.list_public_articles_for_feed(
            published_from=stale_cutoff,
            limit=settings.max_story_candidates * settings.max_articles_per_story,
        )

        cluster_ids = []
        seen = set()
        for article in recent_articles:
            if article.cluster_id and article.cluster_id not in seen:
                cluster_ids.append(article.cluster_id)
                seen.add(article.cluster_id)
            if len(cluster_ids) >= settings.max_story_candidates:
                break

        if not cluster_ids:
            return []

        clusters = []
        for cid in cluster_ids:
            cluster = await self._story_cluster_repository.get_by_id(cid)
            if cluster is not None and cluster.status.value == "active":
                clusters.append(cluster)
        return clusters

    async def _build_trusted_source_map(self) -> dict[str, str]:
        """Build a map of trusted source IDs to source names."""
        sources = await self._source_repository.list_all()
        return {
            str(s.id): s.name
            for s in sources
            if s.is_active and s.status == SourceStatus.VERIFIED
        }

    async def _evaluate_cluster(
        self,
        *,
        cluster: Any,
        now: datetime,
        trusted_source_ids: set[str],
        source_map: dict[str, str],
    ) -> StoryActivity:
        """Evaluate activity for a single story cluster."""
        settings = self._settings
        developing_cutoff = now - timedelta(hours=settings.developing_window_hours)

        articles = await self._article_repository.list_by_cluster_id(
            cluster_id=cluster.id,
            limit=settings.max_articles_per_story,
        )

        recent_articles = [
            a for a in articles if a.published_at >= developing_cutoff
        ]

        article_count_recent = len(recent_articles)

        unique_sources = {
            str(a.source_id) for a in recent_articles if str(a.source_id) in trusted_source_ids
        }
        unique_source_count_recent = len(unique_sources)

        latest_article_at = max((a.published_at for a in recent_articles), default=None)
        first_article_at = min((a.published_at for a in recent_articles), default=None)

        hours_since_latest = None
        if latest_article_at is not None:
            hours_since_latest = (now - latest_article_at).total_seconds() / 3600.0

        window_hours = max(
            (now - first_article_at).total_seconds() / 3600.0, 1.0
        ) if first_article_at else float(settings.developing_window_hours)
        recent_article_velocity = article_count_recent / window_hours

        recent_claim_count = 0
        recent_conflict_count = 0
        state_change_count = 0

        if recent_articles:
            claim_texts = set()
            company_ids = set()
            topic_ids = set()
            for article in recent_articles:
                try:
                    claims = await self._claim_repository.list_by_article_id(article.id)
                    for claim in claims:
                        claim_texts.add(claim.claim_text.strip().lower())
                except Exception:
                    logger.debug(
                        "Failed to load claims for article",
                        article_id=str(article.id),
                        exc_info=True,
                    )

            recent_claim_count = len(claim_texts)
            state_change_count += recent_claim_count

            try:
                conflicts = await self._conflict_repository.list_by_story_cluster_id(
                    cluster.id, limit=settings.max_articles_per_story
                )
                recent_conflicts = [
                    c for c in conflicts
                    if c.created_at >= developing_cutoff
                ]
                recent_conflict_count = len(recent_conflicts)
                state_change_count += recent_conflict_count
            except Exception:
                recent_conflict_count = 0

            for article in recent_articles:
                for link in getattr(article, "company_links", []) or []:
                    company_ids.add(str(link.company_id))
                for link in getattr(article, "topic_links", []) or []:
                    topic_ids.add(str(link.topic_id))
            state_change_count += len(company_ids) + len(topic_ids)

        velocity_signal = min(recent_article_velocity / 10.0, 1.0)
        source_diversity_signal = min(unique_source_count_recent / 5.0, 1.0)

        if hours_since_latest is not None:
            recency_signal = max(
                0.0, 1.0 - hours_since_latest / float(settings.breaking_window_hours)
            )
        else:
            recency_signal = 0.0

        meaningful_update_signal = min(state_change_count / 10.0, 1.0)

        activity_score = (
            0.35 * velocity_signal
            + 0.25 * source_diversity_signal
            + 0.20 * recency_signal
            + 0.20 * meaningful_update_signal
        )

        if article_count_recent == 0:
            status = StoryActivityStatus.STALE
        elif activity_score < settings.developing_threshold:
            status = StoryActivityStatus.ONGOING
        elif (
            activity_score >= settings.breaking_threshold
            and unique_source_count_recent >= settings.minimum_independent_sources
            and hours_since_latest is not None
            and hours_since_latest <= settings.breaking_window_hours
        ):
            status = StoryActivityStatus.BREAKING
        else:
            status = StoryActivityStatus.DEVELOPING

        explanation_parts = []
        explanation_parts.append(f"velocity={recent_article_velocity:.1f}/hr")
        explanation_parts.append(f"sources={unique_source_count_recent}")
        if hours_since_latest is not None:
            explanation_parts.append(f"latest={hours_since_latest:.1f}h ago")
        explanation_parts.append(f"claims={recent_claim_count}")
        explanation_parts.append(f"conflicts={recent_conflict_count}")
        explanation_parts.append(f"state_changes={state_change_count}")
        explanation = "; ".join(explanation_parts)

        confidence = self._compute_confidence(
            article_count_recent=article_count_recent,
            unique_source_count_recent=unique_source_count_recent,
            has_recent_claims=recent_claim_count > 0,
            has_conflicts=recent_conflict_count > 0,
            velocity=recent_article_velocity,
        )

        return StoryActivity.create(
            story_cluster_id=cluster.id,
            status=status,
            activity_score=activity_score,
            confidence=confidence,
            explanation=explanation,
            evaluated_at=now,
            detection_version=_DETECTION_VERSION,
            article_count_recent=article_count_recent,
            unique_source_count_recent=unique_source_count_recent,
            recent_article_velocity=recent_article_velocity,
            latest_article_at=latest_article_at,
            first_article_at=first_article_at,
            recent_claim_count=recent_claim_count,
            recent_conflict_count=recent_conflict_count,
            state_change_count=state_change_count,
        )

    def _compute_confidence(
        self,
        *,
        article_count_recent: int,
        unique_source_count_recent: int,
        has_recent_claims: bool,
        has_conflicts: bool,
        velocity: float,
    ) -> float:
        """Compute a bounded confidence score for the activity classification."""
        confidence = 0.5
        if article_count_recent >= 3:
            confidence += 0.15
        if unique_source_count_recent >= 3:
            confidence += 0.15
        if has_recent_claims:
            confidence += 0.1
        if has_conflicts:
            confidence += 0.05
        if velocity >= 2.0:
            confidence += 0.05
        return min(confidence, 1.0)

    def _is_ambiguous(self, activity: StoryActivity) -> bool:
        """Return True if the activity classification is near a threshold."""
        margin = 0.1
        settings = self._settings
        near_breaking = abs(activity.activity_score - settings.breaking_threshold) <= margin
        near_developing = abs(activity.activity_score - settings.developing_threshold) <= margin
        return near_breaking or near_developing

    async def _maybe_llm_check(
        self,
        activity: StoryActivity,
        cluster: Any,
    ) -> StoryActivityStatus | None:
        """Optionally invoke LLM for ambiguous classifications."""
        if self._provider_manager is None or not self._settings.ai_enabled:
            return None

        try:
            from ai_news_digest.application.evaluation.story_activity_llm import (
                run_llm_story_activity_check,
            )

            result = await run_llm_story_activity_check(
                activity=activity,
                cluster=cluster,
                provider_manager=self._provider_manager,
            )
            if result is not None and result.status in (
                StoryActivityStatus.BREAKING.value,
                StoryActivityStatus.DEVELOPING.value,
                StoryActivityStatus.ONGOING.value,
                StoryActivityStatus.STALE.value,
            ):
                return StoryActivityStatus(result.status)
        except Exception as exc:
            logger.warning(
                "LLM story activity check failed",
                error=str(exc),
            )
        return None


__all__ = ["DetectStoryActivityUseCase"]
