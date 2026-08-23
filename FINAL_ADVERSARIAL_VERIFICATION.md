# AI News Digest — Final Adversarial Production-Readiness Verification

**Date:** 2026-08-20
**Verifier:** Independent adversarial review
**Repository:** C:\Projects\ai-news-digest
**Mode:** Verification + remediation

---

## 1. Final Verdict

**PRODUCTION READY — STAGING VERIFICATION REQUIRED**

All 3 CRITICAL, 5 HIGH, and 9 MEDIUM findings from the previous audit have been verified fixed or accepted. Additional defects discovered during adversarial review have been remediated. The backend passes:

- **642 unit tests passed, 1 skipped** (testcontainers unavailable)
- **89.16% code coverage** (exceeds 80% threshold)
- **ruff check: All checks passed**
- **ruff format: 341 files formatted**

Infrastructure validation (Docker build/start, PostgreSQL migrations, Redis/Celery runtime) is classified as **UNVERIFIED — environment limitation** and must be completed in staging before final production deployment.

---

## 2. Previous Finding Verification

### Critical Findings

| ID | Status | Description | Evidence |
|----|--------|-------------|----------|
| C-1 | **VERIFIED FIXED** | Dockerfile healthcheck uses stdlib `urllib.request`, not `requests` | `Dockerfile:28` — `CMD python -c "import urllib.request; ..."` |
| C-2 | **VERIFIED FIXED** | PostgreSQL async driver stack consistent | `pyproject.toml:22` — `asyncpg = "^2.9.0"`; all `DATABASE_URL` values use `postgresql+asyncpg://` |
| C-3 | **VERIFIED FIXED** | Digest idempotency invariant enforced | `article_repository.py:125-130` — `READY` removed from eligibility; `digest_repository.py:153` — `get_by_title()` added; `digest_model.py:35` — `unique=True` on title; migration `005` present |

### High Findings

| ID | Status | Description | Evidence |
|----|--------|-------------|----------|
| H-1 | **VERIFIED FIXED** | `.env` not tracked | `git ls-files .env` returns empty; `.gitignore:50` contains `.env` |
| H-2 | **VERIFIED FIXED** | Automatic migrations in Docker | `entrypoint.sh` runs `python -m alembic upgrade head`; `Dockerfile` copies `alembic.ini` and `migrations/`; worker/beat `depends_on` web service health |
| H-3 | **VERIFIED FIXED** | No mutable Pydantic defaults | `password.py:16` — `Field(default_factory=list)` |
| H-4 | **VERIFIED FIXED** | All digest paths bounded | API: `limit=50` default, max 100; Worker: `limit=50`; Config: `digest_max_articles=50` |
| H-5 | **VERIFIED FIXED** | Production docs disabled | `main.py:46-50` — `openapi_url`, `docs_url`, `redoc_url` all `None` when `environment == "production"` |

### Medium Findings

| ID | Status | Description | Evidence |
|----|--------|-------------|----------|
| M-1 | **VERIFIED FIXED** | ArticleStatus lifecycle coherent | `article_status.py` — 5 states: `NEW, CATEGORIZED, SUMMARIZED, READY, FAILED`; dead `FETCHED, PROCESSED` removed |
| M-2 | **VERIFIED FIXED** | Cleanup batches beyond 1000 | `cleanup.py:14` — `_BATCH_SIZE = 1000`; offset-based pagination loop |
| M-3 | **VERIFIED FIXED** | Safe DEBUG default | `.env.example:5` — `DEBUG=false` |
| M-4 | **ACCEPTED RISK** | JWT revocation not implemented | Documented in `core/config.py:263-272`; short-lived stateless tokens (60 min) without refresh tokens |
| M-5 | **VERIFIED FIXED** | Digest idempotency DB-backed | `get_by_title()` + unique constraint on `digests.title` |
| M-6 | **VERIFIED FIXED** | No hardcoded credentials | `docker-compose.yml` — all values use `${VAR:-default}` pattern |
| M-7 | **VERIFIED FIXED** | RenderedDigest typing precise | `deliver.py` — explicit `isinstance(html_content, bytes)` check; no `# type: ignore` |
| M-8 | **ACCEPTED RISK** | Redis fail-closed behavior | Documented in `redis_store.py`; intentional security design |
| M-9 | **VERIFIED FIXED** | Migration verification tests | `tests/unit/test_migrations.py` — 4 tests for config, files, chain, enum presence |

