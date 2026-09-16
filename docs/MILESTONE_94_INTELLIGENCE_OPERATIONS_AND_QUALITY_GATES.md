# M94 Intelligence Operations and Quality Gates

## Overview

M94 adds operational reliability controls to the AI News Digest intelligence pipeline. It provides deterministic quality gate evaluation, health aggregation, operational alerting, and safe automated safeguards — without modifying any production intelligence algorithms.

## What Changed

### New Capabilities

- **Quality Gates**: Configurable PASS/WARN/FAIL/INSUFFICIENT_DATA gates for extraction success, structured validity, provenance completeness, and evidence coverage
- **Health Aggregation**: Component-level and overall health status with deterministic precedence (BLOCKED > DEGRADED > INSUFFICIENT_DATA > UNKNOWN)
- **Operational Alerts**: Deduplicated alerting for quality gate failures with resolve actions
- **Automated Evaluation**: Daily Celery beat task (`daily-quality-gate-evaluation` at 04:00 UTC) for unattended quality monitoring
- **Admin API**: New endpoints under `/api/v1/intelligence/*` for health, gates, definitions, alerts, and evaluation triggering

### Configuration

New settings in `src/ai_news_digest/core/config.py`:
- `quality_gates_enabled` — master switch for quality gate system
- `quality_gate_evaluation_enabled` — enable/disable automated evaluation
- `minimum_evaluation_samples` — minimum samples before gate evaluation
- `extraction_success_threshold`, `structured_validity_threshold`, `provenance_completeness_threshold`, `evidence_coverage_threshold` — gate thresholds
- `drift_gate_enabled` — enable drift-based quality gates
- `alert_retention_days` — bounded retention for operational alerts
- `quality_gate_history_limit` — bounded history for gate results

### Database

New tables via migration `032_add_quality_gates_and_alerts.py`:
- `quality_gate_results` — individual gate evaluation results
- `operational_alerts` — deduplicated operational alerts
- `component_health_snapshots` — time-series health snapshots

### Frontend

Updated `AdminIntelligencePage.tsx` with M94 UI sections for:
- Overall health status and component breakdown
- Quality gate results with filtering
- Operational alerts with resolve actions
- Manual quality gate evaluation trigger

## Constraints Honored

- No changes to intelligence ranking weights, prompts, provider priorities, source trust, or recommendation scoring
- Full compatibility with `AI_ENABLED=false`
- Reuses existing abstractions: health endpoints, Celery, circuit breakers (M78), quota (M79), M93 evaluation infrastructure
- All new persistent records have bounded retention
- Admin-only endpoints with bounded pagination/filters

## Validation

- Unit tests: 30 passed
- Ruff: passed on all new/modified files
- Mypy: passed on all new/modified files
- Frontend: `tsc --noEmit` passed, `npm run lint` passed, `npm run build` passed
- Migration: `alembic heads` confirms revision `032` is current head
