# M85 Engineering Report — Trend Detection and Emerging Story Intelligence

## Status

**ACCEPTED**

## Implementation Completed

All acceptance criteria for M85 — Trend Detection and Emerging Story Intelligence have been met. The milestone is fully implemented, tested, linted, type-checked, built, and verified.

## Architecture

M85 follows the existing hexagonal architecture:

- **Domain**: `Trend` model, `TrendType` enum, `TrendStatus` enum, `TrendRepository` port
- **Application**: `DetectTrendsUseCase` orchestrating deterministic trend detection
- **Infrastructure**: SQLAlchemy model (`TrendModel`), mapper, repository implementation
- **Workers**: Celery task `detect_trends` with bounded retries and metrics
- **API**: Public endpoints `GET /api/v1/public/trends` and `GET /api/v1/public/trends/{trend_id}`
- **Frontend**: `TrendsPage` with filtering and `TrendCard` components

## Trend Model

- `id`: UUID
- `trend_type`: TrendType enum (TOPIC_TREND, COMPANY_TREND, CATEGORY_TREND, STORY_TREND, EMERGING_TREND)
- `canonical_key`: str (unique identity, e.g. `company:openai`, `topic:llm`)
- `display_name`: str
- `status`: TrendStatus enum (EMERGING, RISING, SUSTAINED, COOLING, STALE)
- `trend_score`: float (0.0 to 100.0, deterministic weighted composite)
- `momentum_score`: float (0.0 to 100.0, deterministic momentum signal)
- `recent_activity`: int (article count in recent window)
- `baseline_activity`: int (article count in baseline window)
- `source_count`: int (unique trusted sources)
- `story_count`: int (distinct story clusters)
- `event_count`: int (recent story events)
- `first_detected_at`: datetime
- `last_detected_at`: datetime
- `trend_metadata`: dict[str, str] (JSON-serialized diagnostic metadata)
- `explanation`: str (deterministic human-readable breakdown)
- `created_at`: datetime
- `updated_at`: datetime

## Trend Types

- `TOPIC_TREND` — genuine increase in topic activity
- `COMPANY_TREND` — company mention acceleration
- `CATEGORY_TREND` — category-wide activity shift
- `STORY_TREND` — story cluster acceleration
- `EMERGING_TREND` — reserved for future cross-entity emergent patterns

## Trend Status

Status is deterministic from `trend_score`:

- `EMERGING` — score >= 65
- `RISING` — score >= 50
- `SUSTAINED` — score >= 35
- `COOLING` — score >= 20
- `STALE` — score < 20 or zero recent activity

## Scoring Algorithm

Deterministic, bounded, explainable scoring with configurable weights:

- `trend_activity_weight` (default 0.25) — recent article volume
- `trend_growth_weight` (default 0.25) — acceleration vs baseline
- `trend_source_diversity_weight` (default 0.20) — unique trusted sources
- `trend_story_growth_weight` (default 0.10) — story cluster diversity
- `trend_event_weight` (default 0.05) — story event activity
- `trend_recency_weight` (default 0.10) — hours since latest article
- `trend_activity_boost_weight` (default 0.05) — M83 activity status (BREAKING/DEVELOPING)

All signals are normalized to [0.0, 1.0] before weighting. Final scores are bounded to [0.0, 100.0].

Momentum score emphasizes growth and recency:
- 50% growth signal
- 30% recency signal
- 20% activity boost

## Source Diversity

Uses existing `Source` identity/trust architecture. Only `is_active` and `status == verified` sources count toward diversity. Multiple independent publishers strengthen a trend; single-publisher spikes are dampened by the diversity signal.

## StoryCluster Integration

Story clusters contribute via:
- New articles in the recent window
- Independent source diversity within the cluster
- New StoryEvents (M84)
- M83 activity status (BREAKING/DEVELOPING boosts)

## StoryActivity Integration (M83)

