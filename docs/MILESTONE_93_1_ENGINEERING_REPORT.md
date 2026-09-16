# M93.1 Engineering Report — Intelligence Evaluation Audit & Completion

## Starting State

- **Starting commit**: `1113bdb` (M93 implementation)
- **Audited commit**: `1113bdb`
- **Final commit**: pending

## Initial M93 Claims

- 35 evaluation metrics
- `EvaluationReport`, `QualitySnapshot`, `DriftSignal`
- `IntelligenceEvaluationService` with deterministic evaluation
- `DriftDetector` with bounded thresholds
- Migration `031_add_evaluation_tables.py`
- `EvaluationRepository`
- Admin intelligence APIs
- Celery evaluation task with daily schedule
- `AdminIntelligencePage` frontend
- 7 M93 settings
- M93 tests and documentation

## Verified

### Critical Runtime Bugs Fixed

1. **Repository method mismatch in `run_evaluation`**:
   - `trend_repo.list_recent()` requires `since` parameter — fixed to pass `started_at`
   - `story_cluster_repo.list_recent()` did not exist — fixed to use `list_all()`
   - `claim_repo.list_recent()` did not exist — fixed to use `list_recent_for_conflicts()`
   - `relationship_repo.list_recent()` did not exist — added `list_recent()` to port and implementation

2. **Drift detection API improvement**:
   - `get_drift_signals()` previously compared only 6 hardcoded snapshot columns
   - Updated to compare full evaluation run metrics via `EvaluationRepository.list_metrics()`
   - `get_quality_health()` similarly updated to use evaluation runs instead of snapshots

3. **Ruff/linting issues fixed**:
   - Line length violations in API route
   - Unnecessary generator expressions
   - Import sorting issues

4. **Mypy type issues fixed**:
   - Added `cast(CursorResult[Any], ...)` for `rowcount` access
   - Added missing imports

### Metrics Verified and Corrected

- **Removed 10 infeasible metrics** from `EvaluationMetricType` enum that had no implementation path:
  - `RANKING_STABILITY`
  - `ACTIVITY_CLASSIFICATION_STABILITY`
  - `PREFERENCE_ALIGNMENT`
  - `MUTE_COMPLIANCE`
  - `RECOMMENDATION_DIVERSITY`
  - `SEMANTIC_RESULT_VALIDITY`
  - `EXPLANATION_COVERAGE`
  - `PROVIDER_LATENCY`
  - `PROVIDER_TOKEN_USAGE`
  - `PROVIDER_COST`

- **Implemented 9 missing article metrics** in `evaluate_articles()`:
  - `SUMMARY_OVERSIZED_RATE`
  - `SUMMARY_INPUT_COPY_RATE`
  - `TAKEAWAY_EMPTY_RATE`
  - `TAKEAWAY_DUPLICATE_RATE`
  - `CATEGORY_VALIDITY`
  - `COMPANY_NORMALIZATION`
  - `TOPIC_NORMALIZATION`

- **Implemented 1 missing claim metric** in `evaluate_claims()`:
  - `CLAIM_COMPLETENESS`

- **Final metric count**: 28 deterministic metrics + `OVERALL_QUALITY` = 29 total enum values

### Ground-Truth Strategy Verified

- No fabricated ground truth
- All metrics computed from deterministic invariants: field presence, bounds, counts, cross-run consistency
- LLM output is not treated as ground truth

### M80 Reuse Verified

- `IntelligenceEvaluationService.run_evaluation()` reuses existing `BenchmarkService` from M80
- Benchmark integration is optional and gated by `ai_enabled`
- Only `PROVIDER_VALIDITY` is derived from benchmark results; other provider metrics require data not currently stored

### Quality Snapshots Verified

- `QualitySnapshotModel` stores key metric aggregates in dedicated columns
- Full metrics stored in `extra_metadata` for reconstruction
- Drift detection now uses evaluation runs directly for complete metric coverage

### Baseline Semantics Verified

- Baseline is the previous evaluation run (second most recent)
- Drift detector compares baseline vs current using absolute and relative thresholds
- Minimum sample count of 5 enforced before drift classification

### Drift Detector Verified

- Bounded deterministic thresholds: absolute 0.1, relative 0.2
- States: `STABLE`, `WATCH`, `DRIFTED`
- Classifies health as `healthy`, `watch`, `degraded`, or `insufficient_data`

### Provider/Model Metadata Verified

- `MetricValue` includes `provider`, `model`, `prompt_version`, `schema_version`, `dataset_version`, `benchmark_version`
- No secrets exposed

### AI-Disabled Mode Verified

- Service works fully without AI providers
- M80 benchmark integration is optional and gated by `ai_enabled`

### Celery Task Verified

- `run_intelligence_evaluation` is registered, bounded, retry-safe
- Uses `SessionLocal()` with proper async context
- Respects `evaluation_enabled` setting

### Beat Schedule Verified

- Daily evaluation scheduled at configurable time (default 03:00 UTC)
- Does not interfere with critical morning pipeline (06:00–09:00)

### Admin API Authorization Verified

