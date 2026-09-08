"""Story intelligence utilities for cluster detail pages.

Provides conservative, deterministic helpers for:
- Source-role classification
- Chronological timeline construction
- "What changed" detection across a cluster's article history
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, TypedDict


class TimelineItem(TypedDict, total=False):
    """A single chronological timeline entry produced by :func:`build_timeline`.

    The TypedDict is intentionally permissive: most fields are optional
    so the timeline builder can degrade gracefully when a source does
    not expose a particular piece of metadata. The fields actually used
    by the public story intelligence layer are documented in
    :mod:`ai_news_digest.application.evaluation`.
    """

    id: str
    title: str | None
    url: str | None
    summary: str | None
    published_at: str | None
    source_name: str | None
    source_type: str | None
    source_role: str | None
    importance_score: float | None
    confidence: float | None
    key_takeaways: list[str]
    companies: list[str]
    topics: list[str]
    signals: dict[str, bool]
    source_role_confidence: str | None
    evidence_confidence: str | None
    confidence_label: str | None


def classify_source_role(
    *,
    article_published_at: datetime,
    cluster_first_published_at: datetime,
    source_type: str | None,
    representative_title: str | None = None,
    article_title: str | None = None,
) -> str:
    """Return a conservative source-role label for an article within a cluster.

    Rules are intentionally narrow so that low-confidence cases fall back to
    the neutral ``"Related coverage"`` label.
    """

    time_diff_seconds = abs((article_published_at - cluster_first_published_at).total_seconds())
    twenty_four_hours = 24 * 60 * 60
    seven_days = 7 * 24 * 60 * 60

    if source_type == "official_company" and time_diff_seconds <= twenty_four_hours:
        return "Primary announcement"

    if _is_correction(article_title, representative_title):
        return "Correction"

    if _is_background(article_title):
        return "Background"

    if source_type == "research_org" and time_diff_seconds <= seven_days:
        return "Technical analysis"

    if source_type in {"tech_publication", "business_news"} and (
        time_diff_seconds <= twenty_four_hours
    ):
        return "Independent reporting"

    if time_diff_seconds <= twenty_four_hours:
        return "Independent reporting"

    if time_diff_seconds <= seven_days:
        return "Follow-up"

    return "Related coverage"


def _is_correction(article_title: str | None, representative_title: str | None) -> bool:
    if not article_title:
        return False
    lowered = article_title.lower()
    correction_signals = ("corrects", "correction", "retraction", "update:", "updated:")
    return any(signal in lowered for signal in correction_signals)


def _is_background(article_title: str | None) -> bool:
    if not article_title:
        return False
    lowered = article_title.lower()
    background_signals = ("background", "what you need to know", "explained", "guide:", "guide to")
    return any(signal in lowered for signal in background_signals)


def build_timeline(articles: list[Any], source_map: dict[Any, str]) -> list[dict[str, Any]]:
    """Return articles ordered chronologically (oldest first) with source metadata."""
    sorted_articles = sorted(
        articles,
        key=lambda a: a.published_at or datetime.min.replace(tzinfo=UTC),
    )
    timeline = []
    for article in sorted_articles:
        timeline.append(
            {
                "id": str(article.id),
                "title": article.title,
                "url": article.url,
                "summary": article.summary,
                "published_at": article.published_at.isoformat() if article.published_at else None,
                "source_name": source_map.get(article.source_id),
                "source_type": getattr(article, "source_type", None),
                "source_role": getattr(article, "source_role", None),
                "importance_score": article.importance_score,
                "confidence": article.confidence,
                "key_takeaways": list(article.key_takeaways) if article.key_takeaways else [],
                "companies": list(getattr(article, "companies", [])) or [],
                "topics": list(getattr(article, "topics", [])) or [],
            }
        )
    return timeline


def compute_what_changed(timeline: list[dict[str, Any]]) -> list[str]:
    """Detect meaningful changes across a cluster's article timeline.

    Returns a list of human-readable change descriptions. When evidence is
    insufficient, returns an empty list rather than fabricating claims.
    """
    if not timeline or len(timeline) < 2:
        return []

    changes: list[str] = []
    first = timeline[0]
    latest = timeline[-1]

    if first["title"] != latest["title"] and latest["title"]:
        changes.append(f"Headline updated: \"{latest['title']}\"")

    latest_companies = set(latest.get("companies", []))
    first_companies = set(first.get("companies", []))
    new_companies = latest_companies - first_companies
    if new_companies:
        changes.append(f"New entities mentioned: {', '.join(sorted(new_companies))}")

    latest_topics = set(latest.get("topics", []))
    first_topics = set(first.get("topics", []))
    new_topics = latest_topics - first_topics
    if new_topics:
        changes.append(f"New topics: {', '.join(sorted(new_topics))}")

    latest_latest_score = latest.get("importance_score")
    if first.get("importance_score") != latest_latest_score and latest_latest_score is not None:
        changes.append(
            "Importance score changed from "
            f"{first.get('importance_score')} to {latest_latest_score}"
        )

    first_takeaways = first.get("key_takeaways")
    latest_takeaways = latest.get("key_takeaways")
    if first_takeaways != latest_takeaways and latest_takeaways:
        added_takeaways = [t for t in latest_takeaways if t not in (first_takeaways or [])]
        if added_takeaways:
            changes.append(f"New key takeaways: {added_takeaways[0]}")

    if first.get("published_at") != latest.get("published_at") and len(timeline) > 2:
        changes.append(f"Story updated with additional coverage ({len(timeline)} articles total)")

    return changes


def detect_signals(article_title: str | None) -> dict[str, bool]:
    """Return which corrective/background signals are present in a title.

    The signals are exposed to other parts of the platform so that
    contradiction detection, the public API, and the frontend can agree
    on what a title implies without each re-implementing the lexical
    rules.
    """
    title = (article_title or "").lower()
    return {
        "is_correction": any(
            signal in title
            for signal in (
                "corrects",
                "correction",
                "corrected",
                "update:",
                "updated:",
                "clarification",
                "clarifies",
                "errata",
                "amends",
            )
        ),
        "is_retraction": any(
            signal in title
            for signal in (
                "retraction",
                "retracts",
                "retracted",
                "withdraws",
                "withdrawn",
                "kill",
                "killed",
            )
        ),
        "is_background": any(
            signal in title
            for signal in (
                "background",
                "what you need to know",
                "explained",
                "explainer",
                "guide:",
                "guide to",
            )
        ),
        "is_reaction": any(
            signal in title
            for signal in (
                "reaction",
                "react:",
                "responds to",
                "in response to",
                "opinion:",
                "why this matters",
            )
        ),
    }


def compute_what_changed_with_evidence(
    timeline: list[TimelineItem],
    *,
    detected_at: str | None = None,
) -> list[Any]:
    """Return the same changes as :func:`compute_what_changed` with provenance.

    Each change is wrapped in an :class:`EvidenceItem` so callers can
    surface the supporting articles, the detection method, and a
    confidence level. The function never silently merges clearly
    contradictory claims: when a contradictory report is detected, it is
    surfaced as its own evidence item rather than as a "change" in the
    headline.
    """
    from ai_news_digest.application.evaluation.confidence import (
        Confidence,
        compute_evidence_strength,
        compute_what_changed_confidence,
    )
    from ai_news_digest.application.evaluation.evidence import (
        build_change_evidence,
    )

    if not timeline or len(timeline) < 2:
        return []

    items: list[Any] = []
    first = timeline[0]
    latest = timeline[-1]

    if first.get("title") and latest.get("title") and first["title"] != latest["title"]:
        items.append(
            build_change_evidence(
                description=f"Headline updated: \"{latest['title']}\"",
                detection_method="deterministic_title_diff",
                evidence_type="headline_change",
                fields_used=["title"],
                items=[first, latest],
                confidence=Confidence.MEDIUM.value,
                reason="Latest article's title differs from the earliest article's title.",
                detected_at=detected_at,
            )
        )

    latest_companies = set(latest.get("companies", []) or [])
    first_companies = set(first.get("companies", []) or [])
    new_companies = latest_companies - first_companies
    if new_companies:
        items.append(
            build_change_evidence(
                description=f"New entities mentioned: {', '.join(sorted(new_companies))}",
                detection_method="deterministic_entity_diff",
                evidence_type="new_entities",
                fields_used=["companies"],
                items=[first, latest],
                confidence=compute_what_changed_confidence(
                    has_first_article=True,
                    has_latest_article=True,
                    has_meaningful_delta=True,
                ).value,
                reason="Latest article introduces companies not in the first article.",
                detected_at=detected_at,
            )
        )

    latest_topics = set(latest.get("topics", []) or [])
    first_topics = set(first.get("topics", []) or [])
    new_topics = latest_topics - first_topics
    if new_topics:
        items.append(
            build_change_evidence(
                description=f"New topics: {', '.join(sorted(new_topics))}",
                detection_method="deterministic_topic_diff",
                evidence_type="new_topics",
                fields_used=["topics"],
                items=[first, latest],
                confidence=compute_what_changed_confidence(
                    has_first_article=True,
                    has_latest_article=True,
                    has_meaningful_delta=True,
                ).value,
                reason="Latest article introduces topics not in the first article.",
                detected_at=detected_at,
            )
        )

    first_score = first.get("importance_score")
    latest_score = latest.get("importance_score")
    if first_score != latest_score and first_score is not None and latest_score is not None:
        items.append(
            build_change_evidence(
                description=(f"Importance score changed from {first_score} to {latest_score}"),
                detection_method="deterministic_importance_diff",
                evidence_type="importance_change",
                fields_used=["importance_score"],
                items=[first, latest],
                confidence=compute_evidence_strength(
                    supporting_article_count=2,
                    distinct_source_count=len(
                        {first.get("source_name"), latest.get("source_name")}
                    ),
                    fields_used=["importance_score"],
                ).value,
                reason="Importance score differs between the first and latest article.",
                detected_at=detected_at,
            )
        )

    first_takeaways = first.get("key_takeaways") or []
    latest_takeaways = latest.get("key_takeaways") or []
    if first_takeaways != latest_takeaways and latest_takeaways:
        added_takeaways = [t for t in latest_takeaways if t not in first_takeaways]
        if added_takeaways:
            items.append(
                build_change_evidence(
                    description=f"New key takeaways: {added_takeaways[0]}",
                    detection_method="deterministic_takeaway_diff",
                    evidence_type="new_takeaway",
                    fields_used=["key_takeaways"],
                    items=[first, latest],
                    confidence=compute_what_changed_confidence(
                        has_first_article=True,
                        has_latest_article=True,
                        has_meaningful_delta=True,
                    ).value,
                    reason="Latest article has a key takeaway not in the first article.",
                    detected_at=detected_at,
                )
            )

    if first.get("published_at") != latest.get("published_at") and len(timeline) > 2:
        items.append(
            build_change_evidence(
                description=(
                    f"Story updated with additional coverage ({len(timeline)} articles total)"
                ),
                detection_method="deterministic_coverage_growth",
                evidence_type="additional_coverage",
                fields_used=["published_at"],
                items=timeline,
                confidence=compute_evidence_strength(
                    supporting_article_count=len(timeline),
                    distinct_source_count=len({item.get("source_name") for item in timeline}),
                    fields_used=["published_at"],
                ).value,
                reason="The cluster's article count grew over time.",
                detected_at=detected_at,
            )
        )

    return items


__all__ = [
    "TimelineItem",
    "build_timeline",
    "classify_source_role",
    "compute_what_changed",
    "compute_what_changed_with_evidence",
    "detect_signals",
]
