# Milestone 91: Temporal Knowledge Graph & Entity Evolution Intelligence

## Overview

M91 extends the M89/M90 graph infrastructure with deterministic temporal relationship tracking, entity evolution views, and bounded historical queries. All temporal signals are derived from existing relationship observation metadata without introducing new infrastructure or external data sources.

## Architecture

All temporal features reuse the existing M89 relationship table and PostgreSQL. No graph database, no ML embeddings, and no behavioral tracking are introduced. Temporal intelligence is computed deterministically from `first_observed_at`, `last_observed_at`, `observation_count`, `source_count`, and `valid_from`/`valid_to` fields.

### Relationship Activity Status

Each relationship is assigned a temporal activity status:

- `NEW`: First observed within the emerging window (default: 48 hours)
- `EMERGING`: Observed 2+ times within the emerging window
- `ACTIVE`: Observed 3+ times within the active window (default: 7 days)
- `STABLE`: Observed beyond active window without significant recent acceleration
- `DECLINING`: Older observations with reduced recent activity
- `STALE`: No recent supporting observation (default: 14 days)

### Activity Score

Activity score is a bounded deterministic value (0.0-1.0) composed of:

- Recency: 0.0-0.4 (based on hours since last observation)
- Observation frequency: 0.0-0.3 (capped at 10 observations)
- Source diversity: 0.0-0.2 (capped at 5 sources)
- Confidence: 0.0-0.1 (from relationship confidence field)

Retracted or expired relationships (`valid_to` in the past) receive a score of 0.0.

### Entity Evolution View

The evolution view categorizes an entity's connections into:

- `new_connections`: Relationships with `NEW` status
- `recently_active`: Relationships with `ACTIVE` or `EMERGING` status
- `recently_changed`: Relationships with `STABLE` status
- `historical_connections`: Relationships with `DECLINING` or `STALE` status

### Bounded Queries

All temporal queries are bounded:

- Maximum 50 history items per request
- Maximum 20 evolution items displayed
- Maximum 200 relationships fetched for analysis
- Temporal filtering uses ISO datetime strings (`observed_from`, `observed_to`, `active_at`)

## API Endpoints

### `GET /api/v1/public/graph/entities/{entity_type}/{entity_id}/connections`

Extended with temporal filtering parameters:

- `observed_from`: Filter relationships observed after this ISO datetime
- `observed_to`: Filter relationships observed before this ISO datetime
- `active_at`: Filter relationships active at this ISO datetime

### `GET /api/v1/public/graph/entities/{entity_type}/{entity_id}/evolution`

Returns temporal evolution view for an entity, categorizing connections by activity status.

### `GET /api/v1/public/graph/entities/{entity_type}/{entity_id}/history`

Returns bounded relationship history for an entity, ordered by observation time.

### `GET /api/v1/public/graph/entities/{entity_type}/{entity_id}/changes`

Returns detected relationship change events (new connections, re-observations, status changes).

### `GET /api/v1/public/graph/entities/{entity_type}/{entity_id}/temporal-connections`

Returns graph connections enriched with temporal metadata (activity score, status, observation counts).

### `GET /api/v1/public/graph/path/{source_type}/{source_id}/{target_type}/{target_id}`

Extended with `at_time` parameter to evaluate path existence at a specific point in time.

## Data Model Changes

### Relationship Model

Extended with temporal fields:

- `first_observed_at`: When the relationship was first observed
- `last_observed_at`: When the relationship was last observed
- `valid_from`: When the relationship became valid
- `valid_to`: When the relationship expired (null = still valid)
- `observation_count`: Number of times the relationship has been observed
- `source_count`: Number of independent sources supporting the relationship
- `activity_score`: Computed temporal activity score (0.0-1.0)
- `activity_status`: Computed temporal activity status enum

### RelationshipActivityStatus Enum

New enum with values: `NEW`, `EMERGING`, `ACTIVE`, `STABLE`, `DECLINING`, `STALE`

## Frontend Integration

### Types Added

- `TemporalGraphConnection`: Graph connection enriched with temporal metadata
- `EntityEvolutionResponse`: Entity evolution view with categorized connections
- `RelationshipChangeEventResponse`: Detected relationship change event
- `EntityRelationshipHistoryResponse`: Bounded relationship history

### Components

- `RelationshipEvolutionSection`: Displays entity evolution view on company/topic pages
- `ConnectionHistorySection`: Displays relationship history on story cluster pages

## Constraints

- No graph database
- No ML embeddings or prediction
- No behavioral tracking or collaborative filtering
- No external knowledge imports
- AI is optional; temporal features work with `AI_ENABLED=false`
- All scores are deterministic and bounded
- Conflict-aware: DISPUTED relationships are flagged, RETRACTED/INACTIVE excluded
- Temporal features are separate from M87 recommendation score and M68 ranking

## Files Modified

- `src/ai_news_digest/domain/enums/relationship_activity_status.py` (new)
- `src/ai_news_digest/domain/models/relationship.py` (extended)
- `src/ai_news_digest/domain/ports/relationship_repository.py` (extended)
- `src/ai_news_digest/infrastructure/database/models/relationship_model.py` (extended)
- `src/ai_news_digest/infrastructure/database/repositories/relationship_repository.py` (extended)
- `migrations/versions/030_add_temporal_graph_fields.py` (new)
- `src/ai_news_digest/application/services/graph_intelligence/temporal_graph_intelligence_service.py` (new)
- `src/ai_news_digest/api/v1/routes/graph.py` (extended)
- `src/ai_news_digest/api/v1/schemas/graph.py` (extended)
- `src/ai_news_digest/api/v1/schemas/relationship.py` (extended)
- `src/ai_news_digest/bootstrap/container.py` (extended)
- `frontend/src/types.ts` (extended)
- `frontend/src/api/index.ts` (extended)
- `frontend/src/components/RelationshipEvolutionSection.tsx` (new)
- `frontend/src/components/ConnectionHistorySection.tsx` (new)
- `frontend/src/pages/public/StoryClusterPage.tsx` (extended)
- `tests/unit/application/services/graph_intelligence/test_temporal_graph_intelligence_service.py` (new)
- `tests/unit/api/v1/routes/test_graph.py` (extended)
