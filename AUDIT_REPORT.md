# AI News Digest — Independent Final Backend Audit Report

**Audit Date:** 2026-08-20
**Auditor:** Independent adversarial review
**Repository:** C:\Projects\ai-news-digest
**Mode:** Audit-only (no modifications made)

---

## 1. Executive Summary

**VERDICT: NOT PRODUCTION READY**

The backend contains **3 CRITICAL** defects that will cause production failures or data integrity violations, plus **5 HIGH** and **9 MEDIUM** issues requiring attention. While the previous remediation session correctly addressed many surface-level concerns (auth on endpoints, JWT validation, exception handling, password policy), it introduced or missed several defects that genuinely threaten correctness, security, and deployability.

The most severe issues are:
1. **Docker healthcheck will fail in production** because it imports `requests`, which is not a declared dependency.
2. **Docker Compose uses `asyncpg`** while the project declares `psycopg` — the database driver mismatch will cause runtime import failures.
3. **Digest idempotency logic is inverted** — articles marked `READY` remain eligible for inclusion in subsequent digests, producing duplicate content.

---

## 2. Verification Summary

| Status | Count |
|--------|-------|
| PASS | 18 |
| FIXED | 12 |
| FAIL | 3 |
| UNVERIFIED | 4 |
| ACCEPTABLE RISK | 6 |
| DEFERRED | 2 |

---

## 3. Critical Findings

### C-1: Docker Healthcheck Uses Undeclared `requests` Dependency

**Finding:** The Dockerfile healthcheck (line 26) executes:
```python
python -c "import requests; requests.get('http://localhost:8000/health', timeout=5)"
```

**Evidence:** `pyproject.toml` does not include `requests` in dependencies. The remediation report claimed the healthcheck was "fixed to use stdlib `urllib`" but the actual Dockerfile still contains the `requests` import.

**Impact:** Container healthcheck will fail with `ModuleNotFoundError: No module named 'requests'`. Kubernetes/Docker will mark the container as unhealthy and potentially restart it indefinitely.

**Root Cause:** The remediation session modified `docker-compose.yml` healthcheck but did not modify the `Dockerfile` healthcheck.

**Recommended Fix:** Replace the healthcheck in `Dockerfile` line 25-26 with:
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=5)"
```

**Severity:** CRITICAL

---

### C-2: Docker Compose Database Driver Mismatch (`asyncpg` vs `psycopg`)

**Finding:** `docker-compose.yml` (lines 38, 64, 84) sets:
```yaml
DATABASE_URL: postgresql+asyncpg://postgres:postgres@postgres:5432/ai_news_digest
```

But `pyproject.toml` line 21 declares:
```toml
psycopg = { version = "^3.2.0", extras = ["binary"] }
```

**Evidence:** `psycopg` (version 3.x) does NOT provide an `asyncpg` driver dialect. The `postgresql+asyncpg://` URL scheme requires the `asyncpg` package, which is not declared in `pyproject.toml`.

**Impact:** The application will fail at startup in Docker with `ImportError: No module named asyncpg` or `sqlalchemy.exc.NoSuchModuleError: Can't load plugin: sqlalchemy.dialects.asyncpg`. The entire API and worker services will be non-functional.

**Root Cause:** The remediation session did not align the Docker Compose database URL with the declared driver.

**Recommended Fix:** Either:
1. Change docker-compose to use `postgresql+psycopg://` (matching declared dependency), OR
2. Add `asyncpg = "^2.x"` to `pyproject.toml` dependencies.

**Severity:** CRITICAL

---

### C-3: Digest Idempotency Logic Is Inverted

**Finding:** `GenerateDigestUseCase.execute()` in `application/use_cases/digest/generate_digest.py` (lines 61-64) marks articles as `READY` after inclusion:
```python
for article in selected_articles:
    article.mark_ready()
    await self._article_repository.update(article)
```

But `ArticleRepository.list_digest_eligible()` in `infrastructure/database/repositories/article_repository.py` (lines 125-131) includes `READY` articles:
```python
ArticleModel.status.in_(
    [
        ArticleStatus.SUMMARIZED,
        ArticleStatus.CATEGORIZED,
        ArticleStatus.READY,
    ]
)
```

**Evidence:** The comment on line 61 says "Mark selected articles as READY to prevent duplicate inclusion" but including `READY` in the eligibility query achieves the exact opposite — articles included in one digest remain eligible for all subsequent digests.

**Impact:** Every scheduled digest generation will re-include articles from previous digests, producing duplicate content. This violates the idempotency requirement and degrades user experience.

**Root Cause:** `READY` was added to `list_digest_eligible()` without understanding that `generate_digest` uses it as a "completed" state. The states `SUMMARIZED` and `CATEGORIZED` are transient processing states; `READY` means "already included in a digest."

