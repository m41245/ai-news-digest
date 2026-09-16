# M93 Engineering Report

## Implementation Summary

M93 — Intelligence Evaluation, Quality Monitoring & Drift Detection — has been implemented as an observability layer over the existing M80–M92 intelligence systems. No production intelligence algorithms were modified.

## Files Created

### Domain Layer
- `src/ai_news_digest/domain/evaluation/__init__.py` — package exports
- `src/ai_news_digest/domain/evaluation/metrics.py` — domain models (enums, dataclasses)

### Application Layer
- `src/ai_news_digest/application/services/intelligence_evaluation_service.py` — deterministic metric computation
- `src/ai_news_digest/application/services/drift_detector.py` — bounded drift detection

### Infrastructure Layer
- `src/ai_news_digest/infrastructure/database/models/evaluation_run_model.py` — evaluation run ORM model
- `src/ai_news_digest/infrastructure/database/models/evaluation_metric_model.py` — evaluation metric ORM model
- `src/ai_news_digest/infrastructure/database/models/quality_snapshot_model.py` — quality snapshot ORM model
- `src/ai_news_digest/infrastructure/database/repositories/evaluation_repository.py` — persistence operations

### Migration
- `migrations/versions/031_add_evaluation_tables.py` — Alembic migration for evaluation tables

### API Layer
- `src/ai_news_digest/api/v1/schemas/intelligence_evaluation.py` — Pydantic response schemas
- `src/ai_news_digest/api/v1/routes/intelligence_evaluation.py` — admin REST endpoints
- `src/ai_news_digest/api/v1/routes/__init__.py` — router export

### Workers
- `src/ai_news_digest/workers/tasks/evaluation.py` — Celery task for scheduled evaluation

### Frontend
- `frontend/src/types.ts` — TypeScript interfaces (evaluation types appended)
- `frontend/src/api/index.ts` — admin evaluation API methods
- `frontend/src/pages/admin/AdminIntelligencePage.tsx` — admin intelligence page
- `frontend/src/App.tsx` — route for `/admin/intelligence`

### Tests
- `tests/unit/domain/evaluation/test_metrics.py` — domain model tests
- `tests/unit/application/services/test_intelligence_evaluation_service.py` — service tests
- `tests/unit/application/services/test_drift_detector.py` — drift detector tests
- `tests/unit/api/v1/routes/test_intelligence_evaluation.py` — API route tests

## Files Modified

- `src/ai_news_digest/bootstrap/container.py` — added evaluation repository and services
- `src/ai_news_digest/core/config.py` — added M93 configuration fields
- `src/ai_news_digest/workers/celery_app.py` — added evaluation task to include list and beat schedule
- `src/ai_news_digest/main.py` — registered intelligence evaluation router

## Static Checks

- `ruff check` — passed on all new files
- `mypy` — passed on all new files
- `pytest` — 14 tests passed

## Key Design Decisions

1. **Deterministic metrics**: All metrics are computed from field presence, bounds, and counts. No LLM output is treated as ground truth.
2. **AI_ENABLED=false compatibility**: The service works fully without AI providers. M80 benchmark integration is optional and gated by `ai_enabled`.
3. **Non-destructive observation**: The evaluation service reads production data only. It does not modify articles, claims, clusters, or any other intelligence artifacts.
4. **Bounded drift detection**: Uses simple absolute and relative thresholds with minimum sample counts. No heavyweight statistical tests.
5. **Scheduled outside critical path**: Evaluation runs at 03:00 UTC by default, well outside the morning intelligence pipeline.

## Test Results

```
14 passed, 4 warnings in 30.68s
```

All unit tests for M93 pass successfully.
