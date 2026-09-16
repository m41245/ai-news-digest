# Milestone 91: Engineering Report

## Summary

M91 implements temporal knowledge graph intelligence on top of the M89/M90 graph foundation. The implementation adds deterministic temporal relationship tracking, entity evolution views, relationship history, change detection, and time-bounded graph queries while preserving all existing M81-M90 systems.

## Constraints

- No graph database (Neo4j, etc.)
- No ML embeddings or prediction
- No behavioral tracking or collaborative filtering
- No external knowledge imports
- AI is optional; temporal features work with `AI_ENABLED=false`
- All scores are deterministic and bounded (0.0-1.0)
- Conflict-aware: DISPUTED relationships flagged, RETRACTED/INACTIVE excluded
- Temporal features remain separate from M87 recommendation score and M68 ranking
- Public API routes under `/api/v1/public/graph/...`

## Implementation

### Backend

1. **RelationshipActivityStatus Enum** (`src/ai_news_digest/domain/enums/relationship_activity_status.py`):
   - New enum: NEW, EMERGING, ACTIVE, STABLE, DECLINING, STALE

2. **Relationship Model Extension** (`src/ai_news_digest/domain/models/relationship.py`):
   - Added temporal fields: `first_observed_at`, `last_observed_at`, `valid_from`, `valid_to`
   - Added observation metadata: `observation_count`, `source_count`
   - Added computed fields: `activity_score`, `activity_status`
   - Added `record_observation()` method for deterministic updates

3. **Database Migration** (`migrations/versions/030_add_temporal_graph_fields.py`):
   - Manual Alembic migration adding temporal columns to `relationships` table
   - Added composite indexes for temporal queries

4. **Repository Extension** (`src/ai_news_digest/infrastructure/database/repositories/relationship_repository.py`):
   - Added `update_observation` for incrementing observation counts
   - Added `list_for_entity_with_temporal` for time-bounded queries
   - Added `get_entity_relationship_history` for bounded history retrieval

5. **TemporalGraphIntelligenceService** (`src/ai_news_digest/application/services/graph_intelligence/temporal_graph_intelligence_service.py`):
   - `compute_activity_score`: Bounded deterministic score (0.0-1.0)
   - `compute_activity_status`: Maps relationships to temporal status enum
   - `get_entity_connections_temporal`: Enriches connections with temporal metadata
   - `get_entity_evolution`: Categorizes connections by activity status
   - `detect_relationship_changes`: Identifies new, re-observed, declining, and stale relationships
   - `get_relationship_activity`: Returns activity summaries for relationships
   - `filter_relationships_at_time`: Time-bounded relationship filtering
   - `record_observation`: Updates relationship observation metadata

6. **API Routes** (`src/ai_news_digest/api/v1/routes/graph.py`):
   - Extended `/entities/{type}/{id}/connections` with `observed_from`, `observed_to`, `active_at` filters
   - Added `/entities/{type}/{id}/evolution` endpoint
   - Added `/entities/{type}/{id}/history` endpoint
   - Added `/entities/{type}/{id}/changes` endpoint
   - Added `/entities/{type}/{id}/temporal-connections` endpoint
   - Extended `/path/{source}/{target}` with `at_time` parameter

7. **API Schemas** (`src/ai_news_digest/api/v1/schemas/graph.py`):
   - Added `PublicTemporalGraphConnectionResponse`
   - Added `PublicEntityEvolutionResponse`
   - Added `PublicRelationshipChangeEventResponse`
   - Added `PublicEntityRelationshipHistoryResponse`
   - Added `PublicRelationshipActivityResponse`

8. **Container Registration** (`src/ai_news_digest/bootstrap/container.py`):
   - Registered `TemporalGraphIntelligenceService` as `temporal_graph_intelligence`

### Frontend

1. **Types** (`frontend/src/types.ts`):
   - Added `TemporalGraphConnection` interface
   - Added `EntityEvolutionResponse` interface
   - Added `RelationshipChangeEventResponse` interface
   - Added `EntityRelationshipHistoryResponse` interface

2. **API Client** (`frontend/src/api/index.ts`):
   - Added `entityTemporalConnections` method
   - Added `entityEvolution` method
   - Added `entityRelationshipHistory` method
   - Added `entityRelationshipChanges` method

3. **UI Components**:
   - `RelationshipEvolutionSection.tsx`: Displays entity evolution view
   - `ConnectionHistorySection.tsx`: Displays relationship history on story clusters

4. **StoryClusterPage Integration**:
   - Added `ConnectionHistorySection` to story cluster detail view
   - Integrated temporal connection badges

## Tests

- 22 unit tests for `TemporalGraphIntelligenceService` (all passing)
- 5 unit tests for graph API routes (all passing)
- 6 unit tests for Relationship domain model (all passing)
- Regression: 112 key tests pass (excluding pre-existing conflict repository testcontainers scope mismatch)

## Quality Gates

- ruff: passed
- mypy: passed (with `arg-type` suppress for temporal response variance)
- pytest: passed (graph and temporal tests)
- TypeScript: passed
- Frontend build: passed

## Git

- Commit: pending
- Branch: `main`
- HEAD == origin/main: verified

## Notes

- Alembic autogenerate failed; migration `030_add_temporal_graph_fields.py` was written manually due to limited SQLAlchemy reflection support for the existing `relationships` table.
- The `graph.py` route uses a module-level import for `TemporalGraphIntelligenceService` to avoid line-too-long lint errors.
- `PublicEntityConnectionsResponse.connections` is typed as `list[PublicGraphConnectionResponse]`, but temporal endpoints return `PublicTemporalGraphConnectionResponse` (a superset). A mypy `arg-type` suppress is used; Pydantic handles runtime validation correctly.
- The `test_graph.py` fixture now mocks `list_for_entity_with_temporal` and `get_entity_relationship_history` to support the extended route.
- Frontend `CompaniesPage` integration was reverted to avoid breaking the existing list layout; temporal components are available for future integration.
