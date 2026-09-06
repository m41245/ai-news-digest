# Deployment Runbook

## Overview

This runbook describes the step-by-step procedure for deploying the AI News Digest application to production.

## Pre-Deployment Checklist

- [ ] All tests pass: `poetry run pytest tests/unit/ -q`
- [ ] Lint passes: `poetry run ruff check src/ tests/`
- [ ] Type check passes: `poetry run mypy src/ tests/`
- [ ] Security scan passes: `poetry run pip-audit`
- [ ] Secret hygiene check passes: `poetry run python scripts/check_secret_hygiene.py`
- [ ] Frontend tests pass: `cd frontend && npm test`
- [ ] Frontend build passes: `cd frontend && npm run build`
- [ ] Docker image builds: `docker build -t ai-news-digest:deploy .`
- [ ] All migrations reviewed: `alembic history --verbose`
- [ ] Staging smoke tests pass: `poetry run python tests/smoke_prod.py`
- [ ] Backup completed: `docs/POSTGRES_BACKUP_RESTORE.md`

## Deployment Procedure

### 1. Build and Push Image

```bash
# Build production image
docker build -t ai-news-digest:${VERSION} -f Dockerfile .

# Tag for registry
docker tag ai-news-digest:${VERSION} ghcr.io/m41245/ai-news-digest:${VERSION}
docker tag ai-news-digest:${VERSION} ghcr.io/m41245/ai-news-digest:latest

# Push to registry
docker push ghcr.io/m41245/ai-news-digest:${VERSION}
docker push ghcr.io/m41245/ai-news-digest:latest
```

### 2. Update Environment Variables

Ensure `.env.prod.local` contains:
- `JWT_SECRET_KEY` — cryptographically secure random string (32+ chars)
- `POSTGRES_PASSWORD` — strong password
- `REDIS_PASSWORD` — strong password (if enabled)
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` — email provider credentials
- `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` — AI provider credentials (if enabled)
- `SENTRY_DSN` — Sentry DSN for error tracking (optional but recommended)
- `CORS_ORIGINS` — allowed origins for production

### 3. Deploy Stack

```bash
# Pull latest images
docker compose -f docker-compose.prod.yml pull

# Deploy with zero downtime
docker compose -f docker-compose.prod.yml up -d --force-recreate

# Wait for health checks
sleep 30

# Verify health
curl -f http://localhost:8000/health/live
curl -f http://localhost:8000/health/ready
```

### 4. Run Migrations

Migrations run automatically via Docker entrypoint. To run manually:

```bash
docker compose -f docker-compose.prod.yml exec web poetry run alembic upgrade head
```

### 5. Verify Deployment

```bash
# Check container status
docker compose -f docker-compose.prod.yml ps

# Check application logs
docker compose -f docker-compose.prod.yml logs web --tail 50

# Check worker logs
docker compose -f docker-compose.prod.yml logs celery_worker --tail 50

# Check metrics endpoint
curl -s http://localhost:8000/metrics | head -20

# Run smoke tests
poetry run python tests/smoke_prod.py
```

## Post-Deployment

1. Monitor error rates and latency for 15 minutes
2. Verify Celery tasks are being processed
3. Check notification delivery (if applicable)
4. Update `docs/PROJECT_STATUS.md` with deployment timestamp

## Rollback Procedure

See `docs/ROLLBACK_RUNBOOK.md` for detailed rollback procedures.

## Quick Rollback

```bash
# Rollback to previous image
docker compose -f docker-compose.prod.yml up -d --force-recreate \
  --build-arg DOCKER_IMAGE=ai-news-digest:previous-version

# Verify
curl -f http://localhost:8000/health/ready
```
