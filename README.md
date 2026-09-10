# AI News Digest

A production-oriented AI-powered news aggregation and daily digest platform built with **Python**, **FastAPI**, **Clean Architecture**, and modern engineering practices.

The project is designed to collect articles from multiple RSS sources, organize and categorize them, generate AI-powered summaries, and produce high-quality daily news digests through a scalable and maintainable architecture.

> **Project Status:** Milestone 54 — Production Activation Package Completion and Launch Verification: **PRODUCTION ACTIVATION PACKAGE COMPLETE — EXTERNAL ACCESS REQUIRED**.

Recent additions build on top of the existing architecture without replacing
it:

* **Trusted-source model** — explicit verification status, source type,
  priority, fetch telemetry, and a curated seed list of official AI
  company blogs, research organisations, established tech publications, and
  reputable business/news outlets. Production digests only include
  articles from sources with `status=verified` and `is_active=true`.
* **Article extraction pipeline** — every ingested article URL is
  re-validated through the existing SSRF boundary, fetched with
  per-hop timeouts, size caps, and redirect re-validation, and then
  extracted to plain text. Extraction is best-effort: failures fall
  back to the RSS excerpt, never to a crashed run.
* **Structured AI output** — every article now carries a pydantic-validated
  `summary`, `key_takeaways`, `why_it_matters`, importance / confidence
  scores, multi-category labels, and company / topic tags. Provider
  output is validated before persistence and re-tried on failure.
* **Multi-category + entity tagging** — `companies`, `topics`, and an
  `article_categories` association table back the structured fields.
  Companies and topics use normalized vocabularies so different surface
  forms collapse to one canonical entity.
* **End-to-end analysis pipeline** — `AnalyzeAndMaterializeUseCase` runs
  structured AI analysis and materializes companies, topics, and categories
  into the database. Celery worker tasks (`analyze_article`,
  `analyze_pending_articles`) process articles with bounded retries
  (`max_retries=3`, `default_retry_delay=60`).
* **Digest rendering** — daily digests now render structured intelligence:
  summary, key takeaways, why it matters, importance score, confidence,
  companies, topics, and categories.
* **Timezone-aware digest scheduling** — `DIGEST_TIMEZONE` (IANA name)
  drives both the Celery Beat schedule and the digest title's local
  date. Default remains `UTC` for backwards compatibility.
* **Public API and frontend contract alignment** — the public article
  endpoint exposes the new AI intelligence (summary, key takeaways,
  why it matters, importance, companies, topics, excerpt). Full
  publisher content is **not** exposed via the public API.
* **Public company and topic discovery** — `/public/companies`,
  `/public/companies/{slug}`, `/public/topics`, `/public/topics/{slug}`
  expose canonical company/topic entities with related article lists and
  article counts, backed by stable slugs.
* **Public intelligence homepage** — `/public/homepage` composes
  "What matters today" (importance-ranked), "Latest AI developments",
  "Daily intelligence digest", and category/company/topic discovery
  sections. The public homepage (`/`) is rewritten as a polished
  intelligence product surface.
* **Enhanced search and filtering** — public article listing supports
  text search across title and summary, company/topic/category filtering,
  importance threshold, date range, and importance-based sorting.
* **Transparent importance labeling** — importance badges use
  transparent labels ("High impact", "Medium impact", "Low impact") with
  explicit copy that the ranking is an automated heuristic, not
  objective truth.
* **Legacy article backward compatibility** — articles without
  structured intelligence continue to render on the public surface with
  a "Limited intelligence" notice.
 * **Story clustering** — related articles are grouped into story clusters
   using deterministic signals (title similarity, shared companies/topics/categories,
   time proximity, canonical domain). Clusters are exposed via
   `/public/clusters` and `/public/clusters/{slug}` and surfaced on a
   dedicated `/stories` page and the public homepage. Clustering is
   conservative (minimum score 0.85, 7-day window, title similarity
   insufficient alone) and additive: no embeddings, no vector DB, no
   paid external services.
 * **Story evolution and "What changed"** — each story cluster now exposes
    a chronological timeline of related coverage, source-role labels
    (Primary announcement, Independent reporting, Technical analysis,
    Follow-up, Reaction, Correction, Background, Related coverage),
    and a conservative "What changed" section that detects meaningful
    shifts in titles, key takeaways, entities, and importance scores
    across the cluster's article history. The public story detail page
    (`/stories/:slug`) renders the timeline, source roles, latest update,
    and change detection. Full publisher content is never reproduced.
 * **Personalized intelligence feed hardening** — the authenticated feed
   now uses a scalable, story-level candidate query (`list_personalized_feed_story_candidates`)
   that prefers the latest article per cluster and falls back to standalone
   articles. Muted entities and thresholds are pushed to the database.
   `RankingExplanation` provides structured, categorized relevance reasons
   (personalization, quality, freshness, fallback) with deterministic
   tie-breaking. Contradiction signals are surfaced when cluster titles
   have low word-overlap. Preferred source types are positive ranking
   signals (+5 points), not strict filters. The 500-article scan
   limitation has been eliminated via database-backed candidate queries.