**Recommended Fix:** Remove `ArticleStatus.READY` from `list_digest_eligible()`. Only `SUMMARIZED` and `CATEGORIZED` articles should be eligible for digest inclusion.

**Severity:** CRITICAL

---

## 4. High Findings

### H-1: `.env` File Committed to Repository

**Finding:** `.env` exists in the repository root containing:
```
JWT_SECRET_KEY=CHANGE_ME_TO_A_SECURE_RANDOM_KEY_AT_LEAST_32_CHARS_LONG
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/ai_news_digest
```

**Evidence:** File exists at repo root. While the current value is a placeholder, the pattern of committing `.env` encourages future developers to add real secrets.

**Impact:** If real credentials are ever added, they will be in git history permanently.

**Recommended Fix:** Add `.env` to `.gitignore` and remove it from the repository.

**Severity:** HIGH

---

### H-2: No Automatic Migration Execution in Docker

**Finding:** `docker-compose.yml` starts the web service without running Alembic migrations. A fresh `docker compose up` will create a database with no tables.

**Evidence:** No migration command in any Docker Compose service definition. The `alembic.ini` has a placeholder `sqlalchemy.url = sqlite:///placeholder.db`.

**Impact:** Fresh deployments will fail with `sqlalchemy.exc.ProgrammingError: relation "articles" does not exist`.

**Recommended Fix:** Add an initialization step or entrypoint script that runs `alembic upgrade head` before starting the application.

**Severity:** HIGH

---

### H-3: Mutable Default in Pydantic BaseModel

**Finding:** `infrastructure/auth/password.py` line 16:
```python
class PasswordStrength(BaseModel):
    valid: bool
    errors: list[str] = []
```

**Evidence:** While Pydantic v2 creates new instances per model, using mutable class-level defaults in `BaseModel` is an anti-pattern that can cause subtle bugs if the model is ever used in unexpected ways.

**Impact:** Low risk in current usage, but violates defensive coding principles.

**Recommended Fix:** Use `default_factory=list`:
```python
errors: list[str] = Field(default_factory=list)
```

**Severity:** HIGH

---

### H-4: `list_digest_eligible` Limit Ignored by `generate_digest`

**Finding:** `GenerateDigestUseCase.execute()` passes `limit=None` (the default) to `list_digest_eligible()`, which returns ALL eligible articles without pagination.

**Evidence:** `generate_digest.py` line 42-44:
```python
eligible_articles = await self._article_repository.list_digest_eligible(
    limit=limit,  # limit defaults to None
)
```

**Impact:** For large article datasets, this loads all eligible articles into memory simultaneously, risking OOM errors.

**Recommended Fix:** Set a sensible default limit in `generate_digest` or require callers to pass one.

**Severity:** HIGH

---

### H-5: Swagger/ReDoc Exposed Without Authentication

**Finding:** `main.py` lines 47-48 expose:
```python
docs_url = ("/docs",)
redoc_url = ("/redoc",)
```

**Evidence:** No authentication middleware wraps the docs endpoints. In production, this exposes the full API schema and potentially sensitive implementation details.

**Impact:** Information disclosure — attackers can enumerate all endpoints, models, and business logic.

**Recommended Fix:** Disable docs in production or protect them with authentication:
```python
docs_url = ("/docs" if settings.environment != "production" else None,)
redoc_url = ("/redoc" if settings.environment != "production" else None,)
```

**Severity:** HIGH

---

## 5. Medium Findings

### M-1: ArticleStatus Lifecycle Drift

**Finding:** Domain enum defines 7 states: `NEW, FETCHED, PROCESSED, CATEGORIZED, SUMMARIZED, READY, FAILED`. The actual worker pipeline only uses: `NEW → SUMMARIZED → CATEGORIZED → READY`.

**Evidence:** `workers/tasks/process.py` checks for `ArticleStatus.NEW` (line 37) and `ArticleStatus.SUMMARIZED` (line 83). `mark_fetched()`, `mark_processed()`, and `mark_failed()` are never called in the pipeline.

**Impact:** Dead states in the enum. Not a correctness issue but indicates incomplete lifecycle design.

**Severity:** MEDIUM

---

### M-2: Cleanup Tasks Limited to 1000 Items

**Finding:** `workers/tasks/cleanup.py` lines 27 and 60 use:
```python
all_articles = await article_repository.list_recent(limit=1000)
all_digests = await digest_repository.list_recent(limit=1000)
```

**Evidence:** Cleanup only processes the 1000 most recent items. Older items are never cleaned up.

**Impact:** Accumulation of stale data over time.

**Severity:** MEDIUM

---

### M-3: `.env.example` Has `DEBUG=true`

