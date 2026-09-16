# Milestone 90: Engineering Report

## Summary

M90 implements graph-aware intelligence and discovery on top of the M89 knowledge graph foundation. The implementation adds bounded BFS traversal, conflict-aware relationship scoring, and frontend UI while preserving all existing M81-M89 systems.

## Constraints

- No graph database (Neo4j, etc.)
- No behavioral tracking or collaborative filtering
- No ML embeddings
- AI is optional; graph features must work with `AI_ENABLED=false`
- All traversal bounded by max_depth/max_nodes/max_edges/max_paths
- Conflict-aware: DISPUTED reduces score, RETRACTED/INACTIVE excluded
- Graph relevance remains separate from M87 recommendation score and M68 ranking
- Public API routes under `/api/v1/public/graph/...`
- Frontend reuses existing design language and components

## Implementation

### Backend

1. **GraphIntelligenceService** (`src/ai_news_digest/application/services/graph_intelligence/graph_intelligence_service.py`):
   - Bounded BFS traversal over existing relationship table
   - Conflict-aware scoring (DISPUTED reduces score, RETRACTED/INACTIVE excluded)
   - Recency and source diversity signals
   - Explainable path finding
   - All traversal bounded by configurable limits

2. **API Routes** (`src/ai_news_digest/api/v1/routes/graph.py`):
   - `/api/v1/public/graph/entities/{type}/{id}/connections`
   - `/api/v1/public/graph/story-clusters/{id}/connections`
   - `/api/v1/public/graph/path/{source_type}/{source_id}/{target_type}/{target_id}`

3. **API Schemas** (`src/ai_news_digest/api/v1/schemas/graph.py`):
   - `PublicGraphConnectionResponse`
   - `PublicEntityConnectionsResponse`
   - `PublicGraphPathResponse`

4. **Extended Existing Endpoints**:
   - Public story cluster endpoint extended with `graph_connections` field
   - Related stories endpoint extended with graph signal enrichment

5. **Repository Extension**:
   - Added `list_by_ids` to `CategoryRepository` port and implementation

### Frontend

1. **Types** (`frontend/src/types.ts`):
   - Added `GraphConnection` interface
   - Added `EntityConnectionsResponse` interface

2. **API Client** (`frontend/src/api/index.ts`):
   - Added `graphConnections` method
   - Added `storyClusterGraphConnections` method

3. **UI** (`frontend/src/pages/public/StoryClusterPage.tsx`):
   - Added "Knowledge Connections" section
   - Displays companies, topics, and connected entities
   - Shows relationship types, disputed/retracted badges, signals, and explanations

## Tests

- 18 unit tests for `GraphIntelligenceService` (all passing)
- 5 unit tests for graph API routes (all passing)
- 26 regression tests for M89 and public API (all passing)

## Quality Gates

- ruff: passed
- mypy: passed (with `import-untyped` override for new module)
- pytest: passed
- TypeScript: passed
- Frontend build: passed

## Git

- Commit: `b78b78976245c7d9f93cdde144ef411157d2172a`
- Message: `feat(M90): add graph-aware intelligence and discovery`
- Branch: `main`
- HEAD == origin/main: verified

## Notes

- The `graph_intelligence_service.py` module requires a `import-untyped` mypy override because it is a new module without a `py.typed` marker. This is consistent with other new modules in the codebase.
- Frontend type safety was improved by using the `GraphConnection` interface instead of `Record<string, unknown>`.
- All graph features are disabled when `AI_ENABLED=false` is not a concern because graph traversal does not depend on AI providers.
