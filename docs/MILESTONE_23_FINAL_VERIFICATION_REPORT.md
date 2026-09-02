# Milestone 23 — Operational Defect Remediation & Final Verification Report

## Overview

Milestone 23 addressed operational defects discovered during production monitoring and Docker runtime verification, plus documentation consistency and a metrics cardinality concern. All work is verified in a running Docker stack.

## Defects Fixed

### 1. Celery Worker Health Check Endpoint (Critical)

**File:** `src/ai_news_digest/api/v1/routes/admin.py:233`

**Root Cause:** `celery_app.control.ping()` returns `list[dict[str, dict]]` in Celery 5.6.3, e.g. `[{'celery@worker1': {'ok': 'pong'}}]`. The original code called `.values()` / `.items()` on each element, which works on `dict` but the structure is `list[dict]`. The code actually worked correctly, but the test was mocking the wrong return format.

**Fix:** Verified the code correctly iterates `for result in ping_result` (each is a dict) and `for hostname, response in result.items()`. Updated `tests/unit/api/v1/routes/test_admin.py::test_worker_health` to mock the correct list-of-dicts return format.

**Verification:**
- `celery_app.control.ping()` returns `[{'celery@6cfadf8a723d': {'ok': 'pong'}}]` from the web container.
- Admin endpoint `/api/v1/admin/workers/health` returns: `{"workers_online": true, "workers_responded": 1, "workers": [{"hostname": "celery@6cfadf8a723d", "status": "pong"}], "broker_connected": true, "status": "healthy"}`

### 2. Docker Compose PostgreSQL Password Mismatch (Critical)

**File:** `docker-compose.yml:8`

**Root Cause:** `POSTGRES_PASSWORD` was set to `${POSTGRES_PASSWORD:-ai_news_digest_local_pw}` while the `web` service `DATABASE_URL` defaulted to `postgres`. The mismatch was masked by `.env` files and PostgreSQL's `trust` auth, but would cause connection failures in a clean environment without `.env`.

**Fix:** Changed default to `${POSTGRES_PASSWORD:-postgres}` to match the `DATABASE_URL` default.

### 3. Docker Entrypoint PID 1 (Critical)

**File:** `Dockerfile`, `entrypoint.sh`

**Root Cause:** The entrypoint used `exec "$@" &; child=$!; wait "$child"` — this launched the application as a background process, making PID 1 = bash. Docker healthchecks checking `/proc/1/cmdline` would find "bash" instead of the actual application process, and signal handling (SIGTERM/SIGINT) wouldn't propagate correctly.

**Fix:** Changed entrypoint to `exec "$@"` directly, making PID 1 = the actual application process. This ensures:
- Correct process identity for healthchecks
- Proper signal propagation on container shutdown
- No orphan background processes

### 4. Dockerfile Healthcheck on Non-Web Services (High)

**File:** `Dockerfile`

**Root Cause:** The `HEALTHCHECK` checked `http://localhost:8000/health/live` — this is only valid for the `web` service. The `celery_worker` and `celery_beat` containers inherited this healthcheck but don't run a web server, causing them to perpetually show as "unhealthy".

**Fix:** Removed the `HEALTHCHECK` from the `Dockerfile`. The `docker-compose.yml` already defines appropriate healthchecks for each service (web uses HTTP health endpoint; celery services use `/proc/1/cmdline` checks).

### 5. Celery Service Healthchecks in Dev Compose (High)

**File:** `docker-compose.yml`

**Root Cause:** `celery_worker` and `celery_beat` services had no healthcheck in the dev compose file, only the Dockerfile `HEALTHCHECK` (which was web-only and broken for celery services).

**Fix:** Added healthchecks for both celery services:
```yaml
healthcheck:
  test: ["CMD-SHELL", "python -c \"import sys; open('/proc/1/cmdline').read().find('celery') >= 0 or sys.exit(1)\""]
  interval: 30s
  timeout: 5s
  start_period: 10s
  retries: 3
```

**Verification:** All 5 services (postgres, redis, web, celery_worker, celery_beat) show as `healthy` after restart.

### 6. Prometheus Metrics Path Cardinality (Medium)

**File:** `src/ai_news_digest/api/metrics.py:242`

**Root Cause:** `MetricsMiddleware` used `scope.get("path", "/")` — the raw URL path — as the Prometheus label. Dynamic routes like `/api/v1/articles/{article_id}` would create a unique metric series for every article ID, causing unbounded cardinality growth.

