from __future__ import annotations

from enum import Enum
from typing import Any


class Confidence(str, Enum):
    """Confidence levels for story intelligence detections."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


def compute_evidence_strength(
    *,
    supporting_article_count: int,
    distinct_source_count: int,
    fields_used: list[str],
) -> Confidence:
    """Placeholder strength estimator for evidence bundles."""
    if supporting_article_count >= 2 and distinct_source_count >= 2:
        return Confidence.HIGH
    if supporting_article_count >= 1 and distinct_source_count >= 1:
        return Confidence.MEDIUM
    return Confidence.LOW


def compute_what_changed_confidence(
    *,
    has_first_article: bool,
    has_latest_article: bool,
    has_meaningful_delta: bool,
) -> Confidence:
    """Return a confidence label for a what-changed detection."""
    if has_first_article and has_latest_article and has_meaningful_delta:
        return Confidence.HIGH
    if has_first_article or has_latest_article:
        return Confidence.MEDIUM
    return Confidence.LOW


def compute_source_role_confidence(
    *,
    has_source_type: bool,
    has_representative_title: bool,
    is_correction_signal: bool,
    is_background_signal: bool,
    is_primary_window: bool,
    is_tech_or_business_window: bool,
) -> Confidence:
    """Return a confidence label for a source-role classification."""
    if is_correction_signal or is_primary_window:
        return Confidence.HIGH
    if is_tech_or_business_window and has_source_type:
        return Confidence.MEDIUM
    if is_background_signal or not has_source_type:
        return Confidence.LOW
    return Confidence.MEDIUM


def aggregate_article_confidence(timeline: list[Any]) -> Confidence:
    """Return a representative confidence label for a cluster timeline."""
    if not timeline:
        return Confidence.LOW
    return Confidence.MEDIUM


def compute_cluster_confidence(
    *,
    article_count: int,
    unique_source_count: int,
    average_article_confidence: Confidence,
) -> Confidence:
    """Return a cluster-level confidence label."""
    if article_count >= 5 and unique_source_count >= 3:
        return Confidence.HIGH
    if article_count >= 2 and unique_source_count >= 2:
        return Confidence.MEDIUM
    return Confidence.LOW