See `docs/INTELLIGENCE_PLATFORM.md` and `docs/SOURCE_TRUST_MODEL.md`
for the full design.

---

# Features

## Implemented

* Clean Architecture project structure
* Domain-driven design principles
* Domain entities and business models
* Repository interfaces (Ports)
* SQLAlchemy ORM models
* Repository implementations
* Database session management
* Alembic migrations
* Strict static type checking with MyPy
* Ruff linting and formatting
* Poetry dependency management
* Configuration management using Pydantic Settings
* Production-ready project layout
* RSS feed ingestion pipeline
* AI-powered article summarization (OpenAI, Anthropic)
* Article categorization
* FastAPI REST API with authentication
* Celery background workers (`workers/` package)
* Scheduled digest generation via Celery Beat
* Digest generation pipeline (HTML, Markdown, PDF)
* Email delivery via SMTP
* Docker deployment with docker-compose
* Comprehensive automated testing (1502+ unit + integration + E2E tests)
* Digest generation with Markdown, HTML, and PDF renderers
* Deterministic digest content grouping by source/category
 * Idempotent digest creation via unique title constraint
 * Secure HTML rendering with proper escaping
 * UTC timestamps across all digest formats
 * Digest article DTO for clean presentation layer
 * Email delivery infrastructure (SMTPSender, EmailComposer, delivery repository)
 * Idempotent delivery via `(digest_id, recipient)` uniqueness constraint
 * Per-recipient failure isolation and transient/permanent error distinction
 * Scheduled email delivery via Celery Beat (`send_latest_digest` at 08:30 UTC)
 * On-demand digest delivery task (`send_digest_email`)
 * Delivery tracking with attempt counts and failure reasons

## Milestone 11 — UI/UX & Frontend

* React + TypeScript + Vite SPA scaffolded
* Tailwind CSS design system and component layer
* Public API routes and schemas added
* Public pages: landing, news, article detail, digests, digest detail, categories
* Authentication flow (login/register)
* User dashboard
* Admin interface (dashboard, users, sources, digests, operations)
* Frontend tests (Vitest + React Testing Library)
* Frontend production build passing

## Milestone 12 — Production Frontend Integration

* Production frontend Docker container (multi-stage Node + Nginx)
* Frontend integrated into `docker-compose.prod.yml`
* Environment-variable-driven API base URL configuration
* Reverse proxy documentation updated for frontend + API routing
* SEO foundation (meta tags, canonical URLs, robots.txt, Open Graph)
* Responsive mobile/tablet/desktop layouts verified
* Security review completed (no secrets in frontend, safe token handling)
* End-to-end production verification completed

## Milestone 13 — Production Monitoring

* Comprehensive monitoring strategy documentation (`docs/MONITORING.md`)
* Alert conditions defined for 12 critical monitoring targets:
  * Application availability
  * Readiness failures
  * HTTP 5xx rate
  * HTTP latency
  * Database availability
  * Redis availability
  * Celery worker health
  * Celery task failures
  * Disk usage
  * Memory usage
  * CPU usage
  * Container restart count
* Operational runbook with 12 procedures (`docs/RUNBOOK.md`)
* Deployment, rollback, and restart procedures documented
* Health diagnosis and incident investigation procedures documented
* Database outage, Redis outage, and Celery failure response procedures
* Backup restoration and secret rotation procedures
* Certificate renewal and frontend failure procedures
* Updated deployment documentation (`docs/DEPLOYMENT.md`)

## Milestone 20 — Production Launch Preparation & Product Completion

