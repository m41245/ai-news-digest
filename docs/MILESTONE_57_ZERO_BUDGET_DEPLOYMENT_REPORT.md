# Milestone 57 — Zero-Budget Infrastructure Discovery, Free Deployment Feasibility & Maximum $0 Implementation

## 1. Executive Summary

Milestone 57 investigated whether the AI News Intelligence Platform can be deployed publicly using only legitimate, currently available free tiers and free services. The investigation covered frontend hosting, backend hosting, databases, Redis, background workers, scheduled jobs, email, AI providers, monitoring, and CI/CD.

**Result:** The application can be architected to run entirely on $0 infrastructure indefinitely. The first unavoidable paid component is **AI API usage** (OpenAI/Anthropic), which requires payment after any free trial credits are exhausted. Email delivery also requires a paid SMTP provider for production use.

**Status:** $0 DEPLOYMENT ARCHITECTURE COMPLETE — EXTERNAL ACCESS REQUIRED

## 2. Repository Baseline

### Technology Stack
- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.x, Alembic
- **Frontend:** React 18, TypeScript 5, Vite 5, Tailwind CSS 3
- **Database:** PostgreSQL 16+ (asyncpg)
- **Cache/Broker:** Redis 7+
- **Task Queue:** Celery 5.4+
- **AI:** OpenAI, Anthropic
- **Email:** SMTP (aiosmtplib)
- **Testing:** Pytest (1,452+ unit tests), Vitest (25 frontend tests)
- **Lint/Type:** Ruff, MyPy strict
- **Containerization:** Docker, Docker Compose

### Current Validation Status
| Check | Result |
|-------|--------|
| Backend unit tests | 1,452 passed |
| Frontend tests | 25 passed |
| Ruff lint | All checks passed |
| MyPy | Success: no issues found in 324 source files |
| Frontend typecheck | Clean |
| Frontend build | Successful |
| Docker build (backend) | Successful |
| Docker build (frontend) | Successful |
| pip-audit | No known vulnerabilities |
| Migration head | 017 (linear chain 001→017) |

## 3. Free Providers Investigated

### PostgreSQL
- **Neon** — 0.5 GB storage, 100 CU-hours/month, scale-to-zero after 5 min idle, no credit card, permanent free tier
- **Supabase** — 500 MB, pauses after 1 week inactivity, no credit card, permanent free tier
- **Aiven** — 1 GB storage, 1 GB RAM, 1 CPU, powers off after inactivity, no credit card, permanent free tier
- **Miget** — 1 GiB storage, 256 MiB RAM, 0.1 vCPU, sleeps after 30 min, no credit card, permanent free tier
- **Render** — 1 GB storage, **expires 30 days after creation**, 14-day grace then deletion, NOT suitable for production

### Redis
- **Upstash** — 256 MB, 500,000 commands/month, no sleep, no credit card, permanent free tier
- **Redis Cloud** — 30 MB, 100 ops/sec, 30 connections, no credit card, permanent free tier
- **Aiven Valkey** — 1 GB RAM dedicated VM, powers off after inactivity, no credit card, permanent free tier
- **Layerbase** — 5 GB storage, 20 connections, sleeps after 60 min idle, no credit card, permanent free tier
- **Render Key Value** — 25 MB, **data not persistent**, NOT suitable for production

### Backend/Container Hosting
- **Render** — 750 instance hours/month, spins down after 15 min idle, Docker support, no credit card, permanent free tier
- **Railway** — $5 trial credit (30 days), then $1/month credit, NOT a permanent free tier, requires credit card for paid plans
- **Vercel** — Hobby plan free, serverless only, 300s timeout, no persistent workers
- **Cloudflare Workers** — Free plan, serverless only, 100K requests/day, no persistent workers
- **Fly.io** — Free tier requires credit card, scale-to-zero

### Frontend Static Hosting
- **Cloudflare Pages** — Unlimited bandwidth, 500 builds/month, 20,000 files, no credit card, permanent free tier
- **Vercel** — 100 GB bandwidth, 1M function invocations, 100 hours compute, no credit card, permanent free tier
- **Render Static Sites** — Free, counts against workspace bandwidth

### Scheduled Jobs/Workers
- **GitHub Actions** — 2,000 minutes/month for public repos, cron triggers, no credit card, permanent free tier
- **Render Cron Jobs** — Not available on free tier
- **Vercel Cron** — Available on Hobby plan, but limited to Vercel Functions

### Email
- **Console sender** — Development only, no actual delivery
- **SendGrid** — Free tier: 100 emails/day, requires credit card
- **Mailgun** — Free tier: 5,000 emails/month for 3 months, then paid
- **Amazon SES** — Pay-as-you-go, no free tier for new accounts
- **SMTP2GO** — Free tier: 1,000 emails/month, requires credit card

### AI Providers
- **OpenAI** — Paid API, no permanent free tier (trial credits may be available)
- **Anthropic** — Paid API, no permanent free tier
- **Both providers can be disabled** — Application runs without AI features

## 4. Free-Tier Comparison Summary

