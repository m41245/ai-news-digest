# Milestone 90: Graph-Aware Intelligence and Discovery

## Overview

M90 adds graph-aware intelligence and discovery on top of the M89 knowledge graph foundation. The system provides bounded, explainable graph traversal, relationship scoring, entity connections, and frontend UI without introducing new infrastructure.

## Architecture

All graph features reuse the existing M89 relationship table and PostgreSQL. No graph database (Neo4j, etc.) is used. Traversal is performed via bounded breadth-first search (BFS) over the relationship table.

### Bounded Traversal

All graph operations are bounded by:
- `max_depth`: Maximum traversal depth (default: 3)
- `max_nodes`: Maximum nodes to visit (default: 50)
- `max_edges`: Maximum edges to traverse (default: 100)
- `max_paths`: Maximum paths to return (default: 10)

### Conflict Awareness

Graph scoring is conflict-aware:
- `DISPUTED` relationships reduce the connection score
- `RETRACTED` and `INACTIVE` relationships are excluded from traversal
- `VERIFIED` relationships receive a score boost

### Scoring Signals

Connection signals include:
- `SHARED_COMPANY`, `SHARED_TOPIC`, `SHARED_CATEGORY`, `SHARED_STORY`
- `VERIFIED_RELATIONSHIP`, `DISPUTED_RELATIONSHIP`
- `MULTIPLE_SOURCES`, `RECENT_CONNECTION`, `STRONG_CONNECTION`

## API Endpoints

### `GET /api/v1/public/graph/entities/{entity_type}/{entity_id}/connections`

Returns graph connections for a specific entity.

**Parameters:**
- `entity_type`: `company`, `topic`, or `category`
- `entity_id`: Entity UUID
- `limit`: Maximum connections to return (default: 20, max: 100)
- `max_depth`: Maximum traversal depth (default: 3)
- `signals`: Comma-separated list of connection signals to filter by

### `GET /api/v1/public/graph/story-clusters/{story_cluster_id}/connections`

Returns graph connections for a story cluster, including companies, topics, and other entities connected to the cluster's articles.

### `GET /api/v1/public/graph/path/{source_type}/{source_id}/{target_type}/{target_id}`

Returns explainable paths between two entities.

**Parameters:**
- `source_type`: `company`, `topic`, or `category`
- `source_id`: Source entity UUID
- `target_type`: `company`, `topic`, or `category`
- `target_id`: Target entity UUID
- `max_paths`: Maximum paths to return (default: 5)
- `max_depth`: Maximum traversal depth (default: 3)

## Frontend Integration

### Story Cluster Page

The story cluster page now displays a "Knowledge Connections" section that shows:
- Companies connected to the cluster
- Topics connected to the cluster
- Relationship types (e.g., `MENTIONS`, `RELATED_TO`)
- Disputed/retracted status badges
- Connection signals and explanations

### Types Added

- `GraphConnection`: Represents a graph connection with entity info, relationship type, score, signals, and status
- `EntityConnectionsResponse`: Wraps connections with pagination metadata

### API Client Methods

- `graphConnections(entityType, entityId, params?)`: Fetches connections for an entity
- `storyClusterGraphConnections(storyClusterId)`: Fetches connections for a story cluster

## Conflict Awareness

Graph connections respect conflict status:
- `DISPUTED` relationships are included but flagged with a visual badge and reduced score
- `RETRACTED` and `INACTIVE` relationships are excluded from results
- `VERIFIED` relationships receive a score boost

## Separation from Other Systems

- Graph relevance is separate from M87 recommendation score
- Graph relevance is separate from M68 ranking
- Graph features work with `AI_ENABLED=false`
- No ML embeddings or behavioral tracking are used

## Tests

- 18 unit tests for `GraphIntelligenceService`
- 5 unit tests for graph API routes
- All tests pass

## Files Modified

- `src/ai_news_digest/application/services/graph_intelligence/graph_intelligence_service.py` (new)
- `src/ai_news_digest/api/v1/routes/graph.py` (new)
- `src/ai_news_digest/api/v1/schemas/graph.py` (new)
- `src/ai_news_digest/api/v1/routes/public.py` (extended)
- `src/ai_news_digest/api/v1/schemas/public.py` (extended)
- `src/ai_news_digest/bootstrap/container.py` (extended)
- `src/ai_news_digest/domain/ports/category_repository.py` (extended)
- `src/ai_news_digest/infrastructure/database/repositories/category_repository.py` (extended)
- `src/ai_news_digest/main.py` (extended)
- `frontend/src/types.ts` (extended)
- `frontend/src/api/index.ts` (extended)
- `frontend/src/pages/public/StoryClusterPage.tsx` (extended)
- `tests/unit/application/services/graph_intelligence/test_graph_intelligence_service.py` (new)
- `tests/unit/api/v1/routes/test_graph.py` (new)