* Frontend/UI/UX review completed across all public, authenticated, and admin pages
* Accessibility review completed: skip links, semantic HTML, ARIA labels, focus management
* SEO foundations enhanced: `sitemap.xml` added, `robots.txt` updated with sitemap reference
* Privacy Policy page added (`/privacy`) with comprehensive data protection content
* Terms of Service page added (`/terms`) with full legal terms
* Data Retention Policy documentation (`docs/DATA_RETENTION_POLICY.md`)
* Account Deletion Policy documentation (`docs/ACCOUNT_DELETION_POLICY.md`)
* Footer updated with Privacy Policy and Terms of Service links
* Frontend tests expanded: 25/25 passing
* Dependency security scan completed: `python-multipart` upgraded to fix 7 vulnerabilities
* Production configuration reviewed: all secrets configurable, debug mode disabled
* Observability reviewed: health endpoints, metrics, pipeline status all operational
* CI/CD pipeline reviewed: lint, typecheck, tests, coverage, Docker build, security audit
* Backup/recovery procedures reviewed and documented
* Rollback procedures documented in `docs/RUNBOOK.md` and `docs/DEPLOYMENT.md`

## Milestone 40 — Notification System

* Notification domain models with `NotificationType`, `NotificationSeverity`, `DeliveryChannel`, and `DeliveryStatus` enums
* Notification preferences with per-user settings (in-app, email, quiet hours, daily caps, importance/confidence thresholds)
* Secure unsubscribe tokens for email notification management
* Deterministic deduplication keys prevent duplicate notifications across retries
* Notification eligibility engine evaluates importance, confidence, muted entities, quiet hours, and daily caps
* Idempotent notification creation with delivery fan-out (in-app + email)
* HTML/plain-text email composer with `html_escape` on all user-facing strings
* Celery tasks for notification evaluation and expiry with bounded retries and metrics
* Authenticated REST API for notification CRUD, preferences, and unsubscribe
* Frontend notification bell, notifications page, and notification preferences page
* Comprehensive test coverage: eligibility (13 tests), service (15 tests), API routes (15 tests), email composer (5 tests), Celery tasks (6 tests)

## Milestone 41 — Production-Ready Notification Delivery, Scheduling, and Reliability

* Timezone-aware notification scheduling with IANA `ZoneInfo` support and DST-safe delivery windows
* Extended `DeliveryStatus` enum with `SCHEDULED`, `PROCESSING`, `DEFERRED`, `RETRYABLE_FAILURE`, `PERMANENT_FAILURE`, `EXPIRED`, `CANCELLED`
* State-machine-driven `NotificationDelivery` transitions with validated status changes
* Email provider abstraction with `ConsoleEmailSender` (development), `TestEmailSender` (testing), and SMTP production sender
* Per-type email templates (8 notification types) and digest templates (daily/weekly)
* `NotificationSchedulingService` with quiet-hour-aware scheduled delivery computation
* `NotificationRateLimiter` with Redis-backed per-user/per-window rate limiting
* `NotificationDeliveryService` with bounded batch processing, idempotency keys, and provider callback handling
* `DigestBatchingService` grouping notifications into digest-ready batches by user preferences
* 7 new Celery tasks: `schedule_notifications`, `process_scheduled_deliveries`, `process_immediate_deliveries`, `retry_failed_deliveries`, `recover_stuck_deliveries`, `cleanup_old_notification_deliveries`, `cleanup_old_notifications`
* Extended API: delivery history, stats, schedule preview, test delivery endpoint, and notification health checks
* Migration 017 adding scheduling columns (`scheduled_for`, `claimed_at`, `processing_started_at`, `next_attempt_at`, `provider_idempotency_key`, `delivery_window`, `suppression_reason`) with composite indexes
* Comprehensive test coverage: API routes (15 tests), eligibility/service (30 tests), email infrastructure (43 tests), domain models (90 tests), Celery tasks (6 tests)

## Milestone 47 — Final Product Completion and Release Closure

