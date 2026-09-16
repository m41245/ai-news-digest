"""
Intelligence evaluation service for M93.

Provides deterministic quality measurements over M80-M92 intelligence systems.
Does not modify production intelligence. Respects AI_ENABLED=false.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from ai_news_digest.core.config import get_settings
from ai_news_digest.core.logging import get_logger
from ai_news_digest.domain.evaluation.metrics import (
    EvaluationMetricType,
    EvaluationReport,
    EvaluationStatus,
    MetricValue,
    QualitySnapshot,
)

logger = get_logger(__name__)


class IntelligenceEvaluationService:
    """Deterministic intelligence evaluation and quality measurement.

    Observes production intelligence (M80-M92) and computes bounded metrics.
    Does not modify production behavior. Respects AI_ENABLED=false.
    """

    def __init__(self) -> None:
        self._settings = get_settings()

    async def evaluate_articles(
        self,
        articles: list[Any],
        source_lookup: dict[str, Any] | None = None,
        now: datetime | None = None,
    ) -> list[MetricValue]:
        """Evaluate article intelligence quality."""
        if now is None:
            now = datetime.now(UTC)

        metrics: list[MetricValue] = []
        total = len(articles)
        if total == 0:
            return metrics

        source_lookup = source_lookup or {}

        # Structured output validity
        valid_count = sum(
            1 for a in articles
            if getattr(a, "summary", None) and getattr(a, "key_takeaways_json", None)
        )
        metrics.append(MetricValue(
            metric_type=EvaluationMetricType.STRUCTURED_OUTPUT_VALIDITY,
            value=valid_count / total,
            sample_count=total,
        ))

        # Summary presence
        summary_present = sum(1 for a in articles if getattr(a, "summary", None))
        metrics.append(MetricValue(
            metric_type=EvaluationMetricType.SUMMARY_PRESENCE,
            value=summary_present / total,
            sample_count=total,
        ))

        # Summary empty rate
        empty_summary = sum(
            1 for a in articles
            if not getattr(a, "summary", None) or not getattr(a, "summary", "").strip()
        )
        metrics.append(MetricValue(
            metric_type=EvaluationMetricType.SUMMARY_EMPTY_RATE,
            value=empty_summary / total,
            sample_count=total,
        ))

        # Summary length bounds (expect 50-2000 chars)
        summaries_with_length = [
            len(getattr(a, "summary", "")) for a in articles if getattr(a, "summary", None)
        ]
        if summaries_with_length:
            in_bounds = sum(1 for length in summaries_with_length if 50 <= length <= 2000)
            metrics.append(MetricValue(
                metric_type=EvaluationMetricType.SUMMARY_LENGTH_BOUNDS,
                value=in_bounds / len(summaries_with_length),
                sample_count=len(summaries_with_length),
            ))

        # Metadata completeness
        complete_metadata = sum(
            1 for a in articles
            if (
                getattr(a, "ai_provider", None)
                and getattr(a, "ai_model", None)
                and getattr(a, "ai_processed_at", None)
            )
        )
        ai_processed = [a for a in articles if getattr(a, "ai_processed_at", None)]
        if ai_processed:
            metrics.append(MetricValue(
                metric_type=EvaluationMetricType.METADATA_COMPLETENESS,
                value=complete_metadata / len(ai_processed),
                sample_count=len(ai_processed),
            ))

        # Why_it_matters presence
        why_present = sum(1 for a in articles if getattr(a, "why_it_matters", None))
        metrics.append(MetricValue(
            metric_type=EvaluationMetricType.WHY_IT_MATTERS_PRESENCE,
            value=why_present / total,
            sample_count=total,
        ))

        # Takeaway count bounds (expect 3-10)
        articles_with_takeaways = [
            a for a in articles if getattr(a, "key_takeaways_json", None)
        ]
        if articles_with_takeaways:
            import json
            in_bounds_takeaways = 0
            empty_takeaways = 0
            duplicate_takeaways = 0
            for a in articles_with_takeaways:
                try:
                    takeaways = json.loads(a.key_takeaways_json)
                    if isinstance(takeaways, list) and 3 <= len(takeaways) <= 10:
                        in_bounds_takeaways += 1
                    if not takeaways or all(
                        not isinstance(t, str) or not t.strip() for t in takeaways
                    ):
                        empty_takeaways += 1
                    if isinstance(takeaways, list) and len(takeaways) != len(
                        {t.strip().lower() for t in takeaways if isinstance(t, str)}
                    ):
                        duplicate_takeaways += 1
                except (json.JSONDecodeError, TypeError):
                    empty_takeaways += 1
            metrics.append(MetricValue(
                metric_type=EvaluationMetricType.TAKEAWAY_COUNT,
                value=in_bounds_takeaways / len(articles_with_takeaways),
                sample_count=len(articles_with_takeaways),
            ))
            metrics.append(MetricValue(
                metric_type=EvaluationMetricType.TAKEAWAY_EMPTY_RATE,
                value=empty_takeaways / total,
                sample_count=total,
            ))
            metrics.append(MetricValue(
                metric_type=EvaluationMetricType.TAKEAWAY_DUPLICATE_RATE,
                value=duplicate_takeaways / len(articles_with_takeaways),
                sample_count=len(articles_with_takeaways),
            ))

        # Summary oversized rate (>2000 chars)
        oversized = sum(
            1 for a in articles
            if getattr(a, "summary", None) and len(a.summary) > 2000
        )
        metrics.append(MetricValue(
            metric_type=EvaluationMetricType.SUMMARY_OVERSIZED_RATE,
            value=oversized / total,
            sample_count=total,
        ))

        # Summary input copy rate (summary length close to content length)
        input_copy = sum(
            1 for a in articles
            if (
                getattr(a, "summary", None)
                and getattr(a, "content", None)
                and len(a.summary) >= 0.9 * len(a.content)
                and len(a.content) > 200
            )
        )
        articles_with_content = [
            a for a in articles if getattr(a, "content", None) and len(a.content) > 200
        ]
        if articles_with_content:
            metrics.append(MetricValue(
                metric_type=EvaluationMetricType.SUMMARY_INPUT_COPY_RATE,
                value=input_copy / len(articles_with_content),
                sample_count=len(articles_with_content),
            ))

        # Category validity
        valid_category = sum(
            1 for a in articles
            if getattr(a, "category_id", None) or getattr(a, "categories", ())
        )
        metrics.append(MetricValue(
            metric_type=EvaluationMetricType.CATEGORY_VALIDITY,
            value=valid_category / total,
            sample_count=total,
        ))

        # Company normalization
        normalized_companies = sum(
            1 for a in articles
            if getattr(a, "companies", ()) or getattr(a, "company_ids", ())
        )
        metrics.append(MetricValue(
            metric_type=EvaluationMetricType.COMPANY_NORMALIZATION,
            value=normalized_companies / total,
            sample_count=total,
        ))

        # Topic normalization
        normalized_topics = sum(
            1 for a in articles
            if getattr(a, "topics", ()) or getattr(a, "topic_ids", ())
        )
        metrics.append(MetricValue(
            metric_type=EvaluationMetricType.TOPIC_NORMALIZATION,
            value=normalized_topics / total,
            sample_count=total,
        ))

        return metrics

    async def evaluate_claims(
        self,
        claims: list[Any],
        evidence_by_claim: dict[str, list[Any]] | None = None,
        conflicts_by_claim: dict[str, list[Any]] | None = None,
        now: datetime | None = None,
    ) -> list[MetricValue]:
        """Evaluate claim and evidence quality."""
        if now is None:
            now = datetime.now(UTC)

        metrics: list[MetricValue] = []
        total = len(claims)
        if total == 0:
            return metrics

        evidence_by_claim = evidence_by_claim or {}
        conflicts_by_claim = conflicts_by_claim or {}

        # Evidence attachment rate
        with_evidence = sum(1 for c in claims if evidence_by_claim.get(str(c.id), []))
        metrics.append(MetricValue(
            metric_type=EvaluationMetricType.EVIDENCE_ATTACHMENT_RATE,
            value=with_evidence / total,
            sample_count=total,
        ))

        # Supported claim rate
        supported = sum(
            1 for c in claims
            if str(getattr(c, "status", "")).lower() == "supported"
        )
        metrics.append(MetricValue(
            metric_type=EvaluationMetricType.SUPPORTED_CLAIM_RATE,
            value=supported / total,
            sample_count=total,
        ))

        # Evidence coverage (avg evidence per claim)
        evidence_counts = [len(evidence_by_claim.get(str(c.id), [])) for c in claims]
        avg_coverage = sum(evidence_counts) / total if total > 0 else 0.0
        metrics.append(MetricValue(
            metric_type=EvaluationMetricType.EVIDENCE_COVERAGE,
            value=min(1.0, avg_coverage / 5.0),
            sample_count=total,
        ))

        # Conflict detection rate
        with_conflicts = sum(1 for c in claims if conflicts_by_claim.get(str(c.id), []))
        metrics.append(MetricValue(
            metric_type=EvaluationMetricType.CONFLICT_DETECTION_RATE,
            value=with_conflicts / total,
            sample_count=total,
        ))

        # Claim completeness (non-empty text and valid type)
        complete_claims = sum(
            1 for c in claims
            if getattr(c, "claim_text", None) and getattr(c, "claim_text", "").strip()
            and getattr(c, "claim_type", None) is not None
        )
        metrics.append(MetricValue(
            metric_type=EvaluationMetricType.CLAIM_COMPLETENESS,
            value=complete_claims / total,
            sample_count=total,
        ))

        # Provenance completeness
        complete = sum(
            1 for c in claims
            if getattr(c, "ai_provider", None) and getattr(c, "ai_model", None)
        )
        metrics.append(MetricValue(
            metric_type=EvaluationMetricType.PROVENANCE_COMPLETENESS,
            value=complete / total,
            sample_count=total,
        ))

        return metrics

    async def evaluate_story_clusters(
        self,
        clusters: list[Any],
        articles_by_cluster: dict[str, list[Any]] | None = None,
        now: datetime | None = None,
    ) -> list[MetricValue]:
        """Evaluate story cluster quality."""
        if now is None:
            now = datetime.now(UTC)

        metrics: list[MetricValue] = []
        total = len(clusters)
        if total == 0:
            return metrics

        articles_by_cluster = articles_by_cluster or {}

        # Duplicate rate (clusters with only 1 article)
        singletons = sum(
            1 for c in clusters
            if len(articles_by_cluster.get(str(c.id), [])) <= 1
        )
        metrics.append(MetricValue(
            metric_type=EvaluationMetricType.CLUSTER_SINGLETON_RATE,
            value=singletons / total,
            sample_count=total,
        ))

        # Source diversity
        multi_source = sum(
            1 for c in clusters
            if len({
                a.source_id for a in articles_by_cluster.get(str(c.id), [])
                if getattr(a, "source_id", None)
            }) > 1
        )
        metrics.append(MetricValue(
            metric_type=EvaluationMetricType.CLUSTER_DUPLICATE_RATE,
            value=1.0 - (multi_source / total) if total > 0 else 0.0,
            sample_count=total,
        ))

        return metrics

    async def evaluate_trends(
        self,
        trends: list[Any],
        now: datetime | None = None,
    ) -> list[MetricValue]:
        """Evaluate trend quality."""
        if now is None:
            now = datetime.now(UTC)

        metrics: list[MetricValue] = []
        total = len(trends)
        if total == 0:
            return metrics

        # Source diversity
        multi_source = sum(
            1 for t in trends if getattr(t, "source_count", 0) > 1
        )
        metrics.append(MetricValue(
            metric_type=EvaluationMetricType.TREND_SCORE_DISTRIBUTION,
            value=multi_source / total,
            sample_count=total,
        ))

        # Provenance completeness
        complete = sum(
            1 for t in trends if getattr(t, "source_count", 0) > 0
        )
        metrics.append(MetricValue(
            metric_type=EvaluationMetricType.PROVENANCE_COMPLETENESS,
            value=complete / total,
            sample_count=total,
        ))

        return metrics

    async def evaluate_relationships(
        self,
        relationships: list[Any],
        now: datetime | None = None,
    ) -> list[MetricValue]:
        """Evaluate graph relationship quality."""
        if now is None:
            now = datetime.now(UTC)

        metrics: list[MetricValue] = []
        total = len(relationships)
        if total == 0:
            return metrics

        # Relationship completeness
        complete = sum(
            1 for r in relationships
            if (
                getattr(r, "subject_entity_id", None)
                and getattr(r, "object_entity_id", None)
                and getattr(r, "relationship_type", None)
            )
        )
        metrics.append(MetricValue(
            metric_type=EvaluationMetricType.GRAPH_RELATIONSHIP_COMPLETENESS,
            value=complete / total,
            sample_count=total,
        ))

        # Provenance completeness
        with_provenance = sum(
            1 for r in relationships
            if getattr(r, "provenance_source", None)
        )
        metrics.append(MetricValue(
            metric_type=EvaluationMetricType.PROVENANCE_COMPLETENESS,
            value=with_provenance / total,
            sample_count=total,
        ))

        return metrics

    async def evaluate_extraction(
        self,
        articles: list[Any],
        now: datetime | None = None,
    ) -> list[MetricValue]:
        """Evaluate extraction quality."""
        if now is None:
            now = datetime.now(UTC)

        metrics: list[MetricValue] = []
        total = len(articles)
        if total == 0:
            return metrics

        # Extraction success rate (non-None content with sufficient length)
        successful = sum(
            1 for a in articles
            if getattr(a, "content", None) and len(getattr(a, "content", "")) >= 200
        )
        metrics.append(MetricValue(
            metric_type=EvaluationMetricType.EXTRACTION_SUCCESS_RATE,
            value=successful / total,
            sample_count=total,
        ))

        # Fallback rate (rss extraction method)
        fallback = sum(
            1 for a in articles
            if getattr(a, "extraction_method", "") != "rss"
        )
        metrics.append(MetricValue(
            metric_type=EvaluationMetricType.EXTRACTION_FALLBACK_RATE,
            value=fallback / total,
            sample_count=total,
        ))

        return metrics

    async def run_evaluation(
        self,
        evaluation_type: str = "daily",
        scope: str = "global",
        container: Any = None,
    ) -> EvaluationReport:
        """Run a full intelligence evaluation."""
        started_at = datetime.now(UTC)
        run_id = f"eval-{started_at.strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"

        metrics: list[MetricValue] = []
        error: str | None = None

        try:
            if container is not None:
                try:
                    article_repo = container.article_repository
                    claim_repo = container.claim_repository
                    conflict_repo = container.conflict_repository
                    story_cluster_repo = container.story_cluster_repository
                    trend_repo = container.trend_repo
                    relationship_repo = container.relationship_repository

                    articles = await article_repo.list_recent(limit=500)
                    claims = await claim_repo.list_recent_for_conflicts(limit=500)
                    clusters = await story_cluster_repo.list_all(limit=200)
                    trends = await trend_repo.list_recent(since=started_at, limit=200)
                    relationships = await relationship_repo.list_recent(limit=500)
                    conflicts = await conflict_repo.list_recent(limit=500)

                    articles_by_cluster: dict[str, list[Any]] = {}
                    for cluster in clusters:
                        cluster_articles = await article_repo.list_by_cluster_id(
                            cluster_id=cluster.id, limit=200
                        )
                        articles_by_cluster[str(cluster.id)] = cluster_articles

                    evidence_by_claim: dict[str, list[Any]] = {}
                    conflicts_by_claim: dict[str, list[Any]] = {}
                    for claim in claims:
                        claim_evidence = await claim_repo.list_evidence_by_claim_id(claim.id)
                        evidence_by_claim[str(claim.id)] = claim_evidence

                    claim_ids = {str(c.id) for c in claims}
                    for conflict in conflicts:
                        if str(getattr(conflict, "claim_a_id", "")) in claim_ids:
                            conflicts_by_claim.setdefault(
                                str(conflict.claim_a_id), []
                            ).append(conflict)
                        if str(getattr(conflict, "claim_b_id", "")) in claim_ids:
                            conflicts_by_claim.setdefault(
                                str(conflict.claim_b_id), []
                            ).append(conflict)

                    metrics.extend(await self.evaluate_articles(articles))
                    metrics.extend(
                        await self.evaluate_claims(
                            claims, evidence_by_claim, conflicts_by_claim
                        )
                    )
                    metrics.extend(
                        await self.evaluate_story_clusters(
                            clusters, articles_by_cluster
                        )
                    )
                    metrics.extend(await self.evaluate_trends(trends))
                    metrics.extend(await self.evaluate_relationships(relationships))
                    metrics.extend(await self.evaluate_extraction(articles))

                    if self._settings.ai_enabled:
                        from ai_news_digest.application.ai.benchmark.runner import (
                            BenchmarkExecutionConfig,
                        )
                        from ai_news_digest.application.ai.benchmark.service import BenchmarkService

                        provider_manager = container.provider_manager
                        registry = container.provider_registry

                        benchmark_service = BenchmarkService(
                            provider_manager=provider_manager,
                            registry=registry,
                            config=BenchmarkExecutionConfig(
                                max_cases=5,
                                max_tasks=3,
                                max_total_requests=10,
                            ),
                        )
                        try:
                            benchmark_run = await benchmark_service.run_benchmark()
                            for result in benchmark_run.results:
                                if result.failure is None:
                                    metrics.append(
                                        MetricValue(
                                            metric_type=EvaluationMetricType.PROVIDER_VALIDITY,
                                            value=(
                                                result.quality_score.score
                                                if result.quality_score
                                                else 0.0
                                            ),
                                            sample_count=1,
                                            provider=result.provider_id,
                                            model=result.model,
                                            metadata={
                                                "case_id": result.case_id,
                                                "task": result.task.value,
                                            },
                                        )
                                    )
                        except Exception as bench_exc:
                            logger.warning("Benchmark integration failed", error=str(bench_exc))
                except Exception as repo_exc:
                    logger.warning("Repository evaluation failed", error=str(repo_exc))
                    error = str(repo_exc)

        except Exception as exc:
            logger.error("Evaluation failed", error=str(exc))
            error = str(exc)

        completed_at = datetime.now(UTC)
        status = EvaluationStatus.FAILED if error else EvaluationStatus.COMPLETED

        total_sample_count = sum(m.sample_count for m in metrics)
        overall_value = (
            sum(m.value for m in metrics) / len(metrics)
            if metrics else 0.0
        )
        if overall_value > 0:
            metrics.insert(0, MetricValue(
                metric_type=EvaluationMetricType.OVERALL_QUALITY,
                value=overall_value,
                sample_count=total_sample_count,
            ))

        return EvaluationReport(
            run_id=run_id,
            started_at=started_at,
            completed_at=completed_at,
            status=status,
            evaluation_type=evaluation_type,
            scope=scope,
            dataset_version="production",
            benchmark_version="m93-v1",
            configuration_version="v1",
            metrics=metrics,
            sample_count=total_sample_count,
            provider=None,
            model=None,
            prompt_version=None,
            schema_version="v1",
            drift_signals=[],
            error=error,
        )

    def create_snapshot(
        self,
        report: EvaluationReport,
    ) -> QualitySnapshot:
        """Create a quality snapshot from an evaluation report."""
        return QualitySnapshot(
            snapshot_id=f"snap-{report.run_id}",
            evaluated_at=report.completed_at or report.started_at,
            scope=report.scope,
            metrics=[
                MetricValue(
                    metric_type=m.metric_type,
                    value=m.value,
                    sample_count=m.sample_count,
                    metadata=m.metadata,
                )
                for m in report.metrics
            ],
            sample_count=report.sample_count,
            provider=report.provider,
            model=report.model,
            dataset_version=report.dataset_version,
            benchmark_version=report.benchmark_version,
            configuration_version=report.configuration_version,
        )

    def get_metric_by_type(
        self,
        metrics: list[MetricValue],
        metric_type: EvaluationMetricType,
    ) -> MetricValue | None:
        """Find a metric by type."""
        for m in metrics:
            if m.metric_type == metric_type:
                return m
        return None


__all__ = ["IntelligenceEvaluationService"]