`StoryActivity.status` of `BREAKING` or `DEVELOPING` provides an activity boost proportional to `activity_score`. Activity status is a signal, not ground truth.

## StoryEvent Integration (M84)

Recent `StoryEvent` count per cluster contributes to `event_count` and the event signal. Events are counted per-cluster and bounded by query limit.

## Activity Windows

Configurable via Settings:
- `trend_recent_window_hours` (default 24, range 1-720)
- `trend_baseline_window_hours` (default 168, range 1-720)
- `trend_min_recent_activity` (default 3, range 1-100)
- `trend_min_sources` (default 2, range 1-50)
- `trend_max_candidates_per_type` (default 50, range 1-500)
- `trend_max_total_candidates` (default 200, range 1-1000)

## Persistence

- Unique canonical identity via `canonical_key` unique constraint
- Idempotent upsert on `canonical_key`
- Safe metadata serialization (JSON with fallback to empty dict)
- Bounded integer fields with server defaults
- Useful indexes: `status`, `trend_score`, `last_detected_at`, `canonical_key`

## Migration 026

Alembic migration `026_add_trends.py`:
- Creates `trends` table with all domain fields
- Adds indexes: `ix_trends_status`, `ix_trends_trend_score`, `ix_trends_last_detected_at`, `ix_trends_canonical_key`
- Supports full downgrade (drop indexes, drop table)
- Verified upgrade/downgrade/re-upgrade cycle

## Use Case

`DetectTrendsUseCase.execute()`:
1. Build trusted source ID set
2. Build activity map from recent StoryActivity
3. Fetch recent and baseline articles once (optimized from 6 queries to 2)
4. Collect bounded candidates for companies, topics, categories, story clusters
5. Evaluate each candidate: compute scores, derive status, build explanation
6. Upsert trends idempotently
7. Return summary dict

## Performance

Optimized DB access:
- Reduced article queries from 6 per run to 2 per run
- Pre-fetches recent and baseline articles, filters in memory
- Bounded candidate limits prevent runaway evaluation
- Uses existing PostgreSQL aggregation via SQLAlchemy

## Celery

- Task: `workers.tasks.trend.detect_trends`
- Registered in `celery_app.py` include list
- Beat schedule: daily at 08:12 (after M83 story activity at 08:10, before digest at 08:15)
- Bounded retries: max 2, default delay 120s
- Metrics recorded via existing metrics infrastructure
- M42-safe DB lifecycle via container pattern

## API

New public endpoints:
- `GET /api/v1/public/trends` — paginated list with filters
  - Query params: `limit`, `offset`, `trend_type`, `status`, `min_score`
  - Response: `PaginatedResponse[PublicTrendSearchResponse]`
- `GET /api/v1/public/trends/{trend_id}` — single trend detail
  - Response: `PublicTrendResponse` with `trend_metadata`

No exposure of raw article content, internal prompts, provider secrets, or operational data.

## Frontend

- Route: `/trends`
- Components: `TrendsPage`, `TrendCard`
- Features:
  - Trend name, status, scores, source count, story count
  - Filtering by trend type and status
  - Loading, empty, and error states
  - Responsive grid layout
  - No fake data

## AI Behavior

- Core detection is fully deterministic and requires no AI
- Works with `AI_ENABLED=false`
- Optional AI for trend naming or explanation must go through `ProviderManager`
- No direct provider calls from domain or application layers

## Security

- No new external services
- No unsafe string construction in SQL
- All inputs bounded by configuration limits
- Canonical keys are lowercase, alphanumeric with separators
- Metadata is JSON-serialized with type-safe fallbacks

## Files Changed

