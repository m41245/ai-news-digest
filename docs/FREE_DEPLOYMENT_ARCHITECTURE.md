# $0 Deployment Architecture

## Executive Summary

This document describes the best zero-budget deployment architecture for the AI News Intelligence Platform, based on exhaustive research of current free-tier offerings as of September 2026.

## Chosen Architecture: Render + Neon + Upstash + Cloudflare Pages

```text
Cloudflare Pages (Frontend)
    ↓ HTTPS
Render Free Web Service (Backend API)
    ↓
Neon PostgreSQL (Free Tier)
    ↓
Upstash Redis (Free Tier)
    ↓
GitHub Actions Scheduled Workflows (Replaces Celery Beat)
```

## Why These Providers

### Frontend: Cloudflare Pages
- Unlimited bandwidth
- 500 builds/month
- No credit card required
- Global CDN
- Automatic HTTPS
- Custom domain support

### Backend: Render Free Web Service
- 750 free instance hours/month
- Docker support
- Custom domains + managed TLS
- No credit card required
- Auto-deploy from GitHub

### Database: Neon PostgreSQL
- 0.5 GB storage permanent free tier
- 100 compute-unit-hours/month
- Scale-to-zero after 5 min idle
- PostgreSQL 16 compatible
- No credit card required

### Redis: Upstash
- 256 MB storage
- 500,000 commands/month
- No sleep, no credit card
- Redis-compatible API
- TLS supported

### Scheduler: Celery Beat (Render Worker)
- Celery Beat is the sole automated scheduler
- It runs inside the `ai-news-digest-beat` Render worker service
- It dispatches all 13 periodic tasks to the Celery worker via the message broker
- Schedule is defined in `src/ai_news_digest/workers/celery_app.py`
- No additional infrastructure cost (uses existing Render free worker)

## Environment Variables

### Required for Backend
```bash
DATABASE_URL=postgresql+asyncpg://user:pass@host/ai_news_digest
REDIS_URL=rediss://default:password@upstash-host:6379
CELERY_BROKER_URL=rediss://default:password@upstash-host:6379/1
CELERY_RESULT_BACKEND=rediss://default:password@upstash-host:6379/2
JWT_SECRET_KEY=<32+ char random string>
ENVIRONMENT=production
DEBUG=false
HOST=0.0.0.0
PORT=<set-by-render>
CORS_ORIGINS=["https://ai-news-digest-doo.pages.dev"]
EMAIL_ENABLED=false
EMAIL_DEVELOPMENT_MODE=false
EMAIL_PROVIDER=console
OPENAI_ENABLED=false
ANTHROPIC_ENABLED=false
```

### Required for Frontend
```bash
VITE_API_BASE_URL=https://your-backend.onrender.com
```

## Deployment Steps

### 1. Database Setup (Neon)
1. Sign up at https://neon.tech (no credit card)
2. Create a new project
3. Copy the connection string
4. Run migrations: `poetry run alembic upgrade head`

### 2. Redis Setup (Upstash)
1. Sign up at https://upstash.com (no credit card)
2. Create a new Redis database
3. Copy the connection string
4. Add `/1` for broker and `/2` for result backend

**Important:** The connection string from Upstash is a Redis URL (e.g. `rediss://default:password@upstash-host:6379`). Paste it directly into the Render environment variable `REDIS_URL`. Do **not** prefix it with `redis-cli --tls -u` or any other shell command — Render expects a URL, not a CLI invocation. The application code handles TLS automatically when the URL scheme is `rediss://`.

