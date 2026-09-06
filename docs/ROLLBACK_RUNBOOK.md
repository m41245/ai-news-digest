# Rollback Runbook

## Overview

This runbook provides step-by-step procedures for rolling back the AI News Digest application to a previous stable version.

## When to Rollback

- New deployment causes 5xx errors > 5% of traffic
- New deployment causes database migration failures
- New deployment causes Celery worker crashes
- New deployment causes data corruption
- New deployment breaks critical user flows

## Pre-Rollback Checklist

- [ ] Confirm issue is caused by new deployment
- [ ] Notify stakeholders of rollback
- [ ] Backup current database state
- [ ] Identify previous stable version tag

## Rollback Procedure

### 1. Stop Current Deployment

```bash
docker compose -f docker-compose.prod.yml stop web celery_worker celery_beat
```

### 2. Rollback Database (if needed)

If the new deployment included migrations:

```bash
# Option A: Rollback migrations
docker compose -f docker-compose.prod.yml exec web poetry run alembic downgrade -1

# Option B: Restore from pre-deployment backup
docker compose -f docker-compose.prod.yml exec postgres psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} < backup_before_deployment.sql
```

### 3. Deploy Previous Version

```bash
# Pull previous image
docker compose -f docker-compose.prod.yml pull ai-news-digest:previous-version

# Deploy previous version
docker compose -f docker-compose.prod.yml up -d --force-recreate \
  web celery_worker celery_beat \
  --build-arg DOCKER_IMAGE=ai-news-digest:previous-version
```

### 4. Verify Rollback

```bash
# Wait for containers to start
sleep 30

# Check health
curl -f http://localhost:8000/health/live
curl -f http://localhost:8000/health/ready

# Check container status
docker compose -f docker-compose.prod.yml ps

# Check logs for errors
docker compose -f docker-compose.prod.yml logs web --tail 50
docker compose -f docker-compose.prod.yml logs celery_worker --tail 50

# Run smoke tests
poetry run python tests/smoke_prod.py
```

### 5. Post-Rollback

1. Confirm service is stable
2. Update status page / notify stakeholders
3. Create incident ticket for root cause analysis
4. Schedule fix for next deployment

## Emergency Rollback (Database Only)

If the application is healthy but database is corrupted:

```bash
# Stop application
docker compose -f docker-compose.prod.yml stop web celery_worker celery_beat

# Restore database from backup
docker compose -f docker-compose.prod.yml exec postgres psql -U ${POSTGRES_USER} -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
docker compose -f docker-compose.prod.yml exec postgres psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} < latest_backup.sql

# Run migrations to current version
docker compose -f docker-compose.prod.yml exec web poetry run alembic upgrade head

# Restart application
docker compose -f docker-compose.prod.yml up -d web celery_worker celery_beat

# Verify
curl -f http://localhost:8000/health/ready
```

## Rollback Tags

Keep tags for previous stable versions:
- `v1.0.0` — last known stable production version
- `v0.9.0` — previous stable version (for double rollback)

Never delete or overwrite production tags.

## Post-Rollback Actions

1. **Root cause analysis**: Determine why the deployment failed
2. **Fix in feature branch**: Create a fix branch from the rolled-back version
3. **Test fix in staging**: Deploy to staging and verify
4. **Re-deploy**: Follow normal deployment procedure with the fix
5. **Update runbooks**: Document lessons learned
