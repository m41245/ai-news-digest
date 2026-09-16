# M94 Intelligence Operations and Quality Gates

## Overview

M94 adds operational reliability controls to the AI News Digest intelligence pipeline. It provides deterministic quality gate evaluation, health aggregation, operational alerting, and safe automated safeguards — without modifying any production intelligence algorithms.

## What Changed

### New Capabilities

- **Quality Gates**: Configurable PASS/WARN/FAIL/INSUFFICIENT_DATA gates for extraction success, structured validity, provenance completeness, and evidence coverage
- **Health Aggregation**: Component-level and overall health status with deterministic precedence (BLOCKED > DEGRADED > INSUFFICIENT_DATA > UNKNOWN)
- **Operational Alerts**: Deduplicated alerting for quality gate failures with resolve actions and automatic recovery
- **Automated Evaluation**: Daily Celery beat task (`daily-quality-gate-evaluation` at 04:00 UTC) for unattended quality monitoring
- **Admin API**: New endpoints under `/api/v1/intelligence/*` for health, gates, definitions, alerts, and evaluation triggering

### Configuration

New settings in `src/ai_news_digest/core/config.py`:
- `quality_gates_enabled` — master switch for quality gate system
- `quality_gate_evaluation_enabled` — enable/disable automated evaluation
- `minimum_evaluation_samples` — minimum samples before gate evaluation
- `extraction_success_threshold`, `structured_validity_threshold`, `provenance_completeness_threshold`, `evidence_coverage_threshold` — gate thresholds
- `quality_gate_warning_margin` — fraction below threshold that yields WARN instead of FAIL (0.0 disables WARN)
- `drift_gate_enabled` — enable drift-based quality gates
- `alert_retention_days` — bounded retention for operational alerts
- `quality_gate_history_limit` — bounded history for gate results

### Database

New tables via migration `032_add_quality_gates_and_alerts.py`:
- `quality_gate_results` — individual gate evaluation results
- `operational_alerts` — deduplicated operational alerts
- `component_health_snapshots` — time-series health snapshots with drift state

### Frontend

Updated `AdminIntelligencePage.tsx` with M94 UI sections for:
- Overall health status and component breakdown
- Quality gate results with filtering
- Operational alerts with resolve actions
- Manual quality gate evaluation trigger

## M94.1 Corrective Work

M94.1 fixed gaps between the original M94 implementation and runtime-wired behavior:
- WARN gate results are now deterministically generated based on `quality_gate_warning_margin`
- Drift detection is now integrated into the M94 Celery task using M93's `DriftDetector`
- Automatic alert recovery resolves open alerts when component gates recover
- `quality_gate_history_limit` is enforced in repository queries
- Fixed `OperationalAlertModel.resolved` type mismatch (bool → int)
- Added baseline evaluation retrieval for drift comparison
- Fixed pre-existing migration test defect

## Constraints Honored

- No changes to intelligence ranking weights, prompts, provider priorities, source trust, or recommendation scoring
- Full compatibility with `AI_ENABLED=false`
- Reuses existing abstractions: health endpoints, Celery, circuit breakers (M78), quota (M79), M93 evaluation infrastructure
- All new persistent records have bounded retention
- Admin-only endpoints with bounded pagination/filters

## Validation

- Unit tests: 70 passed (M94/M93/migration)
- Ruff: no new issues introduced
- Mypy: no new issues introduced
- Frontend: `tsc --noEmit` passed, `npm run lint` passed, `npm run build` passed
- Migration: test confirms revision `032` is importable and chain-consistent
