"""
Graph intelligence service for knowledge-graph-aware discovery.

Computes bounded, explainable, conflict-aware graph signals for:

- Related story enrichment
- Entity neighborhood discovery
- Explainable relationship paths
- Graph-derived relevance scoring

All scoring is deterministic and bounded. No graph database is used;
traversal is performed via bounded BFS over the existing relationship table.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from ai_news_digest.core.logging import get_logger
from ai_news_digest.domain.enums.entity_type import EntityType
from ai_news_digest.domain.enums.relationship_status import RelationshipStatus
from ai_news_digest.domain.models.relationship import Relationship

logger = get_logger(__name__)


class ConnectionSignal(StrEnum):
    """Reasons why two entities are graph-connected."""

    SHARED_COMPANY = "shared_company"
    SHARED_TOPIC = "shared_topic"
    SHARED_CATEGORY = "shared_category"
    SHARED_STORY = "shared_story"
    VERIFIED_RELATIONSHIP = "verified_relationship"
    DISPUTED_RELATIONSHIP = "disputed_relationship"
    MULTIPLE_SOURCES = "multiple_independent_sources"
    RECENT_CONNECTION = "recent_connection"
    STRONG_CONNECTION = "strong_connection"


@dataclass(slots=True)
class GraphConnection:
    """A single graph connection between two entities."""

    entity_type: str
    entity_id: str
    name: str
    relationship_type: str | None = None
    status: str | None = None
    score: float = 0.0
    signals: list[str] = field(default_factory=list)
    explanation: str = ""
    source_count: int = 0
    is_disputed: bool = False
    is_retracted: bool = False


@dataclass(slots=True)
class GraphPath:
    """A bounded path between two entities in the graph."""

    path: list[dict[str, Any]]
    length: int
    explanation: str


@dataclass(slots=True)
class EntityNeighborhood:
    """Bounded neighborhood around an entity."""

    entity_type: str
    entity_id: str
    nodes: list[GraphConnection]
    edges: list[dict[str, Any]]
    total_nodes: int
    total_edges: int
    truncated: bool = False


@dataclass(slots=True)
class RelatedStoryGraphSignal:
    """Graph-derived signals for a related story cluster."""

    cluster_id: str
    title: str
    graph_score: float
    signals: list[str]
    explanation: str
    shared_companies: list[str]
    shared_topics: list[str]
    shared_categories: list[str]
    relationship_count: int


class GraphIntelligenceService:
    """Compute graph-aware intelligence signals.

    This service is pure: it receives domain objects and returns scored
    results. All database access is performed by the caller.
    """

    # Bounded traversal limits
    MAX_BFS_DEPTH: int = 3
    MAX_BFS_NODES: int = 50
    MAX_BFS_EDGES: int = 200
    MAX_PATHS: int = 10
    MAX_NEIGHBORHOOD_NODES: int = 20
    MAX_NEIGHBORHOOD_EDGES: int = 50

    # Score weights (must sum to <= 1.0 for normalized score)
    WEIGHT_SHARED_COMPANY: float = 0.25
    WEIGHT_SHARED_TOPIC: float = 0.20
    WEIGHT_SHARED_CATEGORY: float = 0.10
    WEIGHT_RELATIONSHIP: float = 0.25
    WEIGHT_RECENCY: float = 0.10
    WEIGHT_SOURCE_DIVERSITY: float = 0.10

    # Status multipliers
    DISPUTED_MULTIPLIER: float = 0.3
    RETRACTED_MULTIPLIER: float = 0.0
    INACTIVE_MULTIPLIER: float = 0.0
    CANDIDATE_MULTIPLIER: float = 0.5

    # Recency window (hours)
    RECENT_WINDOW_HOURS: float = 72.0

    def __init__(self) -> None:
        self._weights = _GraphWeights()

    def compute_related_story_signals(
        self,
        source_cluster_id: str,
        candidate_cluster_id: str,
        source_company_ids: set[str],
        source_topic_ids: set[str],
        source_category_ids: set[str],
        candidate_company_ids: set[str],
        candidate_topic_ids: set[str],
        candidate_category_ids: set[str],
        relationships: list[Relationship],
        now: datetime | None = None,
    ) -> RelatedStoryGraphSignal | None:
        """Compute graph signals between two story clusters.

        Returns None if there is no meaningful graph connection.
        """
        if source_cluster_id == candidate_cluster_id:
            return None

        if now is None:
            now = datetime.now(UTC)

        signals: list[str] = []
        signal_scores: list[float] = []

        shared_companies = source_company_ids & candidate_company_ids
        shared_topics = source_topic_ids & candidate_topic_ids
        shared_categories = source_category_ids & candidate_category_ids

        if shared_companies:
            signals.append(ConnectionSignal.SHARED_COMPANY.value)
            signal_scores.append(self.WEIGHT_SHARED_COMPANY)

        if shared_topics:
            signals.append(ConnectionSignal.SHARED_TOPIC.value)
            signal_scores.append(self.WEIGHT_SHARED_TOPIC)

        if shared_categories:
            signals.append(ConnectionSignal.SHARED_CATEGORY.value)
            signal_scores.append(self.WEIGHT_SHARED_CATEGORY)

        # Evaluate relationships
        rel_score, rel_signals = self._evaluate_relationships(relationships, now)
        signals.extend(rel_signals)
        if rel_score > 0:
            signal_scores.append(self.WEIGHT_RELATIONSHIP * rel_score)

        if not signals:
            return None

        graph_score = min(1.0, sum(signal_scores))

        explanation = self._build_explanation(
            shared_companies=shared_companies,
            shared_topics=shared_topics,
            shared_categories=shared_categories,
            signals=signals,
            relationship_count=len(relationships),
        )

        return RelatedStoryGraphSignal(
            cluster_id=candidate_cluster_id,
            title="",
            graph_score=graph_score,
            signals=signals,
            explanation=explanation,
            shared_companies=sorted(shared_companies),
            shared_topics=sorted(shared_topics),
            shared_categories=sorted(shared_categories),
            relationship_count=len(relationships),
        )

    def get_entity_connections(
        self,
        entity_type: str,
        entity_id: str,
        relationships: list[Relationship],
        name_resolver: Callable[[str, str], str],
        now: datetime | None = None,
    ) -> list[GraphConnection]:
        """Return graph connections for an entity, with explanations."""
        if now is None:
            now = datetime.now(UTC)

        connections: dict[str, GraphConnection] = {}

        for rel in relationships:
            if not self._is_active(rel.status):
                continue

            is_source = rel.subject_entity_id == entity_id
            other_type = (
                rel.object_entity_type.value
                if is_source
                else rel.subject_entity_type.value
            )
            other_id = (
                rel.object_entity_id if is_source else rel.subject_entity_id
            )

            key = f"{other_type}:{other_id}"
            if key not in connections:
                connections[key] = GraphConnection(
                    entity_type=other_type,
                    entity_id=str(other_id),
                    name=name_resolver(other_type, str(other_id)),
                )

            conn = connections[key]
            rel_score = self._relationship_score(rel, now)
            is_disputed = rel.status == RelationshipStatus.DISPUTED
            is_retracted = rel.status == RelationshipStatus.RETRACTED

            if is_retracted:
                continue

            if conn.relationship_type is None:
                conn.relationship_type = rel.relationship_type.value
                conn.status = rel.status.value
            else:
                conn.relationship_type = (
                    f"{conn.relationship_type}, {rel.relationship_type.value}"
                )

            conn.score = max(conn.score, rel_score)
            conn.is_disputed = conn.is_disputed or is_disputed
            conn.is_retracted = conn.is_retracted or is_retracted
            conn.source_count += 1

            recent_window = self.RECENT_WINDOW_HOURS * 3600
            if rel.observed_at and (now - rel.observed_at).total_seconds() < recent_window:
                conn.signals.append(ConnectionSignal.RECENT_CONNECTION.value)

        # Build explanations and finalize scores
        result: list[GraphConnection] = []
        for conn in connections.values():
            if conn.is_retracted:
                continue

            explanation_parts = []
            if conn.relationship_type:
                explanation_parts.append(f"Relationship: {conn.relationship_type}")

            if conn.source_count > 1:
                explanation_parts.append(f"{conn.source_count} independent sources")
                conn.signals.append(ConnectionSignal.MULTIPLE_SOURCES.value)

            if conn.is_disputed:
                explanation_parts.append("(disputed)")
                conn.signals.append(ConnectionSignal.DISPUTED_RELATIONSHIP.value)
                conn.score *= self.DISPUTED_MULTIPLIER
            else:
                conn.signals.append(ConnectionSignal.VERIFIED_RELATIONSHIP.value)

            if ConnectionSignal.RECENT_CONNECTION.value in conn.signals:
                explanation_parts.append("recent connection")

            conn.explanation = "; ".join(explanation_parts) if explanation_parts else "Connected"
            result.append(conn)

        result.sort(key=lambda c: c.score, reverse=True)
        return result

    def find_path(
        self,
        relationships: list[Relationship],
        source_type: str,
        source_id: str,
        target_type: str,
        target_id: str,
    ) -> GraphPath | None:
        """Find a bounded path between two entities using BFS."""
        if source_type == target_type and source_id == target_id:
            return None

        adjacency: dict[str, dict[str, list[dict[str, Any]]]] = {}
        for rel in relationships:
            if not self._is_active(rel.status):
                continue

            subj_key = f"{rel.subject_entity_type.value}:{rel.subject_entity_id}"
            obj_key = f"{rel.object_entity_type.value}:{rel.object_entity_id}"

            if subj_key not in adjacency:
                adjacency[subj_key] = {}
            if obj_key not in adjacency:
                adjacency[obj_key] = {}

            edge = {
                "relationship_type": rel.relationship_type.value,
                "status": rel.status.value,
                "direction": "outgoing",
            }
            adjacency[subj_key].setdefault(obj_key, []).append(edge)

            reverse_edge = {
                "relationship_type": rel.relationship_type.value,
                "status": rel.status.value,
                "direction": "incoming",
            }
            adjacency[obj_key].setdefault(subj_key, []).append(reverse_edge)

        source_key = f"{source_type}:{source_id}"
        target_key = f"{target_type}:{target_id}"

        if source_key not in adjacency and target_key not in adjacency:
            return None

        visited = {source_key}
        queue: deque[tuple[str, list[dict[str, Any]]]] = deque([(source_key, [])])
        paths_found = 0

        while queue and paths_found < self.MAX_PATHS:
            current, path = queue.popleft()

            if current == target_key:
                paths_found += 1
                explanation = self._build_path_explanation(path)
                return GraphPath(path=path, length=len(path), explanation=explanation)

            if len(path) >= self.MAX_BFS_DEPTH:
                continue

            for neighbor, edges in adjacency.get(current, {}).items():
                if neighbor in visited:
                    continue
                visited.add(neighbor)

                for edge in edges:
                    new_path = [*path, {"from": current, "to": neighbor, **edge}]
                    queue.append((neighbor, new_path))

        return None

    def get_entity_neighborhood(
        self,
        entity_type: str,
        entity_id: str,
        relationships: list[Relationship],
        name_resolver: Callable[[str, str], str],
        now: datetime | None = None,
    ) -> EntityNeighborhood:
        """Return a bounded neighborhood around an entity."""
        if now is None:
            now = datetime.now(UTC)

        visited_nodes: set[str] = set()
        visited_edges: list[dict[str, Any]] = []
        nodes_map: dict[str, GraphConnection] = {}

        entity_key = f"{entity_type}:{entity_id}"
        visited_nodes.add(entity_key)

        queue: deque[tuple[str, int]] = deque([(entity_key, 0)])
        adjacency: dict[str, list[tuple[str, Relationship]]] = {}

        for rel in relationships:
            if not self._is_active(rel.status):
                continue
            subj_key = f"{rel.subject_entity_type.value}:{rel.subject_entity_id}"
            obj_key = f"{rel.object_entity_type.value}:{rel.object_entity_id}"
            adjacency.setdefault(subj_key, []).append((obj_key, rel))
            adjacency.setdefault(obj_key, []).append((subj_key, rel))

        truncated = False

        node_limit = self.MAX_BFS_NODES
        edge_limit = self.MAX_BFS_EDGES
        while (
            queue
            and len(visited_nodes) < node_limit
            and len(visited_edges) < edge_limit
        ):
            current, depth = queue.popleft()

            if depth >= self.MAX_BFS_DEPTH:
                continue

            for neighbor_key, rel in adjacency.get(current, []):
                if neighbor_key in visited_nodes and len(visited_nodes) >= node_limit:
                    continue

                edge_info = {
                    "from": current,
                    "to": neighbor_key,
                    "relationship_type": rel.relationship_type.value,
                    "status": rel.status.value,
                }
                if edge_info not in visited_edges:
                    visited_edges.append(edge_info)

                if neighbor_key not in visited_nodes:
                    visited_nodes.add(neighbor_key)
                    parts = neighbor_key.split(":")
                    n_type, n_id = parts[0], parts[1]

                    rel_score = self._relationship_score(rel, now)
                    nodes_map[neighbor_key] = GraphConnection(
                        entity_type=n_type,
                        entity_id=n_id,
                        name=name_resolver(n_type, n_id),
                        relationship_type=rel.relationship_type.value,
                        status=rel.status.value,
                        score=rel_score,
                    )

                if len(visited_nodes) >= node_limit:
                    truncated = True
                    break

                if len(visited_edges) >= edge_limit:
                    truncated = True
                    break

                queue.append((neighbor_key, depth + 1))

        if len(visited_nodes) >= node_limit or len(visited_edges) >= edge_limit:
            truncated = True

        return EntityNeighborhood(
            entity_type=entity_type,
            entity_id=entity_id,
            nodes=list(nodes_map.values()),
            edges=visited_edges,
            total_nodes=len(visited_nodes),
            total_edges=len(visited_edges),
            truncated=truncated,
        )

    def _evaluate_relationships(
        self,
        relationships: list[Relationship],
        now: datetime,
    ) -> tuple[float, list[str]]:
        """Evaluate a set of relationships and return aggregate score + signals."""
        if not relationships:
            return 0.0, []

        active_rels = [r for r in relationships if self._is_active(r.status)]
        if not active_rels:
            return 0.0, []

        scores: list[float] = []
        signals: list[str] = []

        for rel in active_rels:
            score = self._relationship_score(rel, now)
            scores.append(score)

            if rel.status == RelationshipStatus.VERIFIED:
                signals.append(ConnectionSignal.VERIFIED_RELATIONSHIP.value)
            elif rel.status == RelationshipStatus.DISPUTED:
                signals.append(ConnectionSignal.DISPUTED_RELATIONSHIP.value)

        avg_score = sum(scores) / len(scores) if scores else 0.0

        article_ids = {r.article_id for r in active_rels if r.article_id}
        if len(article_ids) > 1:
            signals.append(ConnectionSignal.MULTIPLE_SOURCES.value)

        recent_window = self.RECENT_WINDOW_HOURS * 3600
        recent_any = any(
            rel.observed_at and (now - rel.observed_at).total_seconds() < recent_window
            for rel in active_rels
        )
        if recent_any:
            signals.append(ConnectionSignal.RECENT_CONNECTION.value)

        return avg_score, signals

    def _relationship_score(self, rel: Relationship, now: datetime) -> float:
        """Compute a normalized score for a single relationship."""
        if not self._is_active(rel.status):
            return 0.0

        score = 1.0

        if rel.status == RelationshipStatus.DISPUTED:
            score *= self.DISPUTED_MULTIPLIER
        elif rel.status == RelationshipStatus.CANDIDATE:
            score *= self.CANDIDATE_MULTIPLIER

        if rel.confidence is not None:
            score *= min(1.0, max(0.0, rel.confidence))

        if rel.observed_at:
            age_hours = (now - rel.observed_at).total_seconds() / 3600.0
            recency = max(0.0, 1.0 - (age_hours / (7 * 24)))
            score = score * 0.7 + recency * 0.3

        if rel.provenance_source.value in ("deterministic", "manual"):
            score *= 1.0
        else:
            score *= 0.8

        return max(0.0, min(1.0, score))

    def _is_active(self, status: RelationshipStatus) -> bool:
        return status not in (
            RelationshipStatus.RETRACTED,
            RelationshipStatus.INACTIVE,
        )

    def _build_explanation(
        self,
        shared_companies: set[str],
        shared_topics: set[str],
        shared_categories: set[str],
        signals: list[str],
        relationship_count: int,
    ) -> str:
        """Build a human-readable explanation."""
        parts: list[str] = []

        if shared_companies:
            parts.append(f"Shared company: {', '.join(sorted(shared_companies))}")
        if shared_topics:
            parts.append(f"Shared topic: {', '.join(sorted(shared_topics))}")
        if shared_categories:
            parts.append(
                f"Shared category: {', '.join(sorted(shared_categories))}"
            )

        has_verified = ConnectionSignal.VERIFIED_RELATIONSHIP.value in signals
        has_disputed = ConnectionSignal.DISPUTED_RELATIONSHIP.value in signals
        if has_verified and not has_disputed:
            parts.append("Supported by verified relationships")
        elif has_disputed:
            parts.append("Partially supported by disputed relationships")

        if ConnectionSignal.MULTIPLE_SOURCES.value in signals:
            parts.append("Multiple independent sources")

        if ConnectionSignal.RECENT_CONNECTION.value in signals:
            parts.append("Recent connection activity")

        return "; ".join(parts) if parts else "Graph-connected"

    def _build_path_explanation(self, path: list[dict[str, Any]]) -> str:
        """Build a human-readable path explanation."""
        if not path:
            return "Directly connected"

        parts = []
        for step in path:
            rel = step.get("relationship_type", "related to")
            parts.append(f"{step['from']} --[{rel}]--> {step['to']}")

        return " | ".join(parts)


@dataclass(slots=True)
class _GraphWeights:
    """Centralized graph scoring weights."""

    SHARED_COMPANY: float = 0.25
    SHARED_TOPIC: float = 0.20
    SHARED_CATEGORY: float = 0.10
    RELATIONSHIP: float = 0.25
    RECENCY: float = 0.10
    SOURCE_DIVERSITY: float = 0.10


__all__ = [
    "ConnectionSignal",
    "EntityNeighborhood",
    "GraphConnection",
    "GraphIntelligenceService",
    "GraphPath",
    "RelatedStoryGraphSignal",
]