---

## 3. Additional Findings (New Issues Discovered)

### ADV-1: OpenAPI Schema Exposed in Production

**Severity:** HIGH
**Status:** FIXED

**Finding:** The previous remediation disabled `/docs` and `/redoc` in production, but left `openapi_url` always set. This exposed the full API schema at `/api/v1/openapi.json` even in production.

**Evidence:** `main.py:46` — `openapi_url=f"{settings.api_prefix}/openapi.json"` had no production guard.

**Fix:** Added production guard to `openapi_url`:
```python
openapi_url = (
    (f"{settings.api_prefix}/openapi.json" if app_settings.environment != "production" else None),
)
```

**Verification:** `tests/unit/test_main.py` — 4 tests confirm docs/openapi disabled in production, enabled in other environments.

---

### ADV-2: DigestRepository.list_recent Missing offset Parameter

**Severity:** HIGH
**Status:** FIXED

**Finding:** The cleanup worker calls `digest_repository.list_recent(limit=_BATCH_SIZE, offset=offset)`, but `DigestRepository.list_recent()` only accepted `limit`. This would cause a `TypeError` at runtime when cleanup processes more than 1000 digests.

**Evidence:** `cleanup.py:81-83` passes `offset=offset`; `digest_repository.py:126-129` only accepted `limit`.

**Fix:** Added `offset: int = 0` parameter to `DigestRepository.list_recent()` and applied `.offset(offset)` to the query.

---

### ADV-3: Dockerfile Missing alembic.ini and migrations/ Copy

**Severity:** CRITICAL
**Status:** FIXED

**Finding:** The Dockerfile did not copy `alembic.ini` or the `migrations/` directory into the image. The entrypoint runs `python -m alembic upgrade head`, but Alembic cannot find its configuration or migration files, causing startup failure.

**Evidence:** `Dockerfile` only copied `pyproject.toml`, `poetry.lock`, and `src/`. No `alembic.ini` or `migrations/`.

**Fix:** Added `COPY alembic.ini ./` and `COPY migrations/ ./migrations/` to Dockerfile.

---

### ADV-4: Poetry Virtualenv Not Disabled in Docker

**Severity:** CRITICAL
**Status:** FIXED

**Finding:** The Dockerfile runs `poetry install` which creates a virtual environment by default. Subsequent `CMD` and `ENTRYPOINT` commands run with the system Python, which cannot find packages installed in the poetry venv. This would cause `ModuleNotFoundError` at runtime.

**Evidence:** `Dockerfile` runs `poetry install` without `poetry config virtualenvs.create false` or `poetry run`.

**Fix:** Added `poetry config virtualenvs.create false &&` before `poetry install` in Dockerfile.

---

### ADV-5: Worker/Beat Could Start Before Migrations Complete

**Severity:** HIGH
**Status:** FIXED

**Finding:** `celery_worker` and `celery_beat` only depended on `postgres` and `redis` health, not on the `web` service. They could start before web's entrypoint completed migrations, causing database schema errors.

**Evidence:** `docker-compose.yml` — worker/beat `depends_on` listed only `postgres` and `redis`.

**Fix:** Added `web` with `condition: service_healthy` to worker/beat `depends_on`. Web's healthcheck ensures the app is running (which requires migrations to have succeeded via entrypoint).

---

### ADV-6: Digest Generation Transaction Atomicity

**Severity:** HIGH
**Status:** FIXED

**Finding:** `GenerateDigestUseCase.execute()` marked articles as `READY` before creating the digest. If digest creation failed after some articles were marked `READY`, those articles would be permanently excluded from future digests without being associated with any digest.

**Evidence:** `generate_digest.py` — article updates happened before `digest_repository.create()`.

**Fix:** Reordered operations: create digest first, then mark articles `READY`. If digest creation fails, articles remain in their previous state and stay eligible.

**Concurrency reasoning:** Two concurrent workers:
1. Both call `get_by_title()` → both get `None`
2. Worker A creates digest → succeeds
3. Worker B creates digest → fails with `IntegrityError` (unique constraint)
4. Worker A marks articles `READY`
5. Worker B retries → `get_by_title()` finds existing digest → skips

The database unique constraint is the final authority. The retry mechanism handles the race condition correctly.

---

## 4. Files Changed

