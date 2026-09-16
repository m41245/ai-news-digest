"""
Intelligence quality assessment service for M92.

Provides deterministic quality diagnostics for intelligence entities.
Does not modify truth claims or fabricate intelligence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from ai_news_digest.domain.models.relationship import ProvenanceSource


class QualityFlag(StrEnum):
    """Bounded set of quality flags for intelligence entities."""

    MISSING_EVIDENCE = "missing_evidence"
    LOW_SOURCE_DIVERSITY = "low_source_diversity"
    CONFLICTING_EVIDENCE = "conflicting_evidence"
    STALE_INTELLIGENCE = "stale_intelligence"
    AI_METADATA_MISSING = "ai_metadata_missing"
    INCOMPLETE_PROVENANCE = "incomplete_provenance"
    UNVERIFIED_CLAIM = "unverified_claim"
    SINGLE_SOURCE = "single_source"
    LOW_CONFIDENCE = "low_confidence"
    HIGH_CONFLICT = "high_conflict"


@dataclass(slots=True)
class QualityResult:
    """Quality assessment result for an intelligence entity."""

    entity_type: str
    entity_id: str
    flags: list[str] = field(default_factory=list)
    evidence_count: int = 0
    source_count: int = 0
    independent_source_count: int = 0
    conflict_present: bool = False
    conflict_count: int = 0
    provenance_complete: bool = True
    freshness: str = "unknown"
    overall_score: float = 0.0
    explanation: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class IntelligenceQualityService:
    """Deterministic quality assessment for intelligence entities.

    This service is pure: it inspects provided data and returns diagnostics.
    It never modifies truth claims, never fabricates intelligence, and
    respects AI_ENABLED=false by operating solely on persisted data.
    """

    STALE_THRESHOLD_HOURS: float = 168.0
    LOW_DIVERSITY_THRESHOLD: int = 2
    HIGH_CONFLICT_THRESHOLD: int = 2
    LOW_CONFIDENCE_THRESHOLD: float = 0.4

    def evaluate_claim(
        self,
        claim: Any,
        evidence_items: list[Any] | None = None,
        conflicts: list[Any] | None = None,
        now: datetime | None = None,
    ) -> QualityResult:
        """Evaluate the quality of a claim."""
        if now is None:
            now = datetime.now(UTC)

        evidence = evidence_items or []
        conflict_list = conflicts or []

        evidence_count = len(evidence)
        source_ids = {getattr(e, "source_location", None) for e in evidence}
        source_ids.discard(None)
        source_count = len(source_ids)

        flags: list[str] = []
        if evidence_count == 0:
            flags.append(QualityFlag.MISSING_EVIDENCE.value)
        if source_count <= 1:
            flags.append(QualityFlag.SINGLE_SOURCE.value)
        if source_count < self.LOW_DIVERSITY_THRESHOLD:
            flags.append(QualityFlag.LOW_SOURCE_DIVERSITY.value)
        if len(conflict_list) > 0:
            flags.append(QualityFlag.CONFLICTING_EVIDENCE.value)
        confidence = getattr(claim, "confidence", None)
        if confidence is not None and confidence < self.LOW_CONFIDENCE_THRESHOLD:
            flags.append(QualityFlag.LOW_CONFIDENCE.value)
        status = getattr(claim, "status", None)
        if status and str(status.value if hasattr(status, "value") else status) == "unverified":
            flags.append(QualityFlag.UNVERIFIED_CLAIM.value)

        ai_provider = getattr(claim, "ai_provider", None)
        ai_model = getattr(claim, "ai_model", None)
        if (ai_provider or ai_model) and (not ai_provider or not ai_model):
            flags.append(QualityFlag.AI_METADATA_MISSING.value)

        created_at = getattr(claim, "created_at", None)
        if created_at and (now - created_at).total_seconds() > self.STALE_THRESHOLD_HOURS * 3600:
            flags.append(QualityFlag.STALE_INTELLIGENCE.value)

        overall_score = self._compute_overall_score(
            evidence_count=evidence_count,
            source_count=source_count,
            conflict_count=len(conflict_list),
            confidence=confidence,
        )

        explanation_parts = []
        if evidence_count == 0:
            explanation_parts.append("No evidence attached")
        elif evidence_count == 1:
            explanation_parts.append("1 piece of evidence")
        else:
            explanation_parts.append(f"{evidence_count} pieces of evidence")
        if source_count > 1:
            explanation_parts.append(f"{source_count} independent sources")
        if len(conflict_list) > 0:
            explanation_parts.append(f"{len(conflict_list)} conflict(s)")
        explanation = "; ".join(explanation_parts) if explanation_parts else "No quality signals"

        return QualityResult(
            entity_type="claim",
            entity_id=str(getattr(claim, "id", "")),
            flags=flags,
            evidence_count=evidence_count,
            source_count=source_count,
            independent_source_count=source_count,
            conflict_present=len(conflict_list) > 0,
            conflict_count=len(conflict_list),
            provenance_complete=not any(
                f
                in (
                    QualityFlag.AI_METADATA_MISSING.value,
                    QualityFlag.INCOMPLETE_PROVENANCE.value,
                )
                for f in flags
            ),
            freshness=self._compute_freshness(created_at, now),
            overall_score=overall_score,
            explanation=explanation,
        )

    def evaluate_evidence(
        self,
        evidence: Any,
        claim_count: int = 0,
        now: datetime | None = None,
    ) -> QualityResult:
        """Evaluate the quality of an evidence item."""
        if now is None:
            now = datetime.now(UTC)

        flags: list[str] = []
        if claim_count == 0:
            flags.append(QualityFlag.MISSING_EVIDENCE.value)

        created_at = getattr(evidence, "created_at", None)
        if created_at and (now - created_at).total_seconds() > self.STALE_THRESHOLD_HOURS * 3600:
            flags.append(QualityFlag.STALE_INTELLIGENCE.value)

        article_id = getattr(evidence, "article_id", None)
        provenance_complete = article_id is not None

        overall_score = self._compute_overall_score(
            evidence_count=claim_count,
            source_count=1 if article_id else 0,
            conflict_count=0,
            confidence=None,
        )

        explanation = f"Supports {claim_count} claim(s)"
        if not provenance_complete:
            explanation += "; missing article provenance"

        return QualityResult(
            entity_type="evidence",
            entity_id=str(getattr(evidence, "id", "")),
            flags=flags,
            evidence_count=claim_count,
            source_count=1 if article_id else 0,
            independent_source_count=1 if article_id else 0,
            provenance_complete=provenance_complete,
            freshness=self._compute_freshness(created_at, now),
            overall_score=overall_score,
            explanation=explanation,
        )

    def evaluate_relationship(
        self,
        relationship: Any,
        now: datetime | None = None,
    ) -> QualityResult:
        """Evaluate the quality of a relationship."""
        if now is None:
            now = datetime.now(UTC)

        flags: list[str] = []
        status = getattr(relationship, "status", None)
        status_value = (
            str(status.value if hasattr(status, "value") else status)
            if status
            else "candidate"
        )
        if status_value in ("disputed",):
            flags.append(QualityFlag.CONFLICTING_EVIDENCE.value)
        if status_value in ("retracted", "inactive"):
            flags.append(QualityFlag.CONFLICTING_EVIDENCE.value)

        source_count = getattr(relationship, "source_count", 1) or 1
        if source_count <= 1:
            flags.append(QualityFlag.SINGLE_SOURCE.value)
        if source_count < self.LOW_DIVERSITY_THRESHOLD:
            flags.append(QualityFlag.LOW_SOURCE_DIVERSITY.value)

        confidence = getattr(relationship, "confidence", None)
        if confidence is not None and confidence < self.LOW_CONFIDENCE_THRESHOLD:
            flags.append(QualityFlag.LOW_CONFIDENCE.value)

        provenance = getattr(relationship, "provenance_source", ProvenanceSource.DETERMINISTIC)
        if (
            provenance == ProvenanceSource.AI_EXTRACTED
            and (
                not getattr(relationship, "ai_provider", None)
                or not getattr(relationship, "ai_model", None)
            )
        ):
            flags.append(QualityFlag.AI_METADATA_MISSING.value)

        last_observed = getattr(relationship, "last_observed_at", None)
        stale_threshold_seconds = self.STALE_THRESHOLD_HOURS * 3600
        if last_observed and (now - last_observed).total_seconds() > stale_threshold_seconds:
            flags.append(QualityFlag.STALE_INTELLIGENCE.value)

        overall_score = self._compute_overall_score(
            evidence_count=source_count,
            source_count=source_count,
            conflict_count=1 if status_value == "disputed" else 0,
            confidence=confidence,
        )

        explanation_parts = []
        if status_value == "verified":
            explanation_parts.append("Verified relationship")
        elif status_value == "disputed":
            explanation_parts.append("Disputed relationship")
        elif status_value == "candidate":
            explanation_parts.append("Candidate relationship")
        else:
            explanation_parts.append(f"{status_value} relationship")
        if source_count > 1:
            explanation_parts.append(f"{source_count} sources")
        explanation = "; ".join(explanation_parts)

        return QualityResult(
            entity_type="relationship",
            entity_id=str(getattr(relationship, "id", "")),
            flags=flags,
            source_count=source_count,
            independent_source_count=source_count,
            conflict_present=status_value == "disputed",
            conflict_count=1 if status_value == "disputed" else 0,
            provenance_complete=not any(
                f == QualityFlag.AI_METADATA_MISSING.value for f in flags
            ),
            freshness=self._compute_freshness(last_observed, now),
            overall_score=overall_score,
            explanation=explanation,
            metadata={"status": status_value},
        )

    def evaluate_story_cluster(
        self,
        cluster: Any,
        article_count: int = 0,
        source_count: int = 0,
        evidence_count: int = 0,
        conflict_count: int = 0,
        now: datetime | None = None,
    ) -> QualityResult:
        """Evaluate the quality of a story cluster."""
        if now is None:
            now = datetime.now(UTC)

        flags: list[str] = []
        if article_count == 0:
            flags.append(QualityFlag.MISSING_EVIDENCE.value)
        if source_count <= 1:
            flags.append(QualityFlag.SINGLE_SOURCE.value)
        if source_count < self.LOW_DIVERSITY_THRESHOLD:
            flags.append(QualityFlag.LOW_SOURCE_DIVERSITY.value)
        if conflict_count > self.HIGH_CONFLICT_THRESHOLD:
            flags.append(QualityFlag.HIGH_CONFLICT.value)
        if conflict_count > 0:
            flags.append(QualityFlag.CONFLICTING_EVIDENCE.value)

        last_updated = getattr(cluster, "last_updated_at", None)
        stale_threshold_seconds = self.STALE_THRESHOLD_HOURS * 3600
        if last_updated and (now - last_updated).total_seconds() > stale_threshold_seconds:
            flags.append(QualityFlag.STALE_INTELLIGENCE.value)

        confidence = getattr(cluster, "confidence", None)
        if confidence is not None and confidence < self.LOW_CONFIDENCE_THRESHOLD:
            flags.append(QualityFlag.LOW_CONFIDENCE.value)

        overall_score = self._compute_overall_score(
            evidence_count=article_count,
            source_count=source_count,
            conflict_count=conflict_count,
            confidence=confidence,
        )

        explanation_parts = []
        explanation_parts.append(f"{article_count} article(s)")
        if source_count > 1:
            explanation_parts.append(f"{source_count} independent sources")
        if conflict_count > 0:
            explanation_parts.append(f"{conflict_count} conflict(s)")
        explanation = "; ".join(explanation_parts)

        return QualityResult(
            entity_type="story_cluster",
            entity_id=str(getattr(cluster, "id", "")),
            flags=flags,
            evidence_count=article_count,
            source_count=source_count,
            independent_source_count=source_count,
            conflict_present=conflict_count > 0,
            conflict_count=conflict_count,
            provenance_complete=article_count > 0,
            freshness=self._compute_freshness(last_updated, now),
            overall_score=overall_score,
            explanation=explanation,
        )

    def evaluate_trend(
        self,
        trend: Any,
        now: datetime | None = None,
    ) -> QualityResult:
        """Evaluate the quality of a trend."""
        if now is None:
            now = datetime.now(UTC)

        flags: list[str] = []
        source_count = getattr(trend, "source_count", 0) or 0
        story_count = getattr(trend, "story_count", 0) or 0
        if source_count <= 1:
            flags.append(QualityFlag.SINGLE_SOURCE.value)
        if source_count < self.LOW_DIVERSITY_THRESHOLD:
            flags.append(QualityFlag.LOW_SOURCE_DIVERSITY.value)

        last_detected = getattr(trend, "last_detected_at", None)
        stale_threshold_seconds = self.STALE_THRESHOLD_HOURS * 3600
        if last_detected and (now - last_detected).total_seconds() > stale_threshold_seconds:
            flags.append(QualityFlag.STALE_INTELLIGENCE.value)

        overall_score = self._compute_overall_score(
            evidence_count=story_count,
            source_count=source_count,
            conflict_count=0,
            confidence=None,
        )

        explanation_parts = []
        explanation_parts.append(f"{source_count} source(s)")
        explanation_parts.append(f"{story_count} story(ies)")
        explanation = "; ".join(explanation_parts)

        return QualityResult(
            entity_type="trend",
            entity_id=str(getattr(trend, "id", "")),
            flags=flags,
            evidence_count=story_count,
            source_count=source_count,
            independent_source_count=source_count,
            provenance_complete=source_count > 0,
            freshness=self._compute_freshness(last_detected, now),
            overall_score=overall_score,
            explanation=explanation,
        )

    def _compute_overall_score(
        self,
        *,
        evidence_count: int,
        source_count: int,
        conflict_count: int,
        confidence: float | None,
    ) -> float:
        """Compute a normalized overall quality score in [0.0, 1.0]."""
        score = 0.0

        evidence_component = min(1.0, evidence_count / 5.0) * 0.3
        score += evidence_component

        source_component = min(1.0, source_count / 5.0) * 0.3
        score += source_component

        conflict_component = max(0.0, 1.0 - (conflict_count / 3.0)) * 0.2
        score += conflict_component

        if confidence is not None:
            confidence_component = max(0.0, min(1.0, confidence)) * 0.2
            score += confidence_component
        else:
            score += 0.1

        return max(0.0, min(1.0, score))

    def _compute_freshness(self, timestamp: Any, now: datetime) -> str:
        """Compute freshness label from a timestamp."""
        if timestamp is None:
            return "unknown"
        if hasattr(timestamp, "isoformat"):
            timestamp = timestamp
        else:
            return "unknown"

        age_hours = (now - timestamp).total_seconds() / 3600.0
        if age_hours < 1.0:
            return "very_recent"
        if age_hours < 24.0:
            return "recent"
        if age_hours < 168.0:
            return "stale"
        return "very_stale"


__all__ = [
    "IntelligenceQualityService",
    "QualityFlag",
    "QualityResult",
]