| Component | Provider | Free Tier | Permanent | Credit Card | Suitable for Production |
|-----------|----------|-----------|-----------|-------------|------------------------|
| PostgreSQL | Neon | 0.5 GB, 100 CU-hr/mo | Yes | No | Limited (scale-to-zero) |
| PostgreSQL | Supabase | 500 MB | Yes | No | Limited (pauses after 1 week) |
| PostgreSQL | Aiven | 1 GB, 1 CPU, 1 GB RAM | Yes | No | Limited (powers off) |
| Redis | Upstash | 256 MB, 500K cmds/mo | Yes | No | Yes (small scale) |
| Redis | Redis Cloud | 30 MB, 100 ops/sec | Yes | No | Limited |
| Backend | Render | 750 hrs/mo | Yes | No | Limited (15-min sleep) |
| Frontend | Cloudflare Pages | Unlimited bandwidth | Yes | No | Yes |
| Scheduler | GitHub Actions | 2,000 min/mo | Yes | No | Yes |
| Email | None | Console only | N/A | N/A | No (development only) |
| AI | None | Disabled | N/A | N/A | No (features disabled) |

## 5. Selected Architecture

### Primary: Render + Neon + Upstash + Cloudflare Pages

```
Cloudflare Pages (Frontend SPA)
    ↓ HTTPS
Render Free Web Service (FastAPI Backend)
    ↓
Neon PostgreSQL (Free Tier)
    ↓
Upstash Redis (Free Tier)
    ↓
GitHub Actions Scheduled Workflows (Replaces Celery Beat)
```

### Why This Architecture

1. **Frontend (Cloudflare Pages):** Unlimited bandwidth, global CDN, automatic HTTPS, custom domains, 500 builds/month. Perfect for React/Vite SPA.

2. **Backend (Render):** Docker support, 750 free instance hours/month, custom domains + managed TLS, auto-deploy from GitHub. Spins down after 15 min idle but cold start is ~1 minute.

3. **Database (Neon):** PostgreSQL 16 compatible, 0.5 GB storage permanent free tier, scale-to-zero after 5 min idle. No credit card required.

4. **Redis (Upstash):** 256 MB storage, 500,000 commands/month, no sleep, Redis-compatible API, TLS support. Perfect for Celery broker + cache.

5. **Scheduler (GitHub Actions):** 2,000 minutes/month free for public repos, cron triggers at any frequency, replaces Celery Beat entirely without additional infrastructure.

## 6. Components Successfully Made $0

| Component | Status | Provider |
|-----------|--------|----------|
| Frontend hosting | $0 | Cloudflare Pages |
| Backend hosting | $0 | Render Free Web Service |
| PostgreSQL | $0 | Neon Free Tier |
| Redis | $0 | Upstash Free Tier |
| Scheduled tasks | $0 | GitHub Actions |
| CI/CD | $0 | GitHub Actions |
| Container registry | $0 | GitHub Container Registry |
| TLS certificates | $0 | Managed by providers |
| Monitoring | $0 | Built-in / provider dashboards |
| Backups | $0 | Neon automatic backups |

## 7. Components That Remain Blocked

| Component | Blocker | Required Action |
|-----------|---------|-----------------|
| AI features | Paid API | Obtain OpenAI/Anthropic API key (paid) |
| Email delivery | Paid SMTP | Obtain SMTP provider (SendGrid, Mailgun, etc.) |
| Domain name | ~$10-15/year | Purchase domain |
| 24/7 uptime | Free tier sleep | Upgrade to paid tier (~$7-20/month) |

## 8. Actual Deployment Attempts

### Local Validation
- Backend unit tests: 1,452 passed
- Frontend tests: 25 passed
- Ruff: all checks passed
- MyPy: clean
- Docker builds: successful
- Docker Compose configs: validated
- pip-audit: no vulnerabilities

### Repository Changes
- Created `render.yaml` — Render deployment configuration
- Created `.github/workflows/scheduled-tasks.yml` — GitHub Actions cron jobs replacing Celery Beat
- Created `scripts/scheduled/run_task.py` — Task runner for GitHub Actions
- Created `docs/FREE_DEPLOYMENT_ARCHITECTURE.md` — Complete deployment blueprint
- Created `docs/MILESTONE_57_ZERO_BUDGET_DEPLOYMENT_REPORT.md` — This report
- Updated `README.md` — M57 status
- Updated `docs/PROJECT_STATUS.md` — M57 status

### External Deployment
**Not performed.** No external accounts were created or accessed. The architecture is documented and configured but requires user action to:
1. Create Neon PostgreSQL account and database
2. Create Upstash Redis account
3. Create Render account and deploy backend
4. Create Cloudflare Pages account and deploy frontend
5. Configure GitHub secrets
6. Obtain AI API key (paid)
7. Obtain SMTP credentials (paid)

## 9. Exact Test Results

### Backend
```
poetry run ruff check src tests .................... All checks passed!
poetry run ruff format --check src tests ........... 535 files already formatted
poetry run mypy src ................................. Success: no issues found in 324 source files
poetry run pytest tests/unit -q --no-cov ............ 1452 passed, 34 warnings in 466.43s
```

