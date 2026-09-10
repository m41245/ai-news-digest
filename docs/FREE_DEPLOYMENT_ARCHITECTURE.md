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

### Scheduler: GitHub Actions
- 2,000 minutes/month free for public repos
- Replaces Celery Beat entirely
- Cron triggers at any frequency
- No additional infrastructure

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
CORS_ORIGINS=["https://your-frontend.pages.dev"]
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

### 3. Backend Deployment (Render)
1. Push code to GitHub
2. Sign up at https://render.com (no credit card)
3. Create new Web Service from GitHub repo
4. Select Docker environment
5. Set environment variables from secrets
6. Deploy

### 4. Frontend Deployment (Cloudflare Pages)
1. Sign up at https://pages.cloudflare.com (no credit card)
2. Connect GitHub repo
3. Set build command: `cd frontend && npm run build`
4. Set output directory: `frontend/dist`
5. Add `VITE_API_BASE_URL` environment variable
6. Deploy

### 5. Scheduled Tasks (GitHub Actions)
1. Go to repo Settings → Secrets and variables → Actions
2. Add all required secrets (same as backend)
3. The workflow in `.github/workflows/scheduled-tasks.yml` will run automatically

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
4. Move scheduled tasks back to Celery Beat on Render worker (~$7/month)

## First Paid Blocker

**AI API costs are the first unavoidable expense.**

The application supports OpenAI and Anthropic for AI-powered features. Both providers require payment:
- OpenAI: Pay-per-token after free trial credits exhausted
- Anthropic: Pay-per-token

All infrastructure (hosting, database, Redis, frontend, scheduler) can run for $0 indefinitely. AI features require paid API credits.

Email delivery also requires an SMTP provider (SendGrid, Mailgun, etc.) for production use. Console sender is development-only.