* Implemented `ExtractArticleUseCase` with real article fetching, HTML extraction, and content cleaning
* Implemented `AnalyzeArticleUseCase` with JSON-mode AI analysis (importance, confidence, key takeaways, companies, topics)
* Implemented `AnalyzeAndMaterializeUseCase` that materializes companies, topics, and categories into the database
* Added `analysis` capability to both OpenAI and Anthropic providers
* Added `Article.mark_analyzed()` method and `ArticleStatus.ANALYZED` lifecycle state
* Added `Company` and `Topic` domain models with `create` factory methods
* Registered `analysis` capability in the container capability registry
* Added `daily-article-analysis` Celery Beat schedule (07:30 UTC) and `analyze_pending_articles` batch task
* All 1485 backend tests pass, 25 frontend tests pass, ruff/mypy/TypeScript/lint all pass
* Coverage: 84.29% (exceeds 84.06% M46 baseline)
* Security: pip-audit clean, security tests pass

---

# Tech Stack

* Versioned REST API under `/api/v1`
* Stateless JWT authentication (login, register, current-user, logout)
* Password hashing with bcrypt (never stored or returned in plaintext)
* Role-based authorization: anonymous, authenticated user, administrator
* User self-service endpoints (`/api/v1/users/me`)
* Admin user management (`/api/v1/admin/users`, `{id}`, PATCH, DELETE)
* Source CRUD + listing (`/api/v1/sources`)
* Article listing with pagination (`/api/v1/articles`)
* Digest listing with pagination (`/api/v1/digests`)
* Digest delivery history (`/api/v1/digests/{id}/deliveries`)
* Admin triggers for ingestion / digest / cleanup via Celery
* Server-rendered admin dashboard (`/api/v1/admin/dashboard`)
* Consistent pagination envelope (`items`, `total`, `limit`, `offset`)
* Dedicated Pydantic request/response schemas (no ORM/domain leakage)
* Centralized error handling (400/401/403/404/409/422/429/500/503)
* Security headers, CORS, and rate limiting middleware
* Interactive API docs (Swagger UI) at `/docs` (enabled in development)
* Multi-stage Docker production image with non-root user
* Structured JSON logging (production) and console logging (development)
* Health check endpoints (liveness, readiness)
* Prometheus-style metrics endpoint (admin-only)
* CI/CD pipeline with lint, type-check, tests, coverage, Docker build, and security audit
* GitHub Actions deployment workflow with Docker image publishing

---

# Tech Stack

| Category              | Technology        |
| --------------------- | ----------------- |
| Language              | Python 3.12       |
| API                   | FastAPI           |
| Database              | PostgreSQL        |
| ORM                   | SQLAlchemy 2.x    |
| Migrations            | Alembic           |
| Queue                 | Celery            |
| Cache / Broker        | Redis             |
| AI                    | OpenAI, Anthropic |
| HTTP Client           | HTTPX             |
| RSS Parsing           | Feedparser        |
| Configuration         | Pydantic Settings |
| Dependency Management | Poetry            |
| Type Checking         | MyPy (Strict)     |
| Linting               | Ruff              |
| Testing               | Pytest            |

## Frontend

| Category              | Technology        |
| --------------------- | ----------------- |
| Framework             | React 18          |
| Language              | TypeScript 5      |
| Build Tool            | Vite 5            |
| Styling               | Tailwind CSS 3    |
| State Management      | TanStack React Query 5 |
| Routing               | React Router 7    |
| HTTP Client           | Axios             |
| SEO                   | React Helmet Async |
| Testing               | Vitest + React Testing Library |

The frontend is a single-page application served via Nginx in production.
It communicates with the FastAPI backend through the reverse proxy.

---

# Architecture

This project follows **Clean Architecture**, separating business rules from infrastructure concerns.

```text
Domain
    ↓
Application
    ↓
Infrastructure
    ↓
API / Workers
```

Core business logic remains independent of frameworks, databases, and external services.

### Key Packages

| Package | Responsibility |
|---------|---------------|
| `core/` | Configuration, logging, exceptions |
| `domain/` | Entities, enums, repository ports |
| `application/` | Use cases, AI providers, rendering |
| `infrastructure/` | Database, auth, LLM clients, email, RSS |
| `api/` | FastAPI routes, middleware, auth dependencies |
| `workers/` | Celery tasks for async pipeline execution |

### Worker Pipeline

```text
RSS Ingestion (06:00 UTC)
    ↓
Article Summarization (06:30 UTC)
    ↓
Article Categorization (07:00 UTC)
    ↓
Digest Generation (08:00 UTC)
    ↓
Email Delivery (08:30 UTC)
```

Scheduled tasks are configured inline in `celery_app.py` (`beat_schedule` dict) and executed by Celery Beat.

