"""
Claim candidate generation for cross-source conflict detection (M82).

Provides bounded candidate-pair generation based on entity overlap,
temporal proximity, and claim-type compatibility.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from ai_news_digest.application.evaluation.claim_normalizer import (
    normalize_claim_text,
)
from ai_news_digest.domain.enums.claim_type import ClaimType
from ai_news_digest.domain.models.claim import Claim

if TYPE_CHECKING:
    from ai_news_digest.domain.models.article import Article
    from ai_news_digest.domain.models.source import Source


@dataclass(slots=True)
class ClaimContext:
    """Enriched claim context for comparison."""

    claim: Claim
    article: Article
    source: Source
    company_ids: frozenset[str]
    topic_ids: frozenset[str]
    normalized_tokens: frozenset[str]
    claim_type_group: str


@dataclass(slots=True)
class ConflictCandidate:
    """A pair of claims that may be in conflict."""

    claim_a: Claim
    claim_b: Claim
    article_a: Article
    article_b: Article
    source_a: Source
    source_b: Source
    company_overlap: frozenset[str]
    topic_overlap: frozenset[str]
    temporal_compatible: bool
    same_source: bool
    detection_version: str


def _extract_tokens(text: str) -> frozenset[str]:
    """Extract meaningful tokens from text for overlap comparison."""
    normalized = normalize_claim_text(text)
    tokens = re.findall(r"[a-z0-9]+", normalized)
    stop_words = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "can", "shall", "to", "of", "in", "for",
        "on", "with", "at", "by", "from", "as", "into", "about", "through",
        "during", "before", "after", "above", "below", "between", "out",
        "off", "over", "under", "again", "further", "then", "once", "here",
        "there", "when", "where", "why", "how", "all", "each", "every",
        "both", "few", "more", "most", "other", "some", "such", "no", "nor",
        "not", "only", "own", "same", "so", "than", "too", "very", "just",
        "because", "but", "and", "or", "if", "while", "that", "this",
        "it", "its", "he", "she", "they", "them", "his", "her", "their",
    }
    return frozenset(t for t in tokens if t not in stop_words and len(t) > 2)


def _get_claim_type_group(claim_type: ClaimType) -> str:
    """Map claim types to broader groups for compatibility checks."""
    quantitative_types = {ClaimType.QUANTITATIVE, ClaimType.FACT}
    event_types = {ClaimType.EVENT, ClaimType.ANNOUNCEMENT, ClaimType.BUSINESS}
    product_types = {ClaimType.PRODUCT, ClaimType.RESEARCH}
    company_types = {ClaimType.COMPANY}
    policy_types = {ClaimType.POLICY}

    if claim_type in quantitative_types:
        return "quantitative"
    if claim_type in event_types:
        return "event"
    if claim_type in product_types:
        return "product"
    if claim_type in company_types:
        return "company"
    if claim_type in policy_types:
        return "policy"
    return "general"


def _temporal_compatible(
    article_a: Article,
    article_b: Article,
    window_hours: float = 72.0,
) -> bool:
    """Return True if two articles are temporally compatible for comparison.

    Articles within the window are considered potentially about the same
    event stage. Articles far apart in time may describe different stages
    of an evolving situation.
    """
    delta = abs((article_a.published_at - article_b.published_at).total_seconds())
    return delta <= window_hours * 3600


def build_claim_contexts(
    claims: list[Claim],
    articles: dict[UUID, Article],
    sources: dict[UUID, Source],
    company_ids_by_article: dict[UUID, frozenset[str]],
    topic_ids_by_article: dict[UUID, frozenset[str]],
) -> list[ClaimContext]:
    """Build enriched ClaimContext objects for a list of claims."""
    contexts: list[ClaimContext] = []
    for claim in claims:
        article = articles.get(claim.article_id)
        source = sources.get(claim.source_id)
        if article is None or source is None:
            continue
        company_ids = company_ids_by_article.get(claim.article_id, frozenset())
        topic_ids = topic_ids_by_article.get(claim.article_id, frozenset())
        tokens = _extract_tokens(claim.claim_text)
        claim_type_group = _get_claim_type_group(claim.claim_type)
        contexts.append(
            ClaimContext(
                claim=claim,
                article=article,
                source=source,
                company_ids=company_ids,
                topic_ids=topic_ids,
                normalized_tokens=tokens,
                claim_type_group=claim_type_group,
            )
        )
    return contexts


def generate_candidates(
    contexts: list[ClaimContext],
    *,
    max_candidates_per_claim: int = 10,
    max_total_candidates: int = 200,
    temporal_window_hours: float = 72.0,
    detection_version: str = "v1",
) -> list[ConflictCandidate]:
    """Generate bounded candidate conflict pairs from claim contexts.

    Filters:
    - Same claim type group (quantitative with quantitative, event with event)
    - Entity overlap (company or topic)
    - Temporal proximity
    - Not the same claim
    - Bounded output
    """
    if not contexts:
        return []

    candidates: list[ConflictCandidate] = []
    seen_pairs: set[frozenset[str]] = set()

    compatible_type_groups = {
        "quantitative": {"quantitative"},
        "event": {"event", "announcement"},
        "product": {"product", "research"},
        "company": {"company", "event"},
        "policy": {"policy"},
        "general": {"general", "other"},
    }

    for i, ctx_a in enumerate(contexts):
        count_for_a = 0
        for ctx_b in contexts[i + 1:]:
            if len(candidates) >= max_total_candidates:
                break
            if count_for_a >= max_candidates_per_claim:
                break

            claim_a = ctx_a.claim
            claim_b = ctx_b.claim
            if claim_a.id == claim_b.id:
                continue

            pair_key = frozenset([str(claim_a.id), str(claim_b.id)])
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)

            compatible_groups = compatible_type_groups.get(
                ctx_a.claim_type_group, {ctx_a.claim_type_group}
            )
            if ctx_b.claim_type_group not in compatible_groups:
                continue

            company_overlap = ctx_a.company_ids & ctx_b.company_ids
            topic_overlap = ctx_a.topic_ids & ctx_b.topic_ids
            if not company_overlap and not topic_overlap:
                continue

            token_overlap = ctx_a.normalized_tokens & ctx_b.normalized_tokens
            if not token_overlap and not company_overlap:
                continue

            temporal_ok = _temporal_compatible(
                ctx_a.article, ctx_b.article, window_hours=temporal_window_hours
            )
            if not temporal_ok:
                continue

            same_source = ctx_a.source.id == ctx_b.source.id

            candidates.append(
                ConflictCandidate(
                    claim_a=claim_a,
                    claim_b=claim_b,
                    article_a=ctx_a.article,
                    article_b=ctx_b.article,
                    source_a=ctx_a.source,
                    source_b=ctx_b.source,
                    company_overlap=company_overlap,
                    topic_overlap=topic_overlap,
                    temporal_compatible=temporal_ok,
                    same_source=same_source,
                    detection_version=detection_version,
                )
            )
            count_for_a += 1

        if len(candidates) >= max_total_candidates:
            break

    return candidates


__all__ = [
    "ClaimContext",
    "ConflictCandidate",
    "build_claim_contexts",
    "generate_candidates",
]
