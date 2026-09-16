"""Story Intelligence Brief assembly service for M95.

Composes existing M67-M94 intelligence capabilities into a coherent,
bounded, evidence-first story brief without duplicating subsystems.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from ai_news_digest.application.services.graph_intelligence.graph_intelligence_service import (
    GraphIntelligenceService,
)
from ai_news_digest.application.use_cases.story_cluster.story_intelligence import (
    build_timeline,
    classify_source_role,
    compute_what_changed,
)
from ai_news_digest.core.config import get_settings
from ai_news_digest.core.logging import get_logger
from ai_news_digest.domain.models.story_cluster import StoryCluster

logger = get_logger(__name__)


class StoryIntelligenceBriefService:
    """Assemble a bounded Story Intelligence Brief from existing data.

    This service is purely compositional: it reuses existing repositories,
    services, and intelligence layers rather than introducing new AI calls
    or duplicating data. All collections are bounded to prevent unbounded
    payload growth.
    """

    def __init__(
        self,
        container: Any,
    ) -> None:
        self._container = container
        self._settings = get_settings()

    async def build_brief(
        self,
        slug: str,
        user_id: UUID | None = None,
    ) -> dict[str, Any]:
        """Build a complete story intelligence brief for the given cluster slug.

        Returns a dict suitable for direct serialization as the brief response.
        """
        cluster = await self._container.story_cluster_repository.get_by_slug(slug)
        if cluster is None:
            return {}

        article_limit = 100
        articles = await self._container.article_repository.list_by_cluster_id(
            cluster_id=cluster.id,
            limit=article_limit,
        )

        sources = await self._container.source_repository.list_all()
        source_map = {str(source.id): source for source in sources}
        source_name_map = {str(source.id): source.name for source in sources}
        source_type_map = {str(source.id): source.source_type.value for source in sources}

        article_count = len(articles)
        unique_source_ids = {a.source_id for a in articles if a.source_id}
        source_count = len(unique_source_ids)

        representative_article = None
        if cluster.representative_article_id is not None:
            for article in articles:
                if article.id == cluster.representative_article_id:
                    representative_article = article
                    break

        source_role_map: dict[str, str] = {}
        for article in articles:
            source_type = source_type_map.get(str(article.source_id), "other")
            source_role = classify_source_role(
                article_published_at=article.published_at or datetime.now(UTC),
                cluster_first_published_at=cluster.first_published_at or datetime.now(UTC),
                source_type=source_type,
                representative_title=(
                    representative_article.title if representative_article else None
                ),
                article_title=article.title,
            )
            source_role_map[str(article.id)] = source_role

        brief: dict[str, Any] = {
            "id": str(cluster.id),
            "title": cluster.title,
            "slug": cluster.slug,
            "status": cluster.status.value,
            "importance_score": cluster.importance_score,
            "confidence": cluster.confidence,
            "ranking_score": cluster.ranking_score,
            "ranking_explanation": cluster.ranking_explanation,
            "first_published_at": (
                cluster.first_published_at.isoformat() if cluster.first_published_at else None
            ),
            "last_updated_at": (
                cluster.last_updated_at.isoformat() if cluster.last_updated_at else None
            ),
            "article_count": article_count,
            "source_count": source_count,
            "independent_source_count": source_count,
        }

        summary = cluster.summary or self._build_summary_fallback(articles, source_name_map)
        brief["summary"] = summary

        key_takeaways = self._build_key_takeaways(articles)
        brief["key_takeaways"] = key_takeaways

        why_it_matters = self._build_why_it_matters(cluster, articles)
        brief["why_it_matters"] = why_it_matters

        activity_status = None
        activity_score = None
        latest_activity_at = None
        try:
            activity = await self._container.story_activity_repository.get_by_story_cluster_id(
                cluster.id
            )
            if activity is not None:
                activity_status = activity.status.value
                activity_score = activity.activity_score
                latest_activity_at = activity.evaluated_at.isoformat()
        except Exception:  # noqa: S110
            pass
        brief["activity_status"] = activity_status
        brief["activity_score"] = activity_score
        brief["latest_activity_at"] = latest_activity_at

        sources_section = self._build_sources_section(
            articles, source_map, source_name_map, source_type_map, source_role_map, article_limit,
        )
        brief["sources"] = sources_section

        claims_section = await self._build_claims_section(cluster.id, articles, source_name_map)
        brief["claims"] = claims_section

        conflicts_section = await self._build_conflicts_section(
            cluster.id, articles, source_name_map,
        )
        brief["conflicts"] = conflicts_section

        timeline_section = self._build_timeline_section(articles, source_name_map, source_role_map)
        brief["timeline"] = timeline_section

        story_evolution = self._build_story_evolution(
            articles, source_name_map, timeline_section, summary
        )
        brief["story_evolution"] = story_evolution

        trends = await self._build_trends_section(cluster)
        brief["trends"] = trends

        entities_section = await self._build_entities_section(cluster.id)
        brief["entities"] = entities_section

        related_stories = await self._build_related_stories_section(
            cluster, articles, article_limit,
        )
        brief["related_stories"] = related_stories

        provenance = self._build_provenance(cluster, articles)
        brief["provenance"] = provenance

        quality = await self._build_quality(
            cluster, articles, article_count, source_count, conflicts_section,
        )
        brief["quality"] = quality

        updated_at = self._compute_updated_at(
            cluster, articles, activity, latest_activity_at
        )
        brief["updated_at"] = updated_at

        personalization = self._build_personalization(user_id, cluster, articles)
        brief["personalization"] = personalization

        return brief

    def _build_summary_fallback(
        self, articles: list[Any], source_name_map: dict[str, str],
    ) -> str | None:
        if not articles:
            return None
        for article in articles:
            if article.summary:
                return article.summary
        return None

    def _build_key_takeaways(self, articles: list[Any]) -> list[str]:
        seen: set[str] = set()
        takeaways: list[str] = []
        for article in articles:
            if not article.key_takeaways:
                continue
            for takeaway in article.key_takeaways:
                normalized = takeaway.strip()
                if not normalized or normalized in seen:
                    continue
                seen.add(normalized)
                takeaways.append(normalized)
                if len(takeaways) >= 8:
                    return takeaways
        return takeaways

    def _build_why_it_matters(self, cluster: StoryCluster, articles: list[Any]) -> str | None:
        for article in articles:
            if article.why_it_matters:
                return article.why_it_matters
        return None

    def _build_sources_section(
        self,
        articles: list[Any],
        source_map: dict[str, Any],
        source_name_map: dict[str, str],
        source_type_map: dict[str, str],
        source_role_map: dict[str, str],
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        seen_article_ids: set[str] = set()
        unique_sources: dict[str, dict[str, Any]] = {}

        for article in articles[:limit]:
            if article.id in seen_article_ids:
                continue
            seen_article_ids.add(str(article.id))

            source_id = str(article.source_id) if article.source_id else None
            if not source_id:
                continue

            source_name = source_name_map.get(source_id, "Unknown")
            source_type = source_type_map.get(source_id, "other")
            source_role = source_role_map.get(str(article.id), "Related coverage")

            if source_id not in unique_sources:
                unique_sources[source_id] = {
                "publisher": source_name,
                "source_type": source_type,
                "source_role": source_role,
                "provenance_source": (
                    "ai_extracted"
                    if getattr(article, "ai_provider", None) or getattr(article, "ai_model", None)
                    else "deterministic"
                ),
                "articles": [],
            }

            unique_sources[source_id]["articles"].append({
                "headline": article.title,
                "publication_date": (
                    article.published_at.isoformat() if article.published_at else None
                ),
                "url": article.url,
                "source_id": source_id,
            })

        result = []
        for _source_id, data in unique_sources.items():
            result.append({
                "publisher": data["publisher"],
                "source_type": data["source_type"],
                "source_role": data["source_role"],
                "article_count": len(data["articles"]),
                "articles": data["articles"][:5],
            })
        return result[:limit]

    async def _build_claims_section(
        self,
        cluster_id: UUID,
        articles: list[Any],
        source_name_map: dict[str, str],
    ) -> list[dict[str, Any]]:
        article_ids = [a.id for a in articles]
        if not article_ids:
            return []

        try:
            claim_repo = self._container.claim_repository
            all_claims: list[Any] = []
            for aid in article_ids:
                try:
                    claims = await claim_repo.list_by_article_id(aid)
                    for claim in claims:
                        claim.article_id = aid
                        all_claims.append(claim)
                except Exception:  # noqa: S112
                    continue

            seen_claim_ids: set[str] = set()
            claims_section: list[dict[str, Any]] = []
            for claim in all_claims:
                claim_id_str = str(claim.id)
                if claim_id_str in seen_claim_ids:
                    continue
                seen_claim_ids.add(claim_id_str)

                evidence_items: list[dict[str, Any]] = []
                try:
                    evidence_list = await claim_repo.list_evidence_by_claim_id(claim.id)
                    for ev in evidence_list[:5]:
                        evidence_items.append({
                            "evidence_type": ev.evidence_type.value,
                            "excerpt": ev.excerpt[:500] if ev.excerpt else None,
                            "source_location": ev.source_location,
                            "strength": ev.strength.value if ev.strength else None,
                            "article_title": None,
                            "source_name": source_name_map.get(str(claim.source_id)),
                            "published_at": (
                                articles[0].published_at.isoformat()
                                if articles and articles[0].published_at
                                else None
                            ),
                        })
                except Exception:
                    evidence_items = []

                claims_section.append({
                    "claim_text": claim.claim_text[:1000],
                    "type": claim.claim_type.value,
                    "status": claim.status.value,
                    "confidence": claim.confidence,
                    "evidence_support_score": claim.evidence_support_score,
                    "evidence_count": len(evidence_items),
                    "evidence": evidence_items if evidence_items else None,
                    "provenance_source": (
                        claim.ai_provider or (claim.ai_model and "ai_extracted") or "deterministic"
                    ),
                })

                if len(claims_section) >= 20:
                    break
            return claims_section
        except Exception:
            return []

    async def _build_conflicts_section(
        self,
        cluster_id: UUID,
        articles: list[Any],
        source_name_map: dict[str, str],
    ) -> list[dict[str, Any]]:
        article_ids = {a.id for a in articles}
        try:
            conflict_repo = self._container.conflict_repository
            recent_conflicts = await conflict_repo.list_recent(limit=200)
            cluster_conflicts = [
                c for c in recent_conflicts
                if c.article_a_id in article_ids or c.article_b_id in article_ids
            ]

            result: list[dict[str, Any]] = []
            for conflict in cluster_conflicts[:20]:
                source_a_name = source_name_map.get(str(conflict.source_a_id))
                source_b_name = source_name_map.get(str(conflict.source_b_id))
                pub_a = None
                pub_b = None
                for article in articles:
                    if article.id == conflict.article_a_id and article.published_at:
                        pub_a = article.published_at.isoformat()
                    if article.id == conflict.article_b_id and article.published_at:
                        pub_b = article.published_at.isoformat()

                result.append({
                    "conflict_type": conflict.conflict_type.value,
                    "status": conflict.status.value,
                    "confidence": conflict.confidence,
                    "explanation": conflict.explanation,
                    "source_a_name": source_a_name,
                    "source_b_name": source_b_name,
                    "same_source": conflict.same_source,
                    "published_at_a": pub_a,
                    "published_at_b": pub_b,
                })
            return result
        except Exception:
            return []

    def _build_timeline_section(
        self,
        articles: list[Any],
        source_name_map: dict[str, str],
        source_role_map: dict[str, str],
    ) -> list[dict[str, Any]]:
        timeline = build_timeline(articles, source_name_map)
        for item in timeline:
            item_id = item.get("id")
            if item_id is not None:
                item["source_role"] = source_role_map.get(str(item_id))

        result: list[dict[str, Any]] = []
        for item in timeline[:30]:
            entry = {
                "id": item.get("id"),
                "title": item.get("title"),
                "url": item.get("url"),
                "summary": item.get("summary"),
                "published_at": item.get("published_at"),
                "source_name": item.get("source_name"),
                "source_type": item.get("source_type"),
                "source_role": item.get("source_role"),
                "importance_score": item.get("importance_score"),
                "confidence": item.get("confidence"),
            }
            result.append(entry)
        return result

    def _build_story_evolution(
        self,
        articles: list[Any],
        source_name_map: dict[str, str],
        timeline: list[dict[str, Any]],
        summary: str | None,
    ) -> dict[str, Any]:
        evolution: dict[str, Any] = {
            "first_reported": None,
            "latest_development": None,
            "major_developments": [],
            "current_status": None,
        }

        if not timeline:
            return evolution

        first = timeline[0]
        latest = timeline[-1]

        evolution["first_reported"] = {
            "title": first.get("title"),
            "published_at": first.get("published_at"),
            "source_name": first.get("source_name"),
        }

        evolution["latest_development"] = {
            "title": latest.get("title"),
            "published_at": latest.get("published_at"),
            "source_name": latest.get("source_name"),
        }

        what_changed = compute_what_changed(timeline)
        evolution["major_developments"] = what_changed[:10]

        return evolution

    async def _build_trends_section(self, cluster: StoryCluster) -> list[dict[str, Any]] | None:
        if not self._settings.trend_detection_enabled:
            return None

        try:
            trends = await self._container.trend_repository.list_public(limit=50)
            related_trends = []
            for trend in trends:
                related_ids = getattr(trend, "related_company_ids", None) or []
                related_ids += getattr(trend, "related_topic_ids", None) or []
                related_ids += getattr(trend, "related_category_ids", None) or []
                if str(cluster.id) in [str(rid) for rid in related_ids]:
                    related_trends.append({
                        "id": str(trend.id),
                        "trend_type": trend.trend_type.value,
                        "display_name": trend.display_name,
                        "status": trend.status.value,
                        "trend_score": trend.trend_score,
                        "momentum_score": trend.momentum_score,
                        "explanation": trend.explanation,
                    })
                if len(related_trends) >= 5:
                    break
            return related_trends if related_trends else None
        except Exception:
            return None

    async def _build_entities_section(self, cluster_id: UUID) -> dict[str, Any]:
        entities: dict[str, Any] = {
            "companies": [],
            "topics": [],
            "graph_connections": [],
        }

        if not self._settings.knowledge_graph_enabled:
            return entities

        try:
            relationships = await self._container.relationship_repository.list_for_entity(
                entity_type="story",
                entity_id=cluster_id,
                status=None,
                limit=200,
            )

            company_ids = [
                str(r.object_entity_id)
                for r in relationships
                if r.object_entity_type.value == "company"
            ]
            topic_ids = [
                str(r.object_entity_id)
                for r in relationships
                if r.object_entity_type.value == "topic"
            ]

            if company_ids:
                companies = await self._container.company_repository.list_by_ids(
                    [UUID(cid) for cid in company_ids]
                )
                entities["companies"] = [{"id": str(c.id), "name": c.name} for c in companies]

            if topic_ids:
                topics = await self._container.topic_repository.list_by_ids(
                    [UUID(tid) for tid in topic_ids]
                )
                entities["topics"] = [{"id": str(t.id), "name": t.name} for t in topics]

            service = GraphIntelligenceService()

            def name_resolver(e_type: str, e_id: str) -> str:
                if e_type == "company":
                    for c in (entities.get("companies") or []):
                        if c["id"] == e_id:
                            return c["name"]
                if e_type == "topic":
                    for t in (entities.get("topics") or []):
                        if t["id"] == e_id:
                            return t["name"]
                return f"{e_type} {e_id[:8]}"

            connections = service.get_entity_connections(
                entity_type="story",
                entity_id=str(cluster_id),
                relationships=relationships,
                name_resolver=name_resolver,
            )
            entities["graph_connections"] = [
                {
                    "entity_type": c.entity_type,
                    "entity_id": c.entity_id,
                    "name": c.name,
                    "relationship_type": c.relationship_type,
                    "status": c.status,
                    "score": round(c.score, 4),
                    "signals": c.signals,
                    "explanation": c.explanation,
                    "source_count": c.source_count,
                    "is_disputed": c.is_disputed,
                    "is_retracted": c.is_retracted,
                }
                for c in connections[:20]
            ]
        except Exception:  # noqa: S110
            pass

        return entities

    async def _build_related_stories_section(
        self,
        cluster: StoryCluster,
        articles: list[Any],
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        if not articles:
            return []

        try:
            cutoff = datetime.now(UTC) - __import__("datetime").timedelta(hours=72)
            candidate_clusters = (
                await self._container.story_cluster_repository.find_recent_active_clusters(
                    cutoff=cutoff,
                    limit=200,
                )
            )

            existing_cluster_id = str(cluster.id)
            article = articles[0]

            related = await self._container.related_story_finder.find_for_article(
                article=article,
                existing_cluster_id=existing_cluster_id,
                clusters=candidate_clusters,
                limit=limit,
            )

            if self._settings.knowledge_graph_enabled:
                try:
                    service = GraphIntelligenceService()
                    source_company_ids = set(getattr(article, "companies", None) or [])
                    source_topic_ids = set(getattr(article, "topics", None) or [])

                    graph_signals_map: dict[str, dict[str, Any]] = {}
                    for cand_cluster in candidate_clusters:
                        if str(cand_cluster.id) == existing_cluster_id:
                            continue
                        candidate_rels = (
                            await self._container.relationship_repository.list_for_entity(
                                entity_type="story",
                                entity_id=cand_cluster.id,
                                status=None,
                                limit=50,
                            )
                        )
                        source_rels = (
                            await self._container.relationship_repository.list_for_entity(
                                entity_type="story",
                                entity_id=cluster.id,
                                status=None,
                                limit=50,
                            )
                        )
                        candidate_company_ids = {
                            str(r.object_entity_id)
                            for r in candidate_rels
                            if r.object_entity_type.value == "company"
                        }
                        candidate_topic_ids = {
                            str(r.object_entity_id)
                            for r in candidate_rels
                            if r.object_entity_type.value == "topic"
                        }
                        signal = service.compute_related_story_signals(
                            source_cluster_id=existing_cluster_id,
                            candidate_cluster_id=str(cand_cluster.id),
                            source_company_ids=source_company_ids,
                            source_topic_ids=source_topic_ids,
                            source_category_ids=set(),
                            candidate_company_ids=candidate_company_ids,
                            candidate_topic_ids=candidate_topic_ids,
                            candidate_category_ids=set(),
                            relationships=source_rels + candidate_rels,
                        )
                        if signal:
                            graph_signals_map[str(cand_cluster.id)] = {
                                "graph_score": signal.graph_score,
                                "signals": signal.signals,
                                "explanation": signal.explanation,
                                "relationship_count": signal.relationship_count,
                            }
                except Exception:
                    graph_signals_map = {}

                results: list[dict[str, Any]] = []
                for r in related:
                    graph_data = graph_signals_map.get(r.cluster_id)
                    reason = r.reason
                    if graph_data and graph_data.get("graph_score", 0) > 0:
                        reason = f"{r.reason}; {graph_data['explanation']}"

                    results.append({
                        "cluster_id": r.cluster_id,
                        "title": r.title,
                        "summary": r.summary,
                        "similarity": r.similarity,
                        "article_count": r.article_count,
                        "source_count": r.source_count,
                        "reason": reason,
                    })
                    if len(results) >= limit:
                        break
                return results

            return [
                {
                    "cluster_id": r.cluster_id,
                    "title": r.title,
                    "summary": r.summary,
                    "similarity": r.similarity,
                    "article_count": r.article_count,
                    "source_count": r.source_count,
                    "reason": r.reason,
                }
                for r in related[:limit]
            ]
        except Exception:
            return []

    def _build_provenance(
        self, cluster: StoryCluster, articles: list[Any],
    ) -> dict[str, Any]:
        def _has_ai(article: Any) -> bool:
            return bool(getattr(article, "ai_provider", None) or getattr(article, "ai_model", None))

        ai_articles = [a for a in articles if _has_ai(a)]
        deterministic_articles = [a for a in articles if not _has_ai(a)]

        return {
            "source": "ai_extracted" if ai_articles else "deterministic",
            "article_count": len(articles),
            "ai_generated_count": len(ai_articles),
            "deterministic_count": len(deterministic_articles),
            "is_complete": len(articles) > 0,
            "completeness_gaps": [] if articles else ["no_articles"],
        }

    async def _build_quality(
        self,
        cluster: StoryCluster,
        articles: list[Any],
        article_count: int,
        source_count: int,
        conflicts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        quality_flags: list[str] = []
        if article_count == 0:
            quality_flags.append("missing_evidence")
        if source_count <= 1:
            quality_flags.append("single_source")
        if source_count < 2:
            quality_flags.append("low_source_diversity")
        conflict_count = len(conflicts)
        if conflict_count > 0:
            quality_flags.append("conflicting_evidence")
        if conflict_count > 2:
            quality_flags.append("high_conflict")

        if article_count == 0:
            health_status = "insufficient_data"
        elif source_count == 0 or conflict_count > 2 or source_count <= 1:
            health_status = "degraded"
        else:
            health_status = "healthy"

        if self._settings.quality_gates_enabled:
            try:
                gate_repo = self._container.quality_gate_repository
                recent_fails, _ = await gate_repo.list_results(
                    limit=50,
                    result="fail",
                )
                story_components = {
                    "story_clustering",
                    "claims_evidence",
                    "conflict_detection",
                    "story_events",
                    "overall",
                }
                blocked_by_gate = any(
                    (
                        r.component.value
                        if hasattr(r.component, "value")
                        else r.component
                    )
                    in story_components
                    for r in recent_fails
                )
                if blocked_by_gate:
                    health_status = "blocked"
                    quality_flags.append("quality_gate_blocked")
            except Exception:  # noqa: S110
                pass

        overall_quality_score = max(
            0.0,
            min(
                1.0,
                (article_count / 5.0) * 0.3
                + (source_count / 5.0) * 0.3
                + max(0.0, 1.0 - (conflict_count / 3.0)) * 0.2
                + 0.1,
            ),
        )

        quality_explanation = f"{article_count} article(s); {source_count} independent source(s)"
        if conflict_count > 0:
            quality_explanation += f"; {conflict_count} conflict(s)"

        degraded = health_status == "degraded"
        degraded_message = (
            "Some intelligence for this story is currently unavailable."
            if degraded
            else None
        )

        return {
            "overall_quality_score": overall_quality_score,
            "quality_flags": quality_flags,
            "quality_explanation": quality_explanation,
            "evidence_coverage": min(1.0, article_count / 5.0) if article_count > 0 else 0.0,
            "source_coverage": min(1.0, source_count / 5.0) if source_count > 0 else 0.0,
            "conflict_count": conflict_count,
            "health_status": health_status,
            "degraded": degraded,
            "degraded_message": degraded_message,
        }

    def _compute_updated_at(
        self,
        cluster: StoryCluster,
        articles: list[Any],
        activity: Any,
        latest_activity_at: str | None,
    ) -> str | None:
        timestamps: list[datetime] = []
        if cluster.last_updated_at:
            timestamps.append(cluster.last_updated_at)
        if cluster.first_published_at:
            timestamps.append(cluster.first_published_at)
        for article in articles:
            if article.published_at:
                timestamps.append(article.published_at)
        if activity and getattr(activity, "evaluated_at", None):
            timestamps.append(activity.evaluated_at)

        if timestamps:
            return max(timestamps).isoformat()
        return datetime.now(UTC).isoformat()

    def _build_personalization(
        self,
        user_id: UUID | None,
        cluster: StoryCluster,
        articles: list[Any],
    ) -> dict[str, Any] | None:
        if user_id is None:
            return None

        try:
            return {
                "user_id": str(user_id),
                "relevance_reason": "Based on your preferences",
                "matched_companies": [],
                "matched_topics": [],
            }
        except Exception:
            return None


__all__ = ["StoryIntelligenceBriefService"]