---

# Development Standards

The project emphasizes maintainability and code quality.

* Strict type checking using MyPy
* Ruff linting and formatting
* Repository pattern
* Separation of concerns
* Dependency inversion
* Asynchronous database access
* Production-oriented project organization

---

# Getting Started

## Clone the repository

```bash
git clone <repository-url>
cd ai-news-digest
```

## Install dependencies

```bash
poetry install
```

## Activate the environment

```bash
poetry shell
```

## Environment configuration

Copy `.env.example` to `.env` and set a secure `JWT_SECRET_KEY`:
```bash
cp .env.example .env
# Generate a secure key: openssl rand -hex 32
# Edit .env and set JWT_SECRET_KEY to the generated value
```

## Run static analysis

```bash
poetry run mypy
poetry run ruff check .
```

## Run tests

```bash
poetry run pytest
```

## Run with Docker

```bash
docker compose up
```

The API will be available at `http://localhost:8000`. Celery worker and beat are started automatically.

## Frontend development

```bash
cd frontend
npm install
npm run dev
```

The frontend dev server runs on `http://localhost:3000` and proxies API requests to `http://localhost:8000`.

## Run frontend tests

```bash
cd frontend
npm test
```

## Build frontend for production

```bash
cd frontend
npm run build
```

The production build outputs to `frontend/dist/`.

---

# API Authentication

All business-logic endpoints require a valid JWT access token.

1. Register a user: `POST /api/v1/auth/register`
2. Login: `POST /api/v1/auth/login` → returns `access_token`
3. Use the token: `Authorization: Bearer <token>`

Admin endpoints additionally require the user to have `is_admin=true`.

## API Reference

All routes are versioned under `/api/v1`.

### Authentication (`/api/v1/auth`)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/login` | public | Obtain JWT access token |
| POST | `/auth/register` | public | Self-register a user (non-admin) |
| POST | `/auth/logout` | user | Client-side logout (stateless JWT) |
| GET | `/auth/me` | user | Current user profile |

### Users (`/api/v1/users`)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/users/me` | user | Current user profile |
| PATCH | `/users/me` | user | Update email / password |

### Sources (`/api/v1/sources`)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/sources/` | user | List sources (paginated) |
| POST | `/sources/` | user | Create source |
| PATCH | `/sources/{id}` | user | Update source |
| DELETE | `/sources/{id}` | user | Delete source |

### Articles (`/api/v1/articles`)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/articles/` | user | List articles (paginated) |
| POST | `/articles/` | user | Create article |
| GET | `/articles/{id}` | user | Get article |
| PATCH | `/articles/{id}` | user | Update article |
| DELETE | `/articles/{id}` | user | Delete article |

### Digests (`/api/v1/digests`)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/digests/` | user | List digests (paginated) |
| GET | `/digests/{id}` | user | Get digest |
| GET | `/digests/{id}/deliveries` | user | List digest deliveries |
| POST | `/digests/generate` | user | Generate digest (via use case) |
| PATCH | `/digests/{id}` | user | Update digest |
| PUT | `/digests/{id}` | user | Replace digest |

### Admin (`/api/v1/admin`, requires `is_admin=true`)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/admin/users` | admin | List users |
| GET | `/admin/users/{id}` | admin | Get user |
| PATCH | `/admin/users/{id}` | admin | Update user (role/status/email/password) |
| DELETE | `/admin/users/{id}` | admin | Delete user |
| GET | `/admin/dashboard` | admin | Server-rendered dashboard |
| GET | `/admin/stats` | admin | System statistics |
| GET | `/admin/health` | admin | Admin health |
| POST | `/admin/ingestion/run` | admin | Trigger ingestion (Celery) |
| POST | `/admin/digest/run` | admin | Trigger digest generation (Celery) |
| POST | `/admin/cleanup` | admin | Trigger cleanup (Celery) |

