# AI News Digest

A production-oriented AI-powered news aggregation and daily digest platform built with **Python**, **FastAPI**, **Clean Architecture**, and modern engineering practices.

The project is designed to collect articles from multiple RSS sources, organize and categorize them, generate AI-powered summaries, and produce high-quality daily news digests through a scalable and maintainable architecture.

> **Project Status:** Milestone 9 — Production Deployment & Operational Verification ✅

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
* Comprehensive automated testing (819 unit + 14 integration + 15 E2E tests)
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

## Milestone 7 — API & Dashboard

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

Scheduled tasks are registered in `workers/beat_schedule.py` and executed by Celery Beat.

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
- `006` — Digest status column
- `007` — Digest deliveries table (idempotent email delivery tracking)

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
3. **Unit Tests** — 819 tests with mocked dependencies
4. **Integration Tests** — 14 tests using testcontainers (PostgreSQL + Redis)
5. **Coverage** — Full suite with 80% coverage threshold
6. **Docker Build** — Multi-stage production image build verification
7. **Security Audit** — `pip-audit` dependency vulnerability scan
8. **E2E Tests** — 15 end-to-end tests against real PostgreSQL + Redis

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
