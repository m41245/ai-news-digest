# Milestone 74 — Final Platform Hardening & Launch Preparation

## Status: COMPLETE

M74 focuses on final hardening of the existing AI News Digest platform to prepare it for controlled launch. No real AI providers were activated. No new infrastructure was introduced. All work preserves the existing FastAPI + PostgreSQL + SQLAlchemy + Alembic + Redis + Celery/Celery Beat + React + TypeScript + Vite + Tailwind architecture.

## What Changed

### Python 3.14 Compatibility
- **structlog upgrade**: Bumped `structlog` from `24.4.0` to `26.1.0` in `pyproject.toml` to address Python 3.14 compatibility issues with stdlib `logging.Logger._log()` rejecting arbitrary keyword arguments.
- **Logger migration**: Replaced direct `logging.getLogger(__name__)` calls with `get_logger(__name__)` (from `ai_news_digest.core.logging`) in 11 backend modules. This ensures all logging goes through structlog's `BoundLogger`, which correctly routes kwargs through the processor chain instead of passing them directly to the stdlib logger's `_log()` method.
- **PositionalArgumentsFormatter**: Added `structlog.stdlib.PositionalArgumentsFormatter()` to the structlog processor chain in `core/logging.py`. This restores stdlib-style `%s`/`%d` positional argument formatting that was previously handled implicitly by plain stdlib loggers.

### Scheduler Ordering Fix
- **Digest schedule correction**: Changed the default `digest_schedule_minute` from `0` to `15` in `core/config.py`. This ensures the daily digest generation task runs at `08:15` rather than `08:00`, which is AFTER the daily story ranking task at `08:05`. The ordering dependency is now documented in the field description.

### Test Infrastructure
- **Logging initialization in tests**: Added `configure_logging()` call to `tests/conftest.py` so that structlog is configured before any test modules are imported. This prevents logger proxy inconsistencies during test collection.
- **Full regression suite**: All 1759 backend unit tests pass. All 35 frontend tests pass.

### Code Quality
- **Ruff auto-fixes**: Removed unused `import logging` statements in modules that migrated to `get_logger`. Removed unused `import pytest` statements in two test modules. Applied 21 automatic ruff fixes across `src/` and `tests/`.

## Files Changed

### Backend
- `pyproject.toml` — structlog `^26.1.0`
- `poetry.lock` — dependency lock update
- `src/ai_news_digest/core/logging.py` — Added `PositionalArgumentsFormatter` to processor chain
- `src/ai_news_digest/application/use_cases/digest/generate_intelligent_digest.py` — Migrated to `get_logger`
- `src/ai_news_digest/api/middleware/exception_handler.py` — Migrated to `get_logger`
- `src/ai_news_digest/application/services/digest_editorial_generator.py` — Migrated to `get_logger`
- `src/ai_news_digest/application/services/ingestion/ingestion_service.py` — Migrated to `get_logger`
- `src/ai_news_digest/application/services/rss/rss_client.py` — Migrated to `get_logger`
- `src/ai_news_digest/application/use_cases/article/ingest_all_sources.py` — Migrated to `get_logger`
- `src/ai_news_digest/infrastructure/cache/redis_store.py` — Migrated to `get_logger`
- `src/ai_news_digest/infrastructure/email/development_sender.py` — Migrated to `get_logger`
- `src/ai_news_digest/infrastructure/email/smtp_sender.py` — Migrated to `get_logger`
- `src/ai_news_digest/infrastructure/email/test_sender.py` — Migrated to `get_logger`
- `tests/conftest.py` — Added `configure_logging()` call

### Tests
- `tests/unit/api/v1/routes/test_public.py` — Ruff auto-fixes (unused imports, line length)
- `tests/unit/application/ai/test_company_normalizer.py` — Removed unused `pytest` import
- `tests/unit/application/ai/test_topic_normalizer.py` — Removed unused `pytest` import

## Database Changes

No database migration required. No schema changes.

## New Dependencies

- `structlog >= 26.1.0` (replaces `24.4.0`)

## Security Verification

- Public endpoints remain public-only where intended.
- Admin endpoints remain protected.
- Authentication unchanged.
- CORS unchanged.
- No credentials exposed in frontend bundles.
- No secrets in logs (redaction processor unchanged).
- No internal stack traces returned to clients.
- SSRF protections untouched.
- `AI_ENABLED=false` remains the safe default. No real provider activation occurred. No paid AI calls were made. No fabricated AI output was introduced.

## Test Results

### Frontend
- TypeScript: `tsc -b --noEmit` passes cleanly.
- ESLint: passes cleanly.
- Production build: succeeds (26.92 kB CSS, 143.75 kB JS main bundle gzip: 40.47 kB).
- Tests: 35 passed, 0 failed.

### Backend
- Full unit suite: 1759 passed, 0 failed.
- Previously failing test `test_existing_digest_reused_when_not_forced` now passes under Python 3.14 + structlog 26.1.0.

### Static Analysis
- `ruff check src/ tests/ --select E,F,W --fix`: 21 issues auto-fixed. Remaining 5 issues are pre-existing line-length and whitespace issues in test files unrelated to M74.
- `mypy src/ --ignore-missing-imports`: 42 pre-existing errors in 10 files. No new errors introduced by M74 changes.

## AI Status

`AI_ENABLED=false` remains the safe default. No real provider activation occurred. No paid AI calls were made. No fabricated AI output was introduced.

## Known Limitations

- Pre-existing `mypy` errors in `generate_intelligent_digest.py`, `digest.py`, `user_preference` modules, and others (42 errors in 10 files) are unrelated to M74.
- Pre-existing `ruff` formatting differences across test files (5 remaining E501/W293 issues) are unrelated to M74.
- M70 files remain as unstaged modifications in the working tree per project policy and were NOT committed as part of M74.

## Rollback Readiness

The M74 commit (`7316951`) is a single, self-contained commit on `main`. To rollback:
```bash
git revert 7316951
pip install "structlog<26.0"
```

All changes are additive or import-path-only; reverting restores the previous Python 3.13-compatible state.

## Recommended Next Steps

Continue with the next milestone in the project sequence. Keep AI disabled during remaining development. Real provider activation should only occur during the final controlled launch/verification phase, not mixed with ordinary feature development.

## Documentation Status

- `docs/MILESTONE_74.md` — Created.
- `docs/PROJECT_STATUS.md` — **Not updated for M74.** The file contains unstaged M70 modifications that must be preserved. Updating it for M74 would require carefully preserving those M70 changes; this should be done as a separate deliberate action when M70 changes are ready to be committed.