### Frontend
```
npm run typecheck .................................. Clean
npm run build ...................................... ✓ built in 1.80s
npm test ........................................... 25 passed
```

### Security
```
poetry run pip-audit ................................ No known vulnerabilities found
docker compose config ............................... Valid
docker compose -f docker-compose.prod.yml config ... Valid
docker build -t ai-news-digest:test-build . ........ Successful
docker build -t ai-news-digest-frontend:test-build . Successful
```

## 10. Security Results

- HTTPS: Managed by providers (Render, Cloudflare Pages)
- CORS: Configurable via `CORS_ORIGINS` environment variable
- JWT: Stateless tokens, secret validation enforced
- Database SSL: Neon provides SSL by default
- Redis security: Upstash supports TLS (`rediss://`)
- Exposed ports: None (providers handle networking)
- Debug disabled: `DEBUG=false` enforced in production entrypoint
- Secure cookies: Not applicable (JWT in Authorization header)
- Rate limiting: Built-in middleware
- Health endpoints: `/health/live`, `/health/ready` public
- Metrics: `/metrics` requires admin authentication
- Authentication isolation: Role-based (anonymous, user, admin)
- Container security: Existing Docker security maintained
- Dependency vulnerabilities: pip-audit clean
- Secret scanning: No secrets in tracked files

## 11. Free-Tier Limitations

### Neon PostgreSQL
- 0.5 GB storage
- 100 compute-unit-hours/month
- Scale-to-zero after 5 minutes idle (cold start on first connection)
- Not covered by SLA

### Upstash Redis
- 256 MB storage
- 500,000 commands/month
- Single database
- Pay-as-you-go after free tier ($0.20 per 100K commands)

### Render Free Web Service
- 750 instance hours/month
- Spins down after 15 minutes idle (cold start ~1 minute)
- Ephemeral filesystem
- No persistent disks
- No horizontal scaling

### Cloudflare Pages
- 500 builds/month
- 20,000 files per site
- 100 projects per account

### GitHub Actions
- 2,000 minutes/month for public repos
- 5-minute minimum cron granularity
- Not real-time (depends on GitHub scheduling)

## 12. First Unavoidable Paid Blocker

**AI API Usage (OpenAI / Anthropic)**

Both OpenAI and Anthropic require payment for API access:
- OpenAI: Pay-per-token after any free trial credits
- Anthropic: Pay-per-token, no permanent free tier

The application is designed to work with or without AI providers (`OPENAI_ENABLED=false`, `ANTHROPIC_ENABLED=false`). When disabled, articles are ingested and stored but not summarized/categorized/analyzed by AI. The public API still serves articles with RSS excerpts.

**Secondary paid blocker: Email delivery**
- Console email sender is development-only
- Production SMTP requires a paid provider (SendGrid, Mailgun, Amazon SES, etc.)
- Minimum cost: ~$0-15/month depending on volume

**Tertiary paid blocker: Custom domain**
- Domain registration: ~$10-15/year
- Providers offer free subdomains (e.g., `onrender.com`, `pages.dev`)

## 13. Exact Next Steps

### For the Developer
1. Create accounts (no credit card required):
   - https://neon.tech — Create PostgreSQL database
   - https://upstash.com — Create Redis database
   - https://render.com — Create web service from GitHub repo
   - https://pages.cloudflare.com — Create Pages project from GitHub repo
   - https://github.com — Ensure repo is public (for Actions minutes)

2. Configure secrets:
   - GitHub Actions secrets: `FREE_DATABASE_URL`, `FREE_REDIS_URL`, `FREE_CELERY_BROKER_URL`, `FREE_CELERY_RESULT_BACKEND`, `FREE_JWT_SECRET_KEY`, etc.
   - Render environment variables
   - Cloudflare Pages environment variables

3. Run migrations:
   ```bash
   poetry run alembic upgrade head
   ```

4. Obtain paid credentials (when ready):
   - OpenAI API key or Anthropic API key
   - SMTP provider credentials (SendGrid, Mailgun, etc.)
   - Custom domain (optional)

### For Production Deployment
1. Push code to GitHub
2. Configure Render with `render.yaml`
3. Configure Cloudflare Pages with frontend build settings
4. Enable GitHub Actions scheduled-tasks workflow
5. Verify health endpoints
6. Test end-to-end flow

## 14. Final M57 Decision

**$0 DEPLOYMENT ARCHITECTURE COMPLETE — EXTERNAL ACCESS REQUIRED**

All repository-side work is complete:
- Comprehensive free-tier research conducted
- Best $0 architecture selected and documented
- Repository updated with free deployment configurations
- All quality gates verified (1,452 unit tests, 25 frontend tests, ruff clean, mypy clean, pip-audit clean)
- Documentation complete

The application can be deployed using only free services indefinitely. The first paid requirement is AI API access (OpenAI/Anthropic), which is an application-level feature dependency, not an infrastructure dependency. All infrastructure components (hosting, database, Redis, frontend, scheduler, CI/CD) can run at $0.

Activation requires external account creation and credential configuration by the operator.