### 3. Backend Deployment (Render)
1. Push code to GitHub
2. Sign up at https://render.com (no credit card)
3. Create new Web Service from GitHub repo
4. Select Docker environment
5. Set environment variables from secrets:
   - DATABASE_URL (Neon connection string)
   - REDIS_URL (Upstash rediss:// URL)
   - CELERY_BROKER_URL (Upstash rediss:// URL with /1)
   - CELERY_RESULT_BACKEND (Upstash rediss:// URL with /2)
   - JWT_SECRET_KEY (generate a secure random value)
6. Set health check path to `/health/live`
7. Deploy

### 3a. Celery Worker & Beat Deployment (Render)
1. In Render, create a new Worker service from the same GitHub repo
2. Select Docker environment
3. Use the same environment variables as the web service
4. Set the start command to:
   ```
   celery -A ai_news_digest.workers.celery_app worker --loglevel=info --pool=solo
   ```
5. Deploy

### 3b. Celery Beat Deployment (Render)
1. In Render, create a second Worker service from the same GitHub repo
2. Select Docker environment
3. Use the same environment variables as the web service
4. Set the start command to:
   ```
   celery -A ai_news_digest.workers.celery_app beat --loglevel=info --schedule /tmp/celerybeat-schedule
   ```
5. Deploy

The Beat service manages the scheduled task pipeline (ingestion, summarization, categorization, digest generation, delivery) using the schedule defined in `celery_app.py`.

### 4. Frontend Deployment (Cloudflare Pages)
1. Sign up at https://pages.cloudflare.com (no credit card)
2. Connect GitHub repo
3. Set **Root directory** to `frontend`
4. Set **Build command** to `npm run build`
5. Set **Build output directory** to `dist`
6. Add `VITE_API_BASE_URL` environment variable
7. Deploy

Setting the root directory to `frontend` ensures Cloudflare installs
`typescript`, `vite`, and other frontend dependencies from
`frontend/package.json` before running the build. The old configuration
(root `/` with `cd frontend && npm run build`) installed only the root
`package.json` dependencies, which do not include `typescript` or `vite`,
causing `tsc: not found` during the build.

### 5. Manual / On-Demand Task Execution (GitHub Actions)
1. Go to repo Settings → Secrets and variables → Actions
2. Add all required secrets (same as backend)
3. The workflow in `.github/workflows/scheduled-tasks.yml` can be triggered manually via the GitHub Actions UI for ad-hoc task execution (e.g., re-running ingestion outside the normal Celery Beat schedule).

**Automated scheduling is handled entirely by Celery Beat on Render.**

## Render Configuration

The repository includes `render.yaml` which defines:

1. **Web Service** (`ai-news-digest-api`)
   - Runtime: Docker
   - Plan: Free
   - Health check: `/health/live`
   - Auto-deploy from `main` branch

2. **Worker Service** (`ai-news-digest-worker`)
   - Runtime: Docker
   - Plan: Free
   - Start command: `celery -A ai_news_digest.workers.celery_app worker --loglevel=info --pool=solo`

3. **Beat Service** (`ai-news-digest-beat`)
   - Runtime: Docker
   - Plan: Free
   - Start command: `celery -A ai_news_digest.workers.celery_app beat --loglevel=info --schedule /tmp/celerybeat-schedule`
   - **This is the scheduler of record.** It manages all automated periodic task execution.

4. **External Services** (not managed by Render)
   - Database: Neon PostgreSQL (set `DATABASE_URL`)
   - Redis: Upstash Redis (set `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`)

### Required Render Environment Variables

In the Render dashboard, set these environment variables for both the web and worker services:

| Variable | Value | Notes |
|----------|-------|-------|
| `DATABASE_URL` | Neon PostgreSQL connection string. Use the standard `postgresql://` format from Neon. The shared connection helper translates libpq options for asyncpg. | `postgresql://user:pass@host/ai_news_digest?sslmode=require&channel_binding=require` |
| `REDIS_URL` | Upstash Redis URL (rediss://) | Database 0 |
| `CELERY_BROKER_URL` | Upstash Redis URL (rediss://) | Database 1 |
| `CELERY_RESULT_BACKEND` | Upstash Redis URL (rediss://) | Database 2 |
| `JWT_SECRET_KEY` | Auto-generated by Render | Or provide your own 32+ char random string |
| `ENVIRONMENT` | `production` | |
| `DEBUG` | `false` | |
| `LOG_LEVEL` | `INFO` | |
| `CORS_ORIGINS` | `["https://ai-news-digest-doo.pages.dev"]` | Update if frontend URL changes |
| `OPENAI_ENABLED` | `false` | Enable if using AI features |
| `ANTHROPIC_ENABLED` | `false` | Enable if using AI features |
| `EMAIL_ENABLED` | `false` | Set to `true` and configure SMTP to enable email |
| `EMAIL_DEVELOPMENT_MODE` | `false` | |
| `EMAIL_PROVIDER` | `console` | Change to `smtp` in production with SMTP config |

### Port Configuration

Render provides the `PORT` environment variable automatically. The application reads it at startup:
- Default: `8000`
- Production (Render): uses `$PORT` from environment
- The Dockerfile passes `$PORT` to uvicorn via shell expansion

### Health Check

Render uses `/health/live` for health checks. This endpoint:
- Does not depend on external services
- Returns `200` with `{"status": "alive", "application": "AI News Digest"}`
- Is safe for Render's free-tier health check intervals

### Migrations

Database migrations run automatically during Docker image startup via the entrypoint script. Migrations use the same shared URL helper and `asyncpg` driver as the application. A standard `postgresql://` URL is normalized to `postgresql+asyncpg://` at the connection boundary. `sslmode=require`, `verify-ca`, and `verify-full` are consumed and translated to asyncpg's secure `ssl=True` setting; `sslmode=disable` is translated to explicit `ssl=False`, and `allow`/`prefer` are passed through asyncpg's native `ssl` negotiation. Neon URLs commonly also contain `channel_binding=require`; asyncpg 0.31 has no channel-binding keyword, so this libpq-only option is consumed and TLS is forced, but asyncpg cannot enforce the additional SCRAM channel-binding requirement. Supported asyncpg and SQLAlchemy dialect query parameters remain intact, while `application_name` becomes an asyncpg `server_settings` entry. Unsupported TLS certificate-file parameters fail closed rather than silently weakening verification. No `psycopg2` driver is used.

For manual migrations:

```bash
poetry run alembic upgrade head
```

## Limitations

### Database
- 0.5 GB storage (Neon)
- Scale-to-zero after 5 minutes idle (cold start on first connection)
- 100 compute-unit-hours/month

### Redis
- 256 MB storage (Upstash)
- 500,000 commands/month
- Single database

### Backend
- 750 instance hours/month (Render)
- Spins down after 15 minutes idle (cold start ~1 minute)
- Ephemeral filesystem

### Frontend
- 500 builds/month (Cloudflare Pages)
- 20,000 files per site

### Scheduled Tasks
- 2,000 minutes/month (GitHub Actions public repos)
- 5-minute minimum granularity
- Not real-time; depends on GitHub Actions scheduling

## Security

- HTTPS everywhere (managed by providers)
- JWT authentication
- CORS configured to specific origins
- Database connections use SSL (Neon, Upstash)
- Redis connections use TLS (Upstash rediss://)
- No secrets in repository
- Debug mode disabled in production

## Monitoring

- Health endpoints: `/health/live`, `/health/ready`
- Metrics endpoint: `/metrics` (admin auth required)
- Provider dashboards for logs and metrics

## Backup Strategy

- Neon: Automatic backups included
- Manual backup script: `scripts/backup_db.sh`
- Schedule periodic exports to local storage or R2

## Upgrade Path

When traffic grows:
1. Upgrade Neon to paid tier (~$19/month for 4 GB)
2. Upgrade Upstash to fixed plan (~$10/month for 250 MB)
3. Upgrade Render to Starter web service (~$7/month)
4. Celery Beat is already deployed as a separate Render worker service on the free tier

## First Paid Blocker

**AI API costs are the first unavoidable expense.**

The application supports OpenAI and Anthropic for AI-powered features. Both providers require payment:
- OpenAI: Pay-per-token after free trial credits exhausted
- Anthropic: Pay-per-token

All infrastructure (hosting, database, Redis, frontend, scheduler) can run for $0 indefinitely. AI features require paid API credits.

Email delivery also requires an SMTP provider (SendGrid, Mailgun, etc.) for production use. Console sender is development-only.