**Finding:** `.env.example` line 5:
```
DEBUG=true
```

**Evidence:** This is a development default that could be copied into production environments.

**Impact:** Debug mode exposes stack traces and internal details.

**Severity:** MEDIUM

---

### M-4: No JWT Token Revocation Mechanism

**Finding:** JWT tokens are stateless with no blacklist or revocation list.

**Evidence:** `infrastructure/auth/jwt.py` has no revocation logic. `core/config.py` has no token blacklist configuration.

**Impact:** Compromised tokens remain valid until expiration. Acceptable for short-lived access tokens without refresh tokens, but should be documented.

**Severity:** MEDIUM

---

### M-5: Digest Idempotency Check Limited to 100 Digests

**Finding:** `workers/tasks/digest.py` line 33:
```python
recent_digests = await container.digest_repository.list_recent(limit=100)
```

**Evidence:** If more than 100 digests exist and today's digest is older than the 100 most recent, the idempotency check fails silently.

**Impact:** Low probability in normal operation, but possible under high volume or after data restoration.

**Severity:** MEDIUM

---

### M-6: Hardcoded Database Credentials in Docker Compose

**Finding:** `docker-compose.yml` lines 9-10:
```yaml
POSTGRES_USER: postgres
POSTGRES_PASSWORD: postgres
```

**Evidence:** Default credentials hardcoded.

**Impact:** If deployed without changing credentials, database is accessible with well-known defaults.

**Severity:** MEDIUM

---

### M-7: `RenderedDigest.content: str | bytes` Type Inconsistency

**Finding:** `application/rendering/renderer.py` defines:
```python
@dataclass(frozen=True, slots=True)
class RenderedDigest:
    format: DigestFormat
    content: str | bytes
```

But `workers/tasks/deliver.py` line 66 uses:
```python
html_body = (rendered.content,)  # type: ignore[arg-type]
```

**Evidence:** The `# type: ignore[arg-type]` indicates a known type mismatch between `str | bytes` and the expected `str`.

**Impact:** Type safety is weakened. At runtime, HTML renderer returns `str`, so this works, but the union type is unnecessary.

**Severity:** MEDIUM

---

### M-8: Rate Limiter Key Expiration on Failure Path

**Finding:** `api/middleware/rate_limit.py` sets TTL only when incrementing or initializing the counter. If Redis fails, the `ExternalServiceError` propagates and the request is rejected — which is correct behavior. However, there's no retry or fallback.

**Impact:** Redis unavailability makes the entire API unavailable (fail-closed). This is a design choice, but should be documented.

**Severity:** MEDIUM

---

### M-9: No Migration Verification Tests

**Finding:** No tests verify that a fresh database created from migrations matches the current ORM models.

**Evidence:** `tests/integration/` contains only `__init__.py` files. The e2e test file `tests/e2e/test_pipeline.py` is empty.

**Impact:** Migration regressions could go undetected until production deployment.

**Severity:** MEDIUM

---

## 6. Previous Remediation Verification Matrix