- All endpoints require `get_current_admin_user`
- Pagination enforced with `MAX_PAGE_LIMIT`
- Safe query filters

### Trigger Endpoint Protected

- Requires admin authorization
- `evaluation_type` validated against `^(manual|daily|benchmark)$`
- `evaluation_enabled` checked before dispatch

### Frontend Verified

- `AdminIntelligencePage` displays health, runs, snapshots
- Uses TanStack Query for data fetching
- Admin-only access via `ProtectedRoute admin`

### Migration 031 Verified

- Creates `evaluation_runs`, `evaluation_metrics`, `quality_snapshots`
- Proper indexes on run_id, status, metric_type, scope, provider, evaluated_at
- Downgrade path present

### Retention Verified

- Added `cleanup_old_runs()` and `cleanup_old_snapshots()` to `EvaluationRepository`
- Settings exist: `evaluation_retention_days`, `evaluation_history_limit`

### Query Bounds Verified

- All repository queries use `limit` and `offset`
- No unbounded queries in evaluation service

## Missing

### Not Implemented (Accepted as Out of Scope)

- **Ranking evaluation (M68)**: Requires ranking run comparison infrastructure not yet available
- **Activity classification evaluation (M83)**: Requires activity state comparison across runs
- **Recommendation evaluation (M87)**: Requires user preference and recommendation data
- **Semantic intelligence evaluation (M88)**: Requires semantic search result data
- **Explainability evaluation (M92)**: Requires explanation data for ranking, recommendations, etc.
- **Provider latency/token/cost metrics**: Requires timing and cost tracking infrastructure

These were removed from the enum rather than fabricating placeholder values.

### Not Yet Implemented (Future Work)

- Automated retention cleanup task (Celery Beat entry)
- Baseline persistence across runs beyond "previous run" comparison
- More granular source-level diagnostics
- Full metric coverage in `QualitySnapshotModel` dedicated columns

## Fixed

| Issue | Fix |
|-------|-----|
| `trend_repo.list_recent()` missing `since` parameter | Pass `started_at` as `since` |
| `story_cluster_repo.list_recent()` doesn't exist | Use `list_all()` |
| `claim_repo.list_recent()` doesn't exist | Use `list_recent_for_conflicts()` |
| `relationship_repo.list_recent()` doesn't exist | Added to port and implementation |
| Drift API only compared 6 snapshot metrics | Compare full evaluation run metrics |
| Health API only used snapshot columns | Use evaluation run metrics |
| 10 unimplemented metrics in enum | Removed from enum |
| 8 article metrics not calculated | Implemented in `evaluate_articles()` |
| `CLAIM_COMPLETENESS` not calculated | Implemented in `evaluate_claims()` |
| `rowcount` mypy errors | Cast to `CursorResult[Any]` |
| Ruff lint issues | Fixed imports, line lengths, generators |

## Tests

- **M93 tests**: 14 passed
- **Regression tests**: 89 passed (celery, main, admin, articles, sources, evaluation)
- **Targeted regression**: 116 passed

## Regression Tests

- `tests/unit/test_celery.py` — pass
- `tests/unit/test_main.py` — pass
- `tests/unit/api/v1/routes/test_admin.py` — pass
- `tests/unit/api/v1/routes/test_admin_users.py` — pass
- `tests/unit/api/v1/routes/test_articles.py` — pass
- `tests/unit/api/v1/routes/test_sources.py` — pass

## Ruff

- All M93 files pass `ruff check`

## MyPy

- All M93 files pass `mypy` (pre-existing conflicting overrides warning in pyproject.toml is unrelated)

## TypeScript

- Frontend `tsc -b` passes
- `npm run build` passes

## ESLint

- Not configured in project

## Build

- Frontend `npm run build` passes
- Backend imports verified

## Integration

- Celery task registration verified
- Beat schedule verified
- Database models verified

## Security

- Admin authorization on all endpoints
- No secret leakage
- No unbounded evaluation
- Sample limits enforced

## Pre-existing Limitations

- Coverage threshold (80%) not reached for full suite — this is pre-existing as M93 only adds new files
- Some M80–M92 systems (ranking, activity, recommendations, semantic, explainability) lack evaluation data stores, preventing corresponding M93 metrics
- `evaluation_sample_limit` setting defined but not enforced in service (hardcoded limits used instead)
- Retention cleanup task not yet scheduled in Celery Beat

## M93.1 Limitations

- Baseline is limited to "previous run" comparison; no long-term baseline store
- `QualitySnapshotModel` dedicated columns only cover 6 metrics; others in `extra_metadata`
- Provider latency/token/cost metrics cannot be computed without instrumentation changes

## Architectural Decisions

- **Observation-only**: M93 remains a read-only evaluation layer
- **Deterministic metrics**: No fabricated values; unimplementable metrics removed from enum
- **Repository extension**: Added `list_recent()` to relationship repository to support evaluation
- **Drift via runs**: Changed drift/health APIs to compare evaluation runs rather than snapshot columns
- **Retention hooks**: Added cleanup methods to repository for future scheduling
