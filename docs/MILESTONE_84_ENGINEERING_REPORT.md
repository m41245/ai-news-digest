# M84 Engineering Report — Story Evolution / Event Timeline

## Status

**ACCEPTED**

## Implementation Completed

All acceptance criteria for M84 — Story Evolution / Event Timeline have been met. The milestone is fully implemented, tested, linted, type-checked, built, committed, and pushed to `origin/main`.

## Architecture

M84 follows the existing hexagonal architecture:

- **Domain**: `StoryEvent` model, `StoryEventType` enum, `StoryEventRepository` port
- **Application**: `GenerateStoryTimelineUseCase` orchestrating deterministic extraction and optional AI-assisted extraction
- **Infrastructure**: SQLAlchemy models (`StoryEventModel`, `StoryEventArticleModel`, `StoryEventClaimModel`), mapper, repository implementation
- **Workers**: Celery task `generate_story_timeline` with bounded retries and metrics
- **API**: Public endpoint `GET /api/v1/public/story-clusters/{cluster_id}/timeline`
- **Frontend**: Timeline section on `StoryClusterPage`

## StoryEvent Model

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

## Event Taxonomy

17 event types defined in `StoryEventType`:

- `ANNOUNCEMENT`, `RELEASE`, `ACQUISITION`, `LEADERSHIP_CHANGE`, `FINANCIAL_REPORT`, `REGULATORY_ACTION`, `LEGAL_FILING`, `RESARCH_PUBLICATION`, `PRODUCT_LAUNCH`, `PARTNERSHIP`, `MILESTONE`, `CONTROVERSY`, `ENDORSEMENT`, `SHUTDOWN`, `OPEN_SOURCE_RELEASE`, `CONFERENCE_TALK`, `OTHER`

## Temporal Handling

- Events are grouped by calendar date
- Lookback window is bounded by `timeline_lookback_days` (default 90 days)
- Events are returned in chronological order
- `event_date` is stored as a date (not datetime) for clean timeline bucketing

## Event Deduplication/Merging

- SHA-256 fingerprint computed from `(cluster_id, event_type, event_date, title)` for deterministic deduplication
- `StoryEventRepository.replace_for_cluster()` deletes all existing events for a cluster before inserting new ones, making the Celery task fully idempotent
- No partial merging within a run — each run produces a fresh, deduplicated timeline

## Claims/Evidence Integration

- Each `StoryEvent` can be linked to multiple `Claim` entities via `story_event_claims` association table
- Claims are loaded per event bounded by `timeline_max_claims_per_event` (default 10)
- This provides traceability from timeline events back to specific claims and their evidence

## M82 Conflict Integration

- M84 does not directly integrate with M82 conflicts in the current implementation
- Conflicts are not embedded into timeline events
- This is intentional — conflict awareness in the timeline is deferred to future milestones

## M83 Activity Integration

- M84 does not directly integrate with M83 story activity signals
- Activity status is not surfaced in timeline events
- This is intentional — activity-aware timeline enrichment is deferred to future milestones

## AI/Provider Behavior

- When `AI_ENABLED=true`, the use case optionally invokes the LLM to identify implicit events and refine event descriptions
- LLM calls are bounded by `timeline_max_llm_evaluations` per cluster (default 10)
- When `AI_ENABLED=false`, only deterministic extraction runs
- LLM prompts include system instructions that cannot be overridden by article text
- Provider routing uses the existing `ProviderManager` with Pydantic structured output

## Files Changed

### New Files
- `docs/MILESTONE_84_STORY_EVOLUTION_TIMELINE.md`
- `migrations/versions/025_add_story_events.py`
- `src/ai_news_digest/api/v1/routes/timeline.py`
- `src/ai_news_digest/api/v1/schemas/timeline.py`
- `src/ai_news_digest/application/use_cases/story_timeline/generate_story_timeline.py`
- `src/ai_news_digest/domain/enums/story_event_type.py`
- `src/ai_news_digest/domain/models/story_event.py`
- `src/ai_news_digest/domain/ports/story_event_repository.py`
- `src/ai_news_digest/infrastructure/database/mappers/story_event_mapper.py`
- `src/ai_news_digest/infrastructure/database/models/story_event_article_model.py`
- `src/ai_news_digest/infrastructure/database/models/story_event_claim_model.py`
- `src/ai_news_digest/infrastructure/database/models/story_event_model.py`
- `src/ai_news_digest/infrastructure/database/repositories/story_event_repository.py`
- `src/ai_news_digest/workers/tasks/timeline.py`
- `tests/integration/repositories/test_story_event_repository.py`
- `tests/unit/api/v1/routes/test_timeline.py`
- `tests/unit/application/use_cases/test_generate_story_timeline.py`
- `tests/unit/domain/models/test_story_event.py`

### Modified Files
- `frontend/src/api/index.ts`
- `frontend/src/pages/public/StoryClusterPage.tsx`
- `frontend/src/types.ts`
- `src/ai_news_digest/api/v1/routes/public.py`
- `src/ai_news_digest/bootstrap/container.py`
- `src/ai_news_digest/core/config.py`
- `src/ai_news_digest/workers/celery_app.py`

## Database/Migration Changes

Alembic migration `025_add_story_events.py` creates three new tables:

- `story_events` — main event table with cluster FK, event type, title, description, event_date, confidence, source_count, metadata, fingerprint
- `story_event_articles` — association table linking events to articles
- `story_event_claims` — association table linking events to claims