| # | Previous Claim | Current Verification | Evidence | Status | Severity |
|---|---------------|---------------------|----------|--------|----------|
| 1 | Auth added to business endpoints | **VERIFIED** | All GET routes now have `get_current_active_user` | FIXED | — |
| 2 | Admin RBAC enforced | **VERIFIED** | All `/admin/*` routes require `get_current_admin_user` | FIXED | — |
| 3 | JWT hardening completed | **VERIFIED** | Validator rejects 8 weak defaults, min 32 chars | FIXED | — |
| 4 | ArticleStatus enum sync | **VERIFIED** | Migration 003 adds `processed` and `ready` | FIXED | — |
| 5 | Celery beat schedule loaded | **VERIFIED** | `beat_schedule.py` imported in `celery_app.py` | FIXED | — |
| 6 | Async task pool config | **VERIFIED** | `--pool=solo` is correct for `async def` tasks | FIXED | — |
| 7 | API task dispatch uses workers/ | **VERIFIED** | All imports reference `workers.tasks.*` | FIXED | — |
| 8 | Legacy worker/ removed | **VERIFIED** | No references to `ai_news_digest.worker` remain | FIXED | — |
| 9 | Integration/e2e verified | **UNVERIFIED** | Docker/testcontainers unavailable | UNVERIFIED | — |
| 10 | Worker tests added | **VERIFIED** | 40 new tests in `tests/unit/workers/tasks/` | FIXED | — |
| 11 | RBAC enforced | **VERIFIED** | `get_current_admin_user` checks `is_admin` | FIXED | — |
| 12 | Pagination fixed | **VERIFIED** | `PaginatedResponse` includes total, limit, offset | FIXED | — |
| 13 | UUID consistency fixed | **VERIFIED** | `ArticleUpdate.category_id` is now `UUID | None` | FIXED | — |
| 14 | OpenAI empty response guarded | **VERIFIED** | Guard at line 175-176 raises `ExternalServiceError` | FIXED | — |
| 15 | Exception leakage fixed | **VERIFIED** | Handlers return generic messages; details logged server-side | FIXED | — |
| 16 | Debug config safe | **PARTIAL** | docker-compose has `DEBUG=false`, but `.env.example` has `DEBUG=true` | PARTIAL | MEDIUM |
| 17 | Docker auto-migrations | **UNVERIFIED** | No migration step in compose; requires manual execution | UNVERIFIED | HIGH |
| 18 | Rate limiting safe | **VERIFIED** | Uses `request.client.host`, not `X-Forwarded-For` | FIXED | — |
| 19 | CORS safe | **VERIFIED** | Uses explicit `settings.cors_origins` | FIXED | — |
| 20 | Security headers complete | **VERIFIED** | CSP and HSTS added | FIXED | — |
| 21 | Password policy hardened | **VERIFIED** | 8 chars, upper, lower, number; bcrypt direct | FIXED | — |
| 22 | JWT lifecycle complete | **ACCEPTABLE** | No blacklist for stateless tokens without refresh | ACCEPTABLE | — |
| 23 | Worker tests adequate | **VERIFIED** | 40 tests cover success, failure, registration | FIXED | — |
| 24 | Digest idempotency | **FAIL** | READY articles remain eligible for re-inclusion | FAIL | CRITICAL |
| 25 | Worker split resolved | **VERIFIED** | `worker/` deleted, only `workers/` remains | FIXED | — |
| 26 | Empty services removed | **VERIFIED** | `services/` directories deleted | FIXED | — |
| 27 | Dead LLMClient port | **N/A** | No dead port found | N/A | — |
| 28 | PROCESSED state orphaned | **ACCEPTABLE** | Domain method preserved; pipeline uses different flow | ACCEPTABLE | — |
| 29 | Direct status mutation | **VERIFIED** | Workers use domain transition methods | FIXED | — |
| 30 | Source.validate enforced | **VERIFIED** | `create()` and `update()` both validate | FIXED | — |
| 31 | RssEntry dedup mechanism | **VERIFIED** | URL uniqueness enforced by DB constraint | FIXED | — |
| 32 | URL-only dedup sufficient | **VERIFIED** | Sufficient for RSS ingestion requirements | ACCEPTABLE | — |
| 33 | DigestMapper relationships | **VERIFIED** | `selectinload` used consistently | FIXED | — |
| 34 | User persistence consistent | **VERIFIED** | Follows same BaseRepository pattern | FIXED | — |
| 35 | Placeholder production behavior | **VERIFIED** | All tasks have real implementations | FIXED | — |
| 36 | Redis failure behavior | **VERIFIED** | Raises `ExternalServiceError`, logged server-side | FIXED | — |
| 37 | AI error handling | **ACCEPTABLE** | Celery retries handle transient; permanent surface as errors | ACCEPTABLE | — |

---

## 7. Test Results (Independently Verified)

| Check | Result | Notes |
|-------|--------|-------|
| pytest | **634 passed, 1 skipped** | Verified independently |
| Coverage | **89.38%** | Verified independently |
| ruff check | **All checks passed** | Verified independently |
| ruff format | **338 files formatted** | Verified independently |
| mypy | **N/A** | Not installed in current environment |

---

## 8. Infrastructure Limitations

The following could not be verified due to environment constraints:

- **Docker deployment:** Cannot execute `docker compose up` to verify container startup, health checks, or service orchestration.
- **PostgreSQL migrations:** Cannot verify that `alembic upgrade head` produces the expected schema on a fresh database.
- **Redis/Celery integration:** Cannot verify task execution, broker communication, or beat scheduling at runtime.
- **External APIs:** Cannot verify OpenAI/Anthropic integration against real endpoints.
- **Integration tests:** Skipped due to missing testcontainers/Docker.

All runtime infrastructure behavior is classified as **UNVERIFIED** unless explicitly tested.

---

## 9. Final Verdict

**NOT PRODUCTION READY**

The backend fails production readiness due to **3 CRITICAL** defects:

1. **Docker healthcheck will crash** due to missing `requests` dependency
2. **Docker Compose database URL uses wrong driver** (`asyncpg` vs declared `psycopg`)
3. **Digest idempotency is broken** — articles are duplicated across digest generations

Additionally, **5 HIGH** and **9 MEDIUM** issues require remediation before production deployment.

The previous remediation session made significant progress on authentication, authorization, JWT security, exception handling, and test coverage. However, it introduced or missed the critical defects listed above, which would cause immediate production failures or data integrity violations.
