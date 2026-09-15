# M89 Knowledge Graph & Entity Relationship Intelligence

## Executive Summary

Milestone 89 introduces knowledge graph entity relationship intelligence to the AI News Digest platform. The implementation adds relationship extraction between companies, topics, stories, and articles—with mandatory provenance tracking, deduplication, and graceful degradation when AI is disabled (`AI_ENABLED=false`).

**Commit:** pending  
**Branch:** main  
**Status:** COMPLETE

## What Was Done

### Backend

1. **Domain Enums** (`src/ai_news_digest/domain/enums/`)
   - `entity_type.py`: `EntityType` — COMPANY, TOPIC, STORY, ARTICLE
   - `relationship_type.py`: `RelationshipType` — RELATED_TO, COMPETES_WITH, PARTNERS_WITH, COLLABORATES_WITH, USES_TECHNOLOGY, PROVIDES_TECHNOLOGY_TO, ANNOUNCED, MENTIONED_WITH, ACQUIRED, ACQUIRED_BY, INVESTS_IN
   - `relationship_status.py`: `RelationshipStatus` — CANDIDATE, VERIFIED, DISPUTED, RETRACTED, INACTIVE

2. **Domain Model** (`src/ai_news_digest/domain/models/relationship.py`)
   - `Relationship`: entity relationship with subject/object, type, status, confidence, provenance, and AI metadata
   - `ProvenanceSource`: DETERMINISTIC or AI_EXTRACTED

3. **Database Model** (`src/ai_news_digest/infrastructure/database/models/relationship_model.py`)
   - `RelationshipModel`: SQLAlchemy ORM model with unique constraint on canonical relationship
   - Indexed columns: subject/object entity type+id, relationship type, status, provenance, timestamps

4. **Migration** (`migrations/versions/029_add_knowledge_graph_relationships.py`)
   - Creates `relationships` table with PostgreSQL native enum types
   - Unique constraint `uq_relationship_canonical` prevents duplicate relationships
   - Indexes for entity lookups, provenance queries, and temporal sorting

5. **Repository** (`src/ai_news_digest/infrastructure/database/repositories/relationship_repository.py`)
   - `SqlAlchemyRelationshipRepository`: CRUD operations, entity lookups, canonical deduplication
   - Converts between domain model and database model with proper enum handling

6. **API Routes** (`src/ai_news_digest/api/v1/routes/relationships.py`)
   - `GET /api/v1/relationships/entities/{entity_type}/{entity_id}` — relationships for an entity
   - `GET /api/v1/relationships/story-clusters/{cluster_id}` — relationships for a story cluster

7. **API Schemas** (`src/ai_news_digest/api/v1/schemas/relationship.py`)
   - `RelationshipResponse`: public API schema with all relationship fields

8. **Extraction Use Case** (`src/ai_news_digest/application/use_cases/knowledge_graph/extract_relationships.py`)
   - `RelationshipExtractionUseCase`: deterministic + AI extraction
   - Deterministic rules: article→company (company_ids), article→topic (topic_ids), article→category
   - AI extraction via `ProviderManager` with M78 circuit breaker and M79 quota integration
   - Deduplication via canonical relationship lookup before creation

9. **Celery Tasks** (`src/ai_news_digest/workers/tasks/knowledge_graph.py`)
   - `extract_article_relationships`: async task for article relationship extraction
   - `extract_story_cluster_relationships`: async task for story cluster relationship extraction

10. **Configuration** (`src/ai_news_digest/core/config.py`)
    - `knowledge_graph_enabled`: bool (default: false)
    - `knowledge_graph_max_relationships_per_article`: int (default: 10)
    - `knowledge_graph_max_relationships_per_story`: int (default: 20)
    - `knowledge_graph_max_nodes`: int (default: 500)
    - `knowledge_graph_max_edges`: int (default: 1000)

11. **Container** (`src/ai_news_digest/bootstrap/container.py`)
    - Wired `relationship_repository` and `extract_relationships` use case

### Frontend

1. **Types** (`frontend/src/types.ts`)
   - Added `RelationshipResponse` interface
   - Added `relationships` field to `PublicStoryCluster`

2. **API Client** (`frontend/src/api/index.ts`)
   - Added `publicApi.entityRelationships(type, id)`
   - Added `publicApi.storyClusterRelationships(clusterId)`

3. **StoryClusterPage** (`frontend/src/pages/public/StoryClusterPage.tsx`)
   - Added "Knowledge Connections" section displaying entity relationships

### Tests

- `tests/unit/domain/models/test_relationship.py`: 9 tests (enum values, creation, status update, AI provenance)
- `tests/unit/application/use_cases/knowledge_graph/test_extract_relationships.py`: 3 tests (deterministic extraction, disabled flag, deduplication)

Total: 12 new tests, all passing.

## Architecture Decisions

### Reuse Existing Entities

Relationships reference existing `companies`, `topics`, `stories`, and `articles` tables by ID. No duplicate `CompanyNode` or `TopicNode` tables are created. This keeps the data model normalized and avoids synchronization issues.

### Mandatory Provenance

Every relationship records its provenance source (DETERMINISTIC or AI_EXTRACTED) and, for AI-extracted relationships, the provider, model, and prompt version. This enables audit trails and trust scoring.

### Deduplication

The `uq_relationship_canonical` unique constraint prevents duplicate relationships. The repository's `get_canonical` method checks for existing relationships before creation.

### Graceful Degradation

- `knowledge_graph_enabled=false` → extraction is skipped entirely
- `AI_ENABLED=false` → only deterministic rules produce relationships
- No AI provider available → deterministic fallback only

### No New Infrastructure

No graph database, no external knowledge import, no additional infrastructure dependencies. Relationships are stored in a single PostgreSQL table.

## Quality Gates

- **Ruff**: All checks passed on M89 files
- **MyPy**: No issues found in M89 modules
- **Pytest**: 12/12 M89 tests passed; 2201/2201 affected regression tests passed
- **TypeScript**: Compilation clean
- **Frontend Build**: Successful

## Known Limitations

1. Only deterministic rules implemented for article→company and article→topic relationships; AI extraction is scaffolded but requires provider integration
2. Relationship confidence is not yet computed (placeholder for future scoring)
3. No relationship pruning or archival policy yet
4. Frontend Knowledge Connections section is minimal; graph visualization not implemented