### New Files
- `docs/MILESTONE_85_TREND_INTELLIGENCE.md`
- `docs/MILESTONE_85_ENGINEERING_REPORT.md`
- `migrations/versions/026_add_trends.py`
- `frontend/src/components/TrendCard.tsx`
- `frontend/src/pages/public/TrendsPage.tsx`
- `src/ai_news_digest/application/use_cases/trend/detect_trends.py`
- `src/ai_news_digest/domain/enums/trend_status.py`
- `src/ai_news_digest/domain/enums/trend_type.py`
- `src/ai_news_digest/domain/models/trend.py`
- `src/ai_news_digest/domain/ports/trend_repository.py`
- `src/ai_news_digest/infrastructure/database/mappers/trend_mapper.py`
- `src/ai_news_digest/infrastructure/database/models/trend_model.py`
- `src/ai_news_digest/infrastructure/database/repositories/trend_repository.py`
- `src/ai_news_digest/workers/tasks/trend.py`
- `tests/unit/api/v1/routes/test_trends.py`
- `tests/unit/application/use_cases/trend/test_detect_trends.py`
- `tests/unit/domain/models/test_trend.py`
- `tests/unit/workers/tasks/test_trend.py`

### Modified Files
- `frontend/src/App.tsx`
- `frontend/src/api/index.ts`
- `frontend/src/types.ts`
- `src/ai_news_digest/api/v1/routes/public.py`
- `src/ai_news_digest/api/v1/schemas/public.py`
- `src/ai_news_digest/bootstrap/container.py`
- `src/ai_news_digest/core/config.py`
- `src/ai_news_digest/workers/celery_app.py`

## Exact Tests and Results

### M85-Specific Tests (15 tests)

- `tests/unit/domain/models/test_trend.py` — domain model, clamping, timestamps, score updates
- `tests/unit/application/use_cases/trend/test_detect_trends.py` — disabled, no candidates, high growth, idempotency, status thresholds
- `tests/unit/api/v1/routes/test_trends.py` — list paginated, get by ID, not found
- `tests/unit/workers/tasks/test_trend.py` — disabled returns status, use case unavailable returns status

**Result**: 15 passed, 5 warnings in 20.43s

### Regression Tests (51 tests)

- `tests/unit/domain/test_story_activity_model.py` — M83 story activity model
- `tests/unit/workers/tasks/test_story_activity.py` — M83 story activity task
- `tests/unit/application/use_cases/story_cluster/test_story_intelligence.py` — M67/M68 story intelligence

**Result**: 51 passed, 4 warnings in 20.00s

## Lint/Typecheck Results

### Ruff
- M85-specific files: clean (only pre-existing issues in `public.py`, `container.py`, `config.py`)
- All E501, F401, F821, S110 issues in M85 files resolved

### MyPy
- M85-specific files: clean
- Remaining errors are pre-existing in `public.py` (conflict detection code)

## Frontend Build

- `npm run build` (vite build): successful
- TypeScript: 4 pre-existing unused-import errors in `api/index.ts` (used via `import()` expressions)
- TrendsPage imports corrected to match existing page patterns

## Known Limitations

- Trend detection uses in-memory filtering for entity matching; very large candidate sets may require DB-level aggregation
- `trend_metadata` is a flat `dict[str, str]`; complex metadata would require schema evolution
- StoryEvent lookup is per-cluster with limit=100; extremely active clusters may miss events
- AI-assisted trend naming/explanation is not yet implemented (deferred to future milestone)

## Architectural Decisions

- **Deterministic first**: All scoring is deterministic; AI is optional and routed through ProviderManager
- **No ML/vector/graph DB**: Pure SQL + in-memory filtering
- **Single table**: Trends use one table with unique canonical_key, no join tables
- **Prefetch optimization**: Reduced from 6 to 2 article queries per run
- **UUID-safe filtering**: Filter methods convert string IDs to UUIDs for comparison with Article relationship fields
- **Defensive event counting**: StoryEvent failures are logged at debug level and skipped, not fatal

## AI Disabled Verification

Trend detection functions fully with `AI_ENABLED=false`. No provider calls are made. All signals are derived from article counts, source diversity, story clusters, and story activity/events.

## Commit

Pending: `feat(M85): add trend and emerging story intelligence`
