from __future__ import annotations

import contextlib
import hashlib
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from ai_news_digest.core.config import get_settings
from ai_news_digest.core.logging import get_logger
from ai_news_digest.domain.enums.story_event_type import StoryEventType
from ai_news_digest.domain.models.article import Article
from ai_news_digest.domain.models.claim import Claim
from ai_news_digest.domain.models.conflict import Conflict
from ai_news_digest.domain.models.story_event import StoryEvent
from ai_news_digest.domain.ports.article_repository import ArticleRepository
from ai_news_digest.domain.ports.claim_repository import ClaimRepository
from ai_news_digest.domain.ports.conflict_repository import ConflictRepository
from ai_news_digest.domain.ports.story_activity_repository import StoryActivityRepository
from ai_news_digest.domain.ports.story_cluster_repository import StoryClusterRepository
from ai_news_digest.domain.ports.story_event_repository import StoryEventRepository

logger = get_logger(__name__)


def _clamp(value: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
    return max(min_val, min(max_val, value))


def _event_fingerprint(
    event_type: StoryEventType,
    title: str,
    event_time: datetime | None,
) -> str:
    fallback = datetime.min.replace(tzinfo=UTC)
    raw = f"{event_type.value}:{title}:{(event_time or fallback).isoformat()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _group_articles_by_event(
    articles: list[Article],
    max_events: int = 20,
) -> list[tuple[StoryEventType, datetime | None, list[Article]]]:
    if not articles:
        return []
    sorted_articles = sorted(articles, key=lambda a: a.published_at)
    groups: dict[str, list[Article]] = defaultdict(list)
    for article in sorted_articles:
        lowered = article.title.lower()
        event_type = StoryEventType.OTHER
        for candidate in StoryEventType:
            if candidate.value.replace("_", " ") in lowered or candidate.value in lowered:
                event_type = candidate
                break
        key = f"{event_type.value}:{article.published_at.date().isoformat()}"
        groups[key].append(article)
    grouped: list[tuple[StoryEventType, datetime | None, list[Article]]] = []
    for key, group_articles in groups.items():
        event_type_str, date_str = key.split(":", 1)
        event_type = (
            StoryEventType(event_type_str)
            if event_type_str in {e.value for e in StoryEventType}
            else StoryEventType.OTHER
        )
        event_time = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=UTC)
        grouped.append((event_type, event_time, group_articles))
    grouped.sort(key=lambda x: x[1] or datetime.min.replace(tzinfo=UTC))
    return grouped[:max_events]


def _compute_event_confidence(
    article_count: int,
    distinct_source_count: int,
    has_claim_support: bool,
    conflict_count: int = 0,
) -> float:
    source_score = min(distinct_source_count / 3.0, 1.0)
    claim_score = 0.2 if has_claim_support else 0.0
    count_score = min(article_count / 5.0, 1.0)
    penalty = 0.1 * min(conflict_count, 3)
    return _clamp(0.3 * source_score + 0.3 * count_score + 0.2 * claim_score + 0.2 - penalty)