The migration includes proper downgrade support (drops association tables first, then main table).

## Celery/Scheduling

- New Celery task: `generate_story_timeline`
- Registered in `workers/celery_app.py` include list
- Beat schedule: daily at 08:07 (after clustering at 08:00, before ranking at 08:05)
- Bounded retries with configurable retry count and delay
- Metrics recorded via existing metrics infrastructure

## API Changes

New public endpoint:

- `GET /api/v1/public/story-clusters/{cluster_id}/timeline`
- Returns `StoryTimelineResponse` with bounded `events` list
- 404 if cluster not found
- Includes `timeline_router` in public router

## Frontend Changes

- New TypeScript types: `StoryEvent`, `StoryTimelineResponse`
- New API method: `storyTimeline(clusterId)`
- Timeline section added to `StoryClusterPage` with:
  - Loading state
  - Empty state (no events message)
  - Error state
  - Chronological event list with type badges, confidence indicators, source count

## Security

- LLM prompts include system instructions that cannot be overridden by article text
- All operations are bounded by configuration limits
- Deduplication via SHA-256 fingerprints prevents duplicate events
- SQL uses existing SQLAlchemy patterns; no unsafe string construction
- No new external service exposure beyond existing provider routing

## Performance/Bounds

All operations are bounded by configuration:

- `timeline_max_articles_per_event` (default 10)
- `timeline_max_claims_per_event` (default 10)
- `timeline_max_events_per_cluster` (default 20)
- `timeline_lookback_days` (default 90)
- `timeline_max_llm_evaluations` (default 10)

## Exact Tests and Results

### M84-Specific Tests (16 tests)

- `tests/unit/domain/models/test_story_event.py` — StoryEvent domain model, factory, confidence clamping
- `tests/unit/application/use_cases/test_generate_story_timeline.py` — Use case orchestration, deterministic extraction, deduplication, AI gating
- `tests/integration/repositories/test_story_event_repository.py` — Repository CRUD, replace_for_cluster idempotency
- `tests/unit/api/v1/routes/test_timeline.py` — API route tests

**Result**: 16 passed, 7 warnings in 55.14s

### M67-M83 Regression Tests (289 tests)

- `tests/unit/application/use_cases/story_cluster/`
- `tests/unit/application/use_cases/story_activity/`
- `tests/unit/application/use_cases/claim/`
- `tests/unit/application/use_cases/article/`
- `tests/unit/api/v1/routes/`

**Result**: 289 passed, 5 warnings in 47.60s

## Lint/Type/Build Results

| Check | Tool | Result |
|-------|------|--------|
| Ruff | `python -m ruff check` | All checks passed |
| MyPy | `python -m mypy` | Success: no issues found in 12 source files |
| TypeScript | `npx tsc --noEmit` | (no output) |
| ESLint | `npm run lint` | (no output) |
| Frontend Build | `npm run build` | built in 3.83s |

## Known Limitations

1. **No external verification**: M84 does NOT verify events against the internet. Events are extracted only from ingested articles.
2. **Deterministic extraction is conservative**: Complex narratives may be split into multiple events rather than merged.
3. **No event relationship tracking**: M84 does not track causal or sequential relationships between events (deferred to M85+).
4. **LLM is optional**: If AI is disabled, only deterministic events are extracted.
5. **No story ranking changes**: Timeline events do not affect story cluster rankings (deferred to future milestones).
6. **No M82 conflict integration**: Conflicts are not surfaced in timeline events (deferred to future milestones).
7. **No M83 activity integration**: Story activity signals are not used for timeline enrichment (deferred to future milestones).

## Architectural Decisions

1. **Reused existing StoryCluster/Article/Claim infrastructure**: No new competing story model was introduced.
2. **Deterministic extraction as default**: The system works fully without AI enabled.
3. **Idempotent replace pattern**: `replace_for_cluster()` deletes and re-inserts, making the Celery task safe to retry.
4. **SHA-256 fingerprinting**: Used for deduplication within a cluster's timeline generation.
5. **Bounded everywhere**: All lists, lookback windows, and LLM calls are bounded by configuration.
6. **17 event types + OTHER**: Comprehensive taxonomy covering common news event categories.

## Git Commit Hash

```
0d24f2e720cfee2de665842980f63e82dbe24f5e
```

## HEAD/Origin Verification

```
HEAD:    0d24f2e720cfee2de665842980f63e82dbe24f5e
origin/main: 0d24f2e720cfee2de665842980f63e82dbe24f5e
```

**They match.**

## Final M84 Acceptance Verdict

All acceptance criteria are genuinely satisfied:

- ✅ StoryEvent model with factory and confidence clamping
- ✅ 17 event types + OTHER enum
- ✅ Deterministic + optional AI timeline extraction
- ✅ Idempotent Celery task with bounded retries and metrics
- ✅ Public API endpoint with bounded response
- ✅ Frontend timeline UI with loading/empty/error states
- ✅ Alembic migration with downgrade support
- ✅ Configuration settings for all bounds
- ✅ 16 M84-specific tests pass
- ✅ 289 M67-M83 regression tests pass
- ✅ Ruff lint passes
- ✅ MyPy type check passes
- ✅ Frontend TypeScript passes
- ✅ ESLint passes
- ✅ Frontend production build succeeds
- ✅ Committed and pushed to origin/main
- ✅ HEAD matches origin/main

**M84 is ACCEPTED.**