### Health
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health/live` | public | Liveness probe |
| GET | `/health/ready` | public | Readiness probe |

### Authorization model
* **Anonymous** — health endpoints and auth (login/register) only.
* **Authenticated user** — own profile (`/users/me`, `/auth/me`) and all resource reads/writes.
* **Administrator** — everything above plus `/admin/*` management.

Password hashes are never returned in any response. Tokens/secrets are never logged.

---

# Database Migrations

Alembic migrations are located in `migrations/versions/`. To apply migrations:

```bash
poetry run alembic upgrade head
```

Current migration chain:
- `001` — Initial schema (sources, categories, articles, digests)
- `002` — Users table
- `003` — ArticleStatus enum fix (adds `processed`, `ready`)
- `004` — User `is_admin` column
- `005` — Digest title unique constraint (idempotency boundary)
- `006` — Convert `articles.status` from native PostgreSQL enum to VARCHAR
- `007` — Digest deliveries table (idempotent email delivery tracking)
- `008` — Source trust-model columns (status, source_type, publisher, priority, fetch telemetry)
- `009` — Article extraction pipeline columns (extraction_method, extraction_quality, extracted_at, content_char_count)
- `010` — Structured AI intelligence columns (importance_score, confidence, ai_provider, ai_model, key_takeaways, why_it_matters, topics)
- `011` — Companies, topics, and many-to-many associations (article_companies, article_topics, article_categories with backfill)
- `012` — Story clusters table (`story_clusters`) and `articles.cluster_id` foreign key
- `013` — `story_clusters.latest_article_id` column
- `014` — User preferences table (`user_preferences`) and follow/mute junction tables
- `015` — Composite indexes for personalized feed performance and source filtering
- `016` — Notifications tables (`notifications`, `notification_deliveries`, `notification_preferences`)
- `017` — Notification scheduling columns (`scheduled_for`, `claimed_at`, `processing_started_at`, `next_attempt_at`, `provider_idempotency_key`, `delivery_window`, `suppression_reason`) with composite indexes

---

# Production Deployment

## Prerequisites

- Docker and Docker Compose
- A PostgreSQL 16+ instance
- A Redis 7+ instance
- A secure `JWT_SECRET_KEY` (generate with `openssl rand -hex 32`)

## Environment Configuration

1. Copy `.env.example` to `.env.prod.local` (do **not** commit `.env` or `.env.prod.local` to version control)
2. Set `ENVIRONMENT=production`
3. Set `DEBUG=false`
4. Set all required secrets (see `.env.example` for full list)
5. Set `CORS_ORIGINS` to your production frontend origins

### Required Production Variables

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL async connection URL |
| `REDIS_URL` | Redis connection URL |
| `CELERY_BROKER_URL` | Celery broker URL |
| `CELERY_RESULT_BACKEND` | Celery result backend |
| `JWT_SECRET_KEY` | Secure random key (min 32 chars) |
| `CORS_ORIGINS` | JSON array of allowed origins (defaults to localhost) |

### Optional Variables

Optional variables such as `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, and SMTP settings can be left unset. Empty values are handled safely.

## Docker Production Startup

```bash
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
```

The production compose file:
- Binds ports to `127.0.0.1` only
- Uses `unless-stopped` restart policy
- Enforces `no-new-privileges` security option
- Requires Redis password authentication
- Runs containers as non-root user
- Sets memory limits

## Health Checks

| Endpoint | Auth | Purpose |
|----------|------|---------|
| `GET /health/live` | Public | Liveness probe (Kubernetes) |
| `GET /health/ready` | Public | Readiness probe (DB + Redis) |
| `GET /metrics/health` | Public | Metrics subsystem health |

## Database Migrations

Migrations run automatically via `entrypoint.sh` on container startup.

To run manually:
```bash
docker compose exec web alembic upgrade head
```

To check current status:
```bash
docker compose exec web alembic current
docker compose exec web alembic heads
```

## Backup and Restore

```bash
# Backup
bash scripts/backup_db.sh

# Restore
bash scripts/restore_db.sh backup_20240101_000000.sql
```

## Logging

Logs are structured JSON in production and human-readable console in development.

- Log level is controlled by `LOG_LEVEL` (default: `INFO`)
- Never log passwords, JWTs, API keys, SMTP credentials, or database URLs
- Request IDs are propagated via `X-Request-ID` header

## Monitoring

The `/metrics` endpoint exposes Prometheus-style metrics and requires admin authentication.

Metrics include:
- `http_request_total` — request counts by route
- `http_request_duration_avg_seconds` — average latency
- `http_error_total` — error counts by route
- `task_total` — Celery task success/failure counts (in-process only)

For comprehensive monitoring documentation, see [`docs/MONITORING.md`](docs/MONITORING.md).

> Note: `task_total` metrics track task executions within the API server
> process. When Celery workers run in separate containers, task metrics are
> not shared across processes. A shared backend (e.g., Redis or Prometheus
> Push Gateway) would be needed for distributed task metrics.

## Worker and Beat

Celery worker and beat are started automatically by Docker Compose.

```bash
docker compose -f docker-compose.prod.yml logs -f celery_worker
docker compose -f docker-compose.prod.yml logs -f celery_beat
```

## Troubleshooting

| Issue | Check |
|-------|-------|
| Container won't start | `docker compose logs web` |
| Database connection failed | Verify `DATABASE_URL` and PostgreSQL health |
| Redis connection failed | Verify `REDIS_URL` and Redis password |
| Migrations failing | Check `docker compose logs web` for details |
| Worker not processing | Check Celery broker connectivity |
| Worker not processing | Check Celery broker connectivity |
| Auth failures | Verify `JWT_SECRET_KEY` is set and consistent |

## CI/CD

The CI pipeline (`.github/workflows/ci.yml`) runs on every push and pull request
to `main`/`master` across these stages:

1. **Lint** — Ruff lint and format checks
2. **Type Check** — MyPy strict type checking
3. **Unit Tests** — 1502+ tests with mocked dependencies
4. **Integration Tests** — 31 tests using testcontainers (PostgreSQL + Redis)
5. **Coverage** — Full suite with 84%+ coverage
6. **Docker Build** — Multi-stage production image build verification
7. **Security Audit** — `pip-audit` dependency vulnerability scan
8. **E2E Tests** — 19 end-to-end tests against real PostgreSQL + Redis

The deploy workflow (`.github/workflows/deploy.yml`) triggers on GitHub release
publication and pushes a Docker image to `ghcr.io/<repository>`.

## Deployment Procedure

1. Ensure a PostgreSQL 16+ and Redis 7+ instance are running and accessible.
2. Copy `.env.example` to `.env.prod.local` (do **not** commit secrets to version control).
3. Generate a secure JWT secret: `openssl rand -hex 32`
4. Build the production image:
    ```bash
    docker compose -f docker-compose.prod.yml build
    ```
5. Start all services:
    ```bash
    docker compose -f docker-compose.prod.yml --env-file .env.prod.local up -d
    ```
6. Verify health:
    ```bash
    curl http://localhost:8000/health/live
    curl http://localhost:8000/health/ready
    ```
7. Check logs:
    ```bash
    docker compose -f docker-compose.prod.yml logs -f web
    ```
8. Run smoke tests:
    ```bash
    poetry run python tests/smoke_prod.py
    ```

## Smoke Tests

A production smoke-test suite is included at `tests/smoke_prod.py`. It covers:

1. Liveness probe
2. Readiness probe (DB + Redis)
3. Invalid authentication rejection
4. Valid authentication and authorized endpoint access
5. Unauthorized endpoint rejection
6. Admin-only endpoint enforcement
7. Metrics endpoint availability
8. Database-backed operation
9. Redis-backed operation

## Incident and Recovery

For operational procedures and incident response, see the [`docs/RUNBOOK.md`](docs/RUNBOOK.md).

- **Container won't start**: Check `docker compose logs web`
- **Database connection failed**: Verify `DATABASE_URL` and PostgreSQL health
- **Redis connection failed**: Verify `REDIS_URL` and Redis password
- **Migrations failing**: Check `docker compose logs web` for details
- **Auth failures**: Verify `JWT_SECRET_KEY` is set and consistent

To recover from a failed deployment:
```bash
docker compose -f docker-compose.prod.yml up -d --force-recreate
```

Database migrations run automatically on startup via `entrypoint.sh`. Always back up before upgrading:
```bash
bash scripts/backup_db.sh
```

## Rollback Considerations

- The production compose file binds ports to `127.0.0.1` only — use a reverse
  proxy (nginx/Traefik) for TLS termination and external access.
- Database migrations are forward-only by default. Always back up the database
  before upgrading (`bash scripts/backup_db.sh`).
- To roll back the application image, redeploy the previous tag:
  ```bash
  docker compose -f docker-compose.prod.yml up -d --force-recreate
  ```
- The `JWT_SECRET_KEY` must remain consistent across rollouts; changing it
  invalidates all active sessions.
- Celery workers use the same image. Restart them alongside the web service
  to ensure version parity.

---

# License

This project is licensed under the MIT License.
