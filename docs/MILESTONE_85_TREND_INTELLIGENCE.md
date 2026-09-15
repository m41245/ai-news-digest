# M85 — Trend Detection and Emerging Story Intelligence

## Overview

Trend Detection and Emerging Story Intelligence (M85) identifies rising topics, companies, categories, and story clusters across the AI news digest pipeline. It provides deterministic, explainable trend scoring and a public `/trends` endpoint.

## Acceptance Criteria

- [x] Trend domain model with canonical identity
- [x] Deterministic scoring algorithm with configurable weights
- [x] Trend status derived from scores (EMERGING / RISING / SUSTAINED / COOLING / STALE)
- [x] Source diversity and story cluster integration
- [x] M83 story activity integration
- [x] M84 story event integration
- [x] Idempotent persistence with unique canonical_key
- [x] Celery task with bounded retries and metrics
- [x] Public API endpoints (`GET /api/v1/public/trends`, `GET /api/v1/public/trends/{id}`)
- [x] Frontend page (`/trends`) with filtering
- [x] Unit tests pass (15 M85-specific tests)
- [x] Regression tests pass (M83/M84)
- [x] Ruff clean, mypy clean for new files
- [x] Documentation and engineering report
- [x] Git commit and push

## Status

**COMPLETE** — 2026-09-15

## Key Design Decisions

- Deterministic first: no AI required; optional AI routed through `ProviderManager`
- No vector/graph database; pure SQL + bounded in-memory evaluation
- Single `trends` table with unique `canonical_key`
- Prefetch-optimized queries (2 article queries per run instead of 6)

## Files

- Design doc: `docs/MILESTONE_85_TREND_INTELLIGENCE.md`
- Engineering report: `docs/MILESTONE_85_ENGINEERING_REPORT.md`
- Source: `src/ai_news_digest/...`
- Tests: `tests/unit/...`
- Frontend: `frontend/src/pages/public/TrendsPage.tsx`, `frontend/src/components/TrendCard.tsx`

## Verification

- M85 tests: 15 passed
- Regression tests: 51 passed
- Frontend build: successful
- Lint: clean for new files
- MyPy: clean for new files