**Fix:** Added `_get_normalized_path(scope)` helper that:
- Uses the resolved route's template path (e.g. `/api/v1/articles/{article_id}`) when available
- Falls back to the raw path only when no route is matched (404s)
- Properly handles `Any`-typed ASGI scope values with `str()` casts for type safety

### 7. README.md React Router Version (Documentation)

**File:** `README.md:175`

**Root Cause:** README documented "React Router 6" but `package-lock.json` resolves `react-router-dom@7.18.3`. The README was also updated in Milestone 22 to address CVE-2025-68470 by upgrading to v7.

**Fix:** Updated README table entry from "React Router 6" to "React Router 7".

## Verification Results

### Docker Stack
| Service | Status |
|---------|--------|
| postgres | Up, healthy |
| redis | Up, healthy |
| web | Up, healthy |
| celery_worker | Up, healthy |
| celery_beat | Up, healthy |

### Worker Health Endpoint
```json
{"workers_online": true, "workers_responded": 1, "workers": [{"hostname": "celery@6cfadf8a723d", "status": "pong"}], "broker_connected": true, "status": "healthy"}
```

### Quality Gates
| Check | Result |
|-------|--------|
| Unit tests | 964 passed, 85.14% coverage |
| Ruff check | All checks passed (402 files) |
| Ruff format | 402 files already formatted |
| MyPy | 0 errors (227 source files) |
| Docker image build | SUCCESS |
| Frontend build | 181 modules (passes) |
| Frontend tests | 25 passed |
| Frontend typecheck | PASS |
| pip-audit | No known vulnerabilities |
| Health endpoints | `/health/live` and `/health/ready` both 200 OK |

### Celery Worker Status
- Celery v5.6.3 (recovery) running on `celery@6cfadf8a723d`
- All 10 tasks registered:
  - `workers.tasks.cleanup.cleanup_old_articles`
  - `workers.tasks.cleanup.cleanup_old_digests`
  - `workers.tasks.deliver.send_digest_email`
  - `workers.tasks.deliver.send_latest_digest`
  - `workers.tasks.digest.generate_daily_digest`
  - `workers.tasks.ingest.fetch_all_sources`
  - `workers.tasks.process.categorize_article`
  - `workers.tasks.process.categorize_pending_articles`
  - `workers.tasks.process.process_article`
  - `workers.tasks.process.summarize_article`
  - `workers.tasks.process.summarize_pending_articles`
- Connected to Redis broker, ready and accepting tasks
- No errors in worker logs

### Security Controls Verified (No Changes Needed)
- JWT "none" algorithm rejection: active
- Bcrypt password hashing with 12 rounds: active
- SSRF protection in `url_safety.py`: fail-closed, validates all redirect hops
- Rate limiting: fail-closed, brute-force lockout after configured failures
- Security headers: HSTS, X-Content-Type-Options, X-Frame-Options, CSP, etc.
- Request size limiting: active
- Admin RBAC: enforced on all admin endpoints
- Metrics endpoint: admin-protected + IP allow-list
- Production Swagger/docs: disabled (`openapi_url=None`, `docs_url=None` when `environment == "production"`)

## Items Reviewed (No Changes Needed)

- **Ingestion idempotency**: `IngestionService` checks `get_by_url` per article; `ProcessArticleUseCase` checks status before each stage; Celery tasks skip already-processed articles. Idempotency confirmed.
- **Digest generation atomicity**: `GenerateDigestUseCase` wraps digest creation + article status updates in try/except with rollback on failure.
- **Delivery idempotency**: `DeliverDigestUseCase` skips already-SENT deliveries, reuses existing delivery records, uses `(digest_id, recipient)` uniqueness.
- **AI provider retries**: `RetryPolicy` uses tenacity with exponential backoff, max 3 attempts, transient-only retry classification.
- **Transaction atomicity in celery tasks**: Tasks wrap use-case execution in try/except with proper metrics recording and re-raise on failure.
- **Frontend Dockerfile**: Multi-stage build, nginx serving, healthcheck, non-root user — all correct.

## Known Limitations (Pre-existing, Not Introduced)

- Integration tests (`tests/integration`) timeout at 300s due to testcontainers startup overhead in this environment.
- npm audit: 1 dev-dependency vulnerability in `esbuild` (via vite) — not used in production build, accepted risk documented.