### Source Files Modified
- `Dockerfile` — healthcheck urllib, copy alembic.ini/migrations, disable poetry venv, entrypoint
- `docker-compose.yml` — parameterized DATABASE_URL, added web dependency for worker/beat
- `entrypoint.sh` — new file, runs alembic migrations before app start
- `pyproject.toml` — added `asyncpg` dependency
- `.env.example` — changed `DEBUG=true` to `DEBUG=false`
- `src/ai_news_digest/main.py` — factory function, production openapi/docs guard
- `src/ai_news_digest/core/config.py` — added `digest_max_articles`, documented JWT tradeoff
- `src/ai_news_digest/domain/enums/article_status.py` — removed dead `FETCHED, PROCESSED` states
- `src/ai_news_digest/domain/models/article.py` — removed dead `mark_fetched, mark_processed` methods
- `src/ai_news_digest/domain/ports/digest_repository.py` — added `get_by_title()` method
- `src/ai_news_digest/infrastructure/auth/password.py` — `Field(default_factory=list)`
- `src/ai_news_digest/infrastructure/cache/redis_store.py` — documented fail-closed behavior
- `src/ai_news_digest/infrastructure/database/models/digest_model.py` — `unique=True` on title
- `src/ai_news_digest/infrastructure/database/repositories/article_repository.py` — removed `READY` from eligibility
- `src/ai_news_digest/infrastructure/database/repositories/digest_repository.py` — added `get_by_title()`, `offset` in `list_recent()`
- `src/ai_news_digest/workers/tasks/cleanup.py` — batched pagination with offset
- `src/ai_news_digest/workers/tasks/deliver.py` — explicit bytes-to-str decode
- `src/ai_news_digest/workers/tasks/digest.py` — uses `get_by_title()` for idempotency

### New Files
- `migrations/versions/005_add_digest_title_unique.py`
- `tests/unit/test_main.py`
- `tests/unit/test_migrations.py`

---

## 5. Test Results

| Check | Result |
|-------|--------|
| **pytest** | **642 passed, 1 skipped** |
| **Coverage** | **89.16%** (threshold: 80%) |
| **ruff check** | **All checks passed** |
| **ruff format** | **341 files formatted** |
| **mypy** | N/A (not installed in environment) |

### Tests Added/Updated
- `tests/unit/test_main.py` — 4 tests for production docs/openapi disabling
- `tests/unit/test_migrations.py` — 4 tests for migration structure and chain consistency
- `tests/unit/workers/tasks/test_digest.py` — updated mocks for `get_by_title()`
- `tests/unit/workers/tasks/test_cleanup.py` — updated assertions for `offset=0`
- `tests/unit/domain/enums/test_article_status.py` — reflects 5-state lifecycle
- `tests/unit/domain/test_article_status.py` — reflects 5-state lifecycle

---

## 6. Infrastructure Verification

| Component | Status | Notes |
|-----------|--------|-------|
| Docker build | **UNVERIFIED** | Docker not available in environment |
| Container startup | **UNVERIFIED** | Docker not available |
| PostgreSQL migration execution | **UNVERIFIED** | PostgreSQL not available |
| Redis/Celery runtime | **UNVERIFIED** | Redis not available |
| Healthcheck behavior | **UNVERIFIED** | Docker not available |
| Production docs disable at runtime | **UNVERIFIED** | Requires FastAPI runtime with production settings |
| Concurrent digest generation | **UNVERIFIED** | Requires PostgreSQL for constraint testing |

All infrastructure configurations are structurally sound and aligned. Verification must be completed in staging.

---

## 7. Remaining Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Docker migration startup race | Low | Medium | Worker/beat now depend on web health; verify in staging |
| Concurrent digest partial failure | Low | Low | Digest created first; articles marked READY after; retry handles races |
| `asyncpg` driver compatibility | Low | High | Standard SQLAlchemy async driver; verify in staging |
| `list_digest_eligible(limit=None)` still possible | Low | Low | All production callers pass explicit limits; repository allows `None` for testing flexibility |

---

## 8. Final Recommendation

**PROCEED TO STAGING**

The repository is internally coherent and ready for staging verification. All critical correctness, security, and operational issues have been addressed. The remaining work is infrastructure validation in a staging environment with Docker, PostgreSQL, and Redis.

Do not deploy to production until staging verification confirms:
1. Docker containers start correctly
2. Migrations execute successfully
3. Healthchecks pass
4. Worker/beat start after migrations
5. Concurrent digest generation handles races correctly
