# M93 — Intelligence Evaluation, Quality Monitoring & Drift Detection

## Status
Accepted

## Architecture
M93 is an observability layer over M80–M92 intelligence systems. It does not modify production intelligence algorithms.

## Domain Model
- `EvaluationMetricType`: bounded enum of measurable metrics
- `EvaluationStatus`: PENDING, RUNNING, COMPLETED, FAILED
- `DriftState`: STABLE, WATCH, DRIFTED
- `EvaluationReport`: structured evaluation results
- `QualitySnapshot`: bounded historical quality record
- `DriftSignal`: drift detection result

## Metrics
Structured output validity, summary presence/rate/length, takeaway count, category/company/topic normalization, claim quality, evidence attachment, conflict detection, cluster stability, ranking stability, activity stability, trend distribution, preference alignment, provenance completeness, explanation coverage, extraction success, provider metrics.

## Ground Truth Strategy
No fabricated ground truth. Metrics are computed from deterministic invariants (field presence, bounds, counts) and cross-run consistency. LLM output is not treated as ground truth.

## Benchmark Integration
Reuses M80 benchmark infrastructure. Benchmark results are recorded with version metadata (dataset, metric, prompt, schema versions).

## Quality Snapshots
Bounded historical snapshots stored in PostgreSQL with key metric aggregates.

## Baseline and Drift
Drift detection compares current window vs baseline window using absolute and relative thresholds. Configurable via settings.

## API
- `GET /api/v1/admin/intelligence/evaluations` — list runs
- `GET /api/v1/admin/intelligence/evaluations/{id}` — run detail
- `GET /api/v1/admin/intelligence/quality/snapshots` — list snapshots
- `GET /api/v1/admin/intelligence/drift` — drift signals
- `GET /api/v1/admin/intelligence/quality/health` — health status
- `POST /api/v1/admin/intelligence/evaluations/run` — trigger evaluation

## Configuration
- `evaluation_enabled`: master switch
- `evaluation_sample_limit`: max items per evaluation
- `evaluation_history_limit`: max retained runs/snapshots
- `evaluation_retention_days`: retention period
- `drift_absolute_threshold`: absolute drift threshold
- `drift_relative_threshold`: relative drift threshold
- `evaluation_schedule_hour/minute`: Celery Beat schedule

## Scheduling
Runs at configured time (default 03:00 UTC), outside the critical morning pipeline.

## AI Behavior
Works with `AI_ENABLED=false`. Deterministic metrics require no provider. M80 benchmark integration is optional and bounded.

## Celery
Uses existing Celery app. Task is bounded, retry-safe, and non-destructive.

## Tests
- Domain model tests
- Service tests (articles, claims, clusters, trends, relationships, extraction)
- Drift detection tests
- API route tests
- AI-disabled behavior tests

## Limitations
- No factual accuracy without ground truth
- No autonomous optimization
- No behavioral tracking
- No graph database
