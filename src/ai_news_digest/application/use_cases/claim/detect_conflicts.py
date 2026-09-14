"""
DetectClaimConflictsUseCase for M82.

Orchestrates the full conflict detection pipeline:
1. Retrieve recent eligible claims
2. Generate candidate pairs
3. Run deterministic comparisons
4. Optionally invoke LLM for uncertain pairs
5. Validate and persist conflict records
6. Deduplicate
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING
from uuid import UUID

from ai_news_digest.application.evaluation.conflict_candidates import (
    build_claim_contexts,
    generate_candidates,
)
from ai_news_digest.application.evaluation.conflict_confidence import (
    ConflictConfidenceFactors,
    compute_conflict_confidence,
)
from ai_news_digest.application.evaluation.conflict_detector import (
    run_deterministic_detection,
)
from ai_news_digest.application.evaluation.conflict_llm import (
    run_llm_conflict_analysis,
)
from ai_news_digest.core.config import get_settings
from ai_news_digest.core.logging import get_logger
from ai_news_digest.domain.enums.conflict_type import ConflictType
from ai_news_digest.domain.models.conflict import Conflict
from ai_news_digest.domain.ports.claim_repository import ClaimRepository
from ai_news_digest.domain.ports.conflict_repository import ConflictRepository

if TYPE_CHECKING:
    from ai_news_digest.application.ai.provider_manager import ProviderManager
    from ai_news_digest.domain.models.article import Article
    from ai_news_digest.domain.models.claim import Claim
    from ai_news_digest.domain.models.source import Source

logger = get_logger(__name__)


class DetectClaimConflictsUseCase:
    """
    Use case for detecting potential conflicts between claims.

    Operates in a deterministic-first mode. LLM analysis is optional
    and only used for uncertain high-value pairs when AI is enabled.
    """

    def __init__(
        self,
        claim_repository: ClaimRepository,
        conflict_repository: ConflictRepository,
        provider_manager: ProviderManager | None = None,
    ) -> None:
        self._claim_repository = claim_repository
        self._conflict_repository = conflict_repository
        self._provider_manager = provider_manager
        self._settings = get_settings()

    async def execute(self, *, detection_version: str = "v1") -> dict[str, int | float]:
        """
        Run a bounded conflict detection pass.

        Returns a summary dict with counts.
        """
        start = time.monotonic()
        settings = self._settings
        max_claims = settings.conflict_detection_max_claims
        max_candidates = settings.conflict_detection_max_candidates
        max_comparisons = settings.conflict_detection_max_comparisons
        max_llm = settings.conflict_detection_max_llm_comparisons

        logger.info(
            "Conflict detection started",
            max_claims=max_claims,
            max_candidates=max_candidates,
            max_comparisons=max_comparisons,
            max_llm=max_llm,
        )

        claims = await self._claim_repository.list_recent_for_conflicts(
            limit=max_claims,
        )
        if not claims:
            logger.info("No claims available for conflict detection")
            return {"candidates": 0, "conflicts": 0, "skipped": 0}

        logger.info(
            "Retrieved claims for conflict detection",
            claim_count=len(claims),
        )

        articles: dict[UUID, Article] = {}
        sources: dict[UUID, Source] = {}
        company_ids_by_article: dict[UUID, frozenset[str]] = {}
        topic_ids_by_article: dict[UUID, frozenset[str]] = {}

        article_ids = {c.article_id for c in claims}
        source_ids = {c.source_id for c in claims}

        for aid in article_ids:
            article = await self._claim_repository.get_article_for_conflict(aid)
            if article is not None:
                articles[aid] = article
                company_ids_by_article[aid] = frozenset(
                    str(cid) for cid in getattr(article, "company_ids", ())
                )
                topic_ids_by_article[aid] = frozenset(
                    str(tid) for tid in getattr(article, "topic_ids", ())
                )

        for sid in source_ids:
            source = await self._claim_repository.get_source_for_conflict(sid)
            if source is not None:
                sources[sid] = source

        contexts = build_claim_contexts(
            claims=list(claims),
            articles=articles,
            sources=sources,
            company_ids_by_article=company_ids_by_article,
            topic_ids_by_article=topic_ids_by_article,
        )

        candidates = generate_candidates(
            contexts=contexts,
            max_candidates_per_claim=max_candidates // max(len(contexts), 1),
            max_total_candidates=max_comparisons,
            temporal_window_hours=settings.conflict_detection_temporal_window_hours,
            detection_version=detection_version,
        )

        logger.info(
            "Generated conflict candidates",
            candidate_count=len(candidates),
        )

        conflicts_created = 0
        llm_calls = 0
        skipped = 0

        for candidate in candidates:
            if conflicts_created >= max_comparisons:
                break

            deterministic = run_deterministic_detection(
                candidate.claim_a, candidate.claim_b
            )

            if deterministic is None:
                skipped += 1
                continue

            conflict_type = deterministic.conflict_type
            confidence = deterministic.confidence
            explanation = deterministic.explanation

            if conflict_type is None:
                skipped += 1
                continue

            if (
                self._provider_manager is not None
                and self._settings.ai_enabled
                and llm_calls < max_llm
                and confidence < 0.8
            ):
                llm_result = await run_llm_conflict_analysis(
                    candidate=candidate,
                    provider_manager=self._provider_manager,
                    deterministic=deterministic,
                )
                llm_calls += 1
                if llm_result is not None:
                    confidence = max(confidence, llm_result.confidence)
                    if llm_result.reason:
                        explanation = llm_result.reason
                    if llm_result.conflicting_aspects:
                        explanation += (
                            " Aspects: "
                            + ", ".join(llm_result.conflicting_aspects)
                        )

            factors = ConflictConfidenceFactors(
                entity_match=bool(candidate.company_overlap or candidate.topic_overlap),
                claim_type_compatible=True,
                temporal_compatible=candidate.temporal_compatible,
                numeric_mismatch=(conflict_type == ConflictType.NUMERIC),
                date_mismatch=(conflict_type == ConflictType.DATE),
                event_state_mismatch=(conflict_type == ConflictType.EVENT_STATUS),
                evidence_support_a=candidate.claim_a.evidence_support_score or 0.0,
                evidence_support_b=candidate.claim_b.evidence_support_score or 0.0,
                source_independent=not candidate.same_source,
            )
            confidence = compute_conflict_confidence(factors, conflict_type)

            story_cluster_id = self._find_shared_story_cluster(
                candidate.claim_a, candidate.claim_b
            )

            conflict = Conflict.create(
                claim_a_id=candidate.claim_a.id,
                claim_b_id=candidate.claim_b.id,
                article_a_id=candidate.article_a.id,
                article_b_id=candidate.article_b.id,
                source_a_id=candidate.source_a.id,
                source_b_id=candidate.source_b.id,
                conflict_type=conflict_type,
                confidence=confidence,
                explanation=explanation,
                detection_version=detection_version,
                story_cluster_id=story_cluster_id,
                same_source=candidate.same_source,
            )

            existing = await self._conflict_repository.find_existing(
                claim_a_id=conflict.claim_a_id,
                claim_b_id=conflict.claim_b_id,
                detection_version=detection_version,
            )
            if existing is None:
                await self._conflict_repository.create(conflict)
                conflicts_created += 1
            else:
                skipped += 1

        duration = time.monotonic() - start
        logger.info(
            "Conflict detection completed",
            candidates=len(candidates),
            conflicts_created=conflicts_created,
            skipped=skipped,
            llm_calls=llm_calls,
            duration_seconds=round(duration, 3),
        )

        return {
            "candidates": len(candidates),
            "conflicts": conflicts_created,
            "skipped": skipped,
            "llm_calls": llm_calls,
            "duration_seconds": round(duration, 3),
        }

    def _find_shared_story_cluster(
        self,
        claim_a: Claim,
        claim_b: Claim,
    ) -> UUID | None:
        """Return a shared story cluster ID if both claims belong to the same cluster."""
        cluster_a = getattr(claim_a, "story_cluster_id", None)
        cluster_b = getattr(claim_b, "story_cluster_id", None)
        if isinstance(cluster_a, UUID) and isinstance(cluster_b, UUID) and cluster_a == cluster_b:
            return cluster_a
        return None


__all__ = ["DetectClaimConflictsUseCase"]
