# M84 — Story Evolution / Event Timeline

## Purpose

M84 introduces **story evolution and event timeline** tracking to the platform. The system now extracts temporal events from story clusters and presents them as a structured timeline showing how stories develop over time.

This milestone builds on the existing StoryCluster, Article, Claim, and Conflict infrastructure and:

- Extracts events from articles clustered around a story using deterministic grouping
- Optionally invokes LLM analysis to identify implicit events not obvious from article metadata
- Persists events with associated articles and claims for traceability
- Exposes timeline data via public API
- Renders an interactive timeline in the StoryClusterPage frontend
- Runs as a scheduled Celery task

## Architecture

M84 follows the existing hexagonal architecture:

```
Application
  └── use_cases/story_timeline/
        └── generate_story_timeline.py (orchestration)

Domain
  ├── models/story_event.py
  ├── enums/story_event_type.py
  └── ports/story_event_repository.py

Infrastructure
  ├── database/models/story_event_model.py
  ├── database/models/story_event_article_model.py
  ├── database/models/story_event_claim_model.py
  ├── database/mappers/story_event_mapper.py
  └── database/repositories/story_event_repository.py

Workers
  └── tasks/timeline.py (Celery task)
```

## Story Event Model

### StoryEvent Domain Model

`src/ai_news_digest/domain/models/story_event.py`

A `StoryEvent` represents a discrete event within a story cluster's evolution:

- `id`: UUID
- `story_cluster_id`: UUID
- `event_type`: StoryEventType enum
- `title`: str
- `description`: str
- `event_date`: date
- `confidence`: float (0.0 to 1.0)
- `source_count`: int
- `article_ids`: list[UUID]
- `claim_ids`: list[UUID]
- `metadata`: dict[str, str]
- `fingerprint`: str (SHA-256 deduplication key)
- `created_at`: datetime
- `updated_at`: datetime

### StoryEventType Enum

`src/ai_news_digest/domain/enums/story_event_type.py`

- `ANNOUNCEMENT` — Product, feature, or policy announcements
- `RELEASE` — Software, product, or report releases
- `ACQUISITION` — Company acquisitions or mergers
- `LEADERSHIP_CHANGE` — CEO, board, or key personnel changes
- `FINANCIAL_REPORT` — Earnings, revenue, or funding reports
- `REGULATORY_ACTION` — Regulatory approvals, fines, or investigations
- `LEGAL_FILING` — Lawsuits, patents, or legal documents
- `RESEARCH_PUBLICATION` — Academic papers or research findings
- `PRODUCT_LAUNCH` — New product or service launches
- `PARTNERSHIP` — Strategic partnerships or collaborations
- `MILESTONE` — Project or company milestones
- `CONTROVERSY` — Scandals, criticism, or public disputes
- `ENDORSEMENT` — Support or validation from authorities/experts
- `SHUTDOWN` — Service or product discontinuations
- `OPEN_SOURCE_RELEASE` — Open source code releases
- `CONFERENCE_TALK` — Conference presentations or keynotes
- `OTHER` — Uncategorized events

### StoryEventArticleModel and StoryEventClaimModel

`src/ai_news_digest/infrastructure/database/models/story_event_article_model.py`
`src/ai_news_digest/infrastructure/database/models/story_event_claim_model.py`

Association tables linking events to their supporting articles and claims.

## Event Extraction

### Deterministic Extraction

Events are extracted deterministically from article metadata:

1. Articles are grouped by `story_cluster_id` and filtered by `published_at` within the lookback window
2. Articles are bucketed by calendar date
3. For each date, articles are grouped by `event_type` (derived from article tags/metadata)
4. A `StoryEvent` is created per (date, event_type) group with:
   - Title derived from the most prominent article in the group
   - Description summarizing the group
   - Confidence based on source diversity and article count
   - SHA-256 fingerprint for deduplication

### AI-Assisted Extraction

When `AI_ENABLED=true`, the use case optionally invokes the LLM to:

1. Identify implicit events not obvious from article metadata
2. Assign event types to untagged articles
3. Refine event descriptions with natural language summaries

LLM calls are bounded by `timeline_max_llm_evaluations` per cluster.

## Idempotency

`StoryEventRepository.replace_for_cluster(cluster_id, events)`:

1. Deletes all existing events for the cluster
2. Inserts new events
3. Creates article and claim associations

This makes the Celery task fully idempotent — safe to retry without creating duplicates.

## API Exposure

### Public API

`src/ai_news_digest/api/v1/schemas/timeline.py`

New schemas:

```typescript
StoryEventResponse:
{
  id: string;
  event_type: string;
  title: string;
  description: string;
  event_date: string; // ISO date
  confidence: number;
  source_count: number;
  created_at: string;
}

StoryTimelineResponse:
{
  cluster_id: string;
  events: StoryEventResponse[];
  total_events: number;
}
```

`src/ai_news_digest/api/v1/routes/timeline.py`

New endpoint: `GET /api/v1/public/story-clusters/{cluster_id}/timeline`

Returns the timeline for a story cluster, bounded by `timeline_max_events_per_cluster`.

### Frontend

`frontend/src/types.ts`

New interfaces:

```typescript
interface StoryEvent {
  id: string;
  event_type: string;
  title: string;
  description: string;
  event_date: string;
  confidence: number;
  source_count: number;
  created_at: string;
}

interface StoryTimelineResponse {
  cluster_id: string;
  events: StoryEvent[];
  total_events: number;
}
```

`frontend/src/pages/public/StoryClusterPage.tsx`

Renders a "Story Evolution" timeline section with:

- Chronological list of events
- Event type badges
- Confidence indicators
- Loading, empty, and error states
- API integration via `storyTimeline` method

## Configuration

New settings in `src/ai_news_digest/core/config.py`:

- `timeline_generation_enabled`: bool (default true)
- `timeline_max_articles_per_event`: int (default 10)
- `timeline_max_claims_per_event`: int (default 10)
- `timeline_max_events_per_cluster`: int (default 20)
- `timeline_lookback_days`: int (default 90)
- `timeline_max_llm_evaluations`: int (default 10)

`AI_ENABLED=false` does NOT prevent timeline generation. LLM-assisted extraction is the only feature gated by `AI_ENABLED`.

## Celery Scheduling

A new Celery task `generate_story_timeline`:

- Runs daily at 08:07 (configurable via beat schedule)
- Is idempotent (safe to retry)
- Records metrics (duration, success, failure)
- Returns summary dict with counts

## Security

### Prompt Injection

LLM prompts include system instructions that cannot be overridden by article text. The prompt explicitly states: "Respond with JSON only."

### Resource Exhaustion

All operations are bounded:

- Articles retrieved: bounded by `timeline_max_articles_per_event`
- Claims loaded per event: bounded by `timeline_max_claims_per_event`
- Events per cluster: bounded by `timeline_max_events_per_cluster`
- Lookback window: bounded by `timeline_lookback_days`
- LLM calls: bounded by `timeline_max_llm_evaluations`

### SQL Safety

- Uses existing SQLAlchemy patterns
- Deduplication via SHA-256 fingerprints prevents duplicate events
- No unsafe SQL string construction

## Testing

### Unit Tests Added

- `tests/unit/domain/models/test_story_event.py` — StoryEvent domain model, factory, confidence clamping
- `tests/unit/application/use_cases/test_generate_story_timeline.py` — Use case orchestration, deterministic extraction, deduplication, AI gating
- `tests/unit/api/v1/routes/test_timeline.py` — API route tests

### Integration Tests Added

- `tests/integration/repositories/test_story_event_repository.py` — Repository CRUD, replace_for_cluster idempotency

### Test Results

- All M84 unit tests pass
- All M84 integration tests pass
- Mypy type checking passes cleanly
- Ruff linting passes cleanly

## Known Limitations

1. **No external verification**: M84 does NOT verify events against the internet. Events are extracted only from ingested articles.
2. **Deterministic extraction is conservative**: Complex narratives may be split into multiple events rather than merged.
3. **No event relationship tracking**: M84 does not track causal or sequential relationships between events (deferred to M85+).
4. **LLM is optional**: If AI is disabled, only deterministic events are extracted.
5. **No story ranking changes**: Timeline events do not affect story cluster rankings (deferred to future milestones).

## Future Extensions

- Event relationship graphs (causal chains, dependencies)
- Event significance scoring for ranking
- User-facing event feedback and corrections
- Timeline zoom and filtering in frontend
- Event merging across clusters for cross-story analysis