class GenerateStoryTimelineUseCase:
    def __init__(
        self,
        story_cluster_repository: StoryClusterRepository,
        article_repository: ArticleRepository,
        claim_repository: ClaimRepository,
        conflict_repository: ConflictRepository,
        story_activity_repository: StoryActivityRepository,
        story_event_repository: StoryEventRepository,
        provider_manager: Any | None = None,
    ) -> None:
        self._cluster_repo = story_cluster_repository
        self._article_repo = article_repository
        self._claim_repo = claim_repository
        self._conflict_repo = conflict_repository
        self._activity_repo = story_activity_repository
        self._event_repo = story_event_repository
        self._provider_manager = provider_manager
        self._settings = get_settings()
        self._logger = get_logger(__name__)

    async def execute(self, cluster_id: UUID) -> dict[str, Any]:
        cluster = await self._cluster_repo.get_by_id(cluster_id)
        if cluster is None:
            raise ValueError(f"StoryCluster {cluster_id} not found")
        if not self._settings.timeline_generation_enabled:
            return {"status": "disabled", "events_created": 0}
        cutoff = datetime.now(UTC) - timedelta(days=self._settings.timeline_lookback_days)
        articles = await self._article_repo.list_by_cluster_id(
            cluster_id=cluster.id,
            limit=self._settings.timeline_max_events_per_cluster * 2,
        )
        bounded_articles = [a for a in articles if a.published_at >= cutoff]
        if not bounded_articles:
            await self._event_repo.delete_for_cluster(cluster_id)
            return {"status": "no_candidates", "events_created": 0}
        claim_map: dict[UUID, list[Claim]] = {}
        for article in bounded_articles:
            try:
                claim_map[article.id] = await self._claim_repo.list_by_article_id(article.id)
            except Exception:
                claim_map[article.id] = []
        recent_conflicts: list[Conflict] = []
        with contextlib.suppress(Exception):
            recent_conflicts = await self._conflict_repo.list_recent(limit=200)
        article_conflict_counts: dict[UUID, int] = defaultdict(int)
        for conflict in recent_conflicts:
            with contextlib.suppress(ValueError):
                if conflict.article_a_id in {a.id for a in bounded_articles}:
                    article_conflict_counts[conflict.article_a_id] += 1
                if conflict.article_b_id in {a.id for a in bounded_articles}:
                    article_conflict_counts[conflict.article_b_id] += 1
        grouped = _group_articles_by_event(
            bounded_articles,
            max_events=self._settings.timeline_max_events_per_cluster,
        )
        events: list[StoryEvent] = []
        for seq, (event_type, event_time, group_articles) in enumerate(grouped):
            article_ids = tuple(
                a.id for a in group_articles[: self._settings.timeline_max_articles_per_event]
            )
            representative = group_articles[0]
            group_claim_ids = tuple(
                {
                    cid
                    for aid in article_ids
                    for cid in [c.id for c in claim_map.get(aid, [])][
                        : self._settings.timeline_max_claims_per_event
                    ]
                }
            )
            conflict_count = sum(
                article_conflict_counts.get(aid, 0) for aid in article_ids
            )
            confidence = _compute_event_confidence(
                article_count=len(group_articles),
                distinct_source_count=len({a.source_id for a in group_articles}),
                has_claim_support=bool(group_claim_ids),
                conflict_count=conflict_count,
            )
            title = representative.title[:200]
            description = representative.summary[:500] if representative.summary else title
            event = StoryEvent.create(
                story_cluster_id=cluster_id,
                event_type=event_type,
                title=title,
                description=description,
                confidence=confidence,
                event_time=event_time,
                representative_article_id=representative.id,
                sequence=seq,
                article_ids=article_ids,
                claim_ids=group_claim_ids,
            )
            events.append(event)
        ai_events: list[dict[str, Any]] = []
        if self._settings.ai_enabled and self._provider_manager is not None:
            ai_events = await self._ai_extract_events(cluster, bounded_articles, claim_map)
        if ai_events:
            existing_fingerprints = {
                _event_fingerprint(e.event_type, e.title, e.event_time) for e in events
            }
            for ai_event in ai_events:
                fp = _event_fingerprint(
                    ai_event["event_type"],
                    ai_event["title"],
                    ai_event.get("event_time"),
                )
                if fp not in existing_fingerprints:
                    events.append(
                        StoryEvent.create(
                            story_cluster_id=cluster_id,
                            event_type=ai_event["event_type"],
                            title=ai_event["title"],
                            description=ai_event["description"],
                            confidence=ai_event.get("confidence", 0.5),
                            event_time=ai_event.get("event_time"),
                            representative_article_id=ai_event.get("representative_article_id"),
                            sequence=len(events),
                            article_ids=ai_event.get("article_ids", ()),
                            claim_ids=ai_event.get("claim_ids", ()),
                        )
                    )
        persisted = await self._event_repo.replace_for_cluster(cluster_id, events)
        self._logger.info(
            "Timeline generated",
            cluster_id=str(cluster_id),
            events=len(persisted),
            method="deterministic+ai",
        )
        return {
            "status": "generated",
            "events_created": len(persisted),
            "cluster_id": str(cluster_id),
        }

    async def _ai_extract_events(
        self,
        cluster: Any,
        articles: list[Article],
        claim_map: dict[UUID, list[Claim]],
    ) -> list[dict[str, Any]]:
        if not articles or not self._provider_manager:
            return []
        try:
            from pydantic import BaseModel, Field

            class AIEvent(BaseModel):
                event_type: str = Field(max_length=32)
                event_time: str | None = None
                title: str = Field(max_length=200)
                description: str = Field(max_length=500)
                article_ids: list[str] = Field(max_length=10)
                claim_ids: list[str] = Field(max_length=5)
                confidence: float = Field(ge=0.0, le=1.0)

            class AIEventResponse(BaseModel):
                events: list[AIEvent] = Field(max_length=10)

            candidates = articles[: self._settings.timeline_max_llm_evaluations]
            article_context = "\n".join(
                f"- [{a.published_at.isoformat()}] {a.title}: {a.summary or ''}"
                for a in candidates
            )
            prompt = (
                "Identify meaningful story events from the following articles. "
                "Return JSON only. Do not invent facts. Use only provided article content.\n"
                f"Cluster: {cluster.title}\nArticles:\n{article_context}"
            )
            response = await self._provider_manager.acomplete(
                capability="analysis",
                prompt=prompt,
                response_format=AIEventResponse,
                max_tokens=1024,
                temperature=0.2,
            )
            parsed = AIEventResponse.model_validate_json(response.content)
            valid_article_ids = {str(a.id) for a in candidates}
            valid_claim_ids = {
                str(c.id) for c in [c for claims in claim_map.values() for c in claims]
            }
            events: list[dict[str, Any]] = []
            for ev in parsed.events:
                article_ids = [
                    aid for aid in ev.article_ids if aid in valid_article_ids
                ][:10]
                claim_ids = [
                    cid for cid in ev.claim_ids if cid in valid_claim_ids
                ][:5]
                if not article_ids:
                    continue
                event_type = (
                    StoryEventType(ev.event_type)
                    if ev.event_type in {e.value for e in StoryEventType}
                    else StoryEventType.OTHER
                )
                event_time = None
                if ev.event_time:
                    with contextlib.suppress(ValueError):
                        event_time = datetime.fromisoformat(ev.event_time)
                events.append(
                    {
                        "event_type": event_type,
                        "event_time": event_time,
                        "title": ev.title,
                        "description": ev.description,
                        "article_ids": tuple(UUID(aid) for aid in article_ids),
                        "claim_ids": tuple(UUID(cid) for cid in claim_ids),
                        "confidence": ev.confidence,
                        "representative_article_id": UUID(article_ids[0]),
                    }
                )
            return events
        except Exception as exc:
            logger.warning(
                "AI timeline extraction failed, using deterministic fallback",
                error=str(exc),
            )
            return []


__all__ = ["GenerateStoryTimelineUseCase"]
