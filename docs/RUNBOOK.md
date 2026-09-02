# Operational Runbook

## Overview

This runbook provides step-by-step procedures for common operational tasks and incident response for the AI News Digest production deployment.

**Prerequisites:**
- SSH access to the production host
- Docker and Docker Compose installed
- `.env.prod.local` configured with production secrets

---

## 1. Deployment

### Standard Deployment

Use this procedure for routine deployments of a new version.

**Pre-deployment:**
1. Verify the new image is available in GHCR:
   ```bash
   docker pull ghcr.io/m41245/ai-news-digest:v1.1.0
   ```

2. Back up the database:
   ```bash
   bash scripts/backup_db.sh
   ```

3. Review release notes for breaking changes or migration requirements.

**Deployment:**
1. Pull the latest code and tag:
   ```bash
   git fetch --tags
   git checkout v1.1.0
   ```

2. Update the image reference and restart:
   ```bash
   DOCKER_IMAGE=ghcr.io/m41245/ai-news-digest:v1.1.0 docker compose -f docker-compose.prod.yml --env-file .env.prod.local up -d --force-recreate
   ```

3. Verify health:
   ```bash
   curl -f http://localhost:8000/health/live
   curl -f http://localhost:8000/health/ready
   ```

4. Run smoke tests:
   ```bash
   poetry run python tests/smoke_prod.py
   ```

5. Verify Celery workers are processing:
   ```bash
   docker compose -f docker-compose.prod.yml logs -f celery_worker --tail=20
   ```

**Post-deployment:**
- Monitor error rates for 15 minutes
- Verify scheduled tasks execute on next beat cycle
- Confirm email delivery (if enabled) on next digest

---

## 2. Rollback

Use this procedure to revert to a previous version after a failed deployment.

**Immediate rollback (same session):**
```bash
DOCKER_IMAGE=ghcr.io/m41245/ai-news-digest:v1.0.0 docker compose -f docker-compose.prod.yml --env-file .env.prod.local up -d --force-recreate
```

**If database migration was applied:**
1. Stop all services:
   ```bash
   docker compose -f docker-compose.prod.yml --env-file .env.prod.local down
   ```

2. Restore database from backup taken before deployment:
   ```bash
   bash scripts/restore_db.sh backup_20240101_000000.sql
   ```

3. Deploy previous version:
   ```bash
   DOCKER_IMAGE=ghcr.io/m41245/ai-news-digest:v1.0.0 docker compose -f docker-compose.prod.yml --env-file .env.prod.local up -d
   ```

4. Verify health and run smoke tests.

**Important notes:**
- The `JWT_SECRET_KEY` must remain consistent across rollouts; changing it invalidates all active sessions.
- Database migrations are forward-only by default. To roll back schema changes, restore from a backup.
- Celery workers use the same image. Restart them alongside the web service to ensure version parity.

---

## 3. Restart

Use this procedure for restarting services after configuration changes or to clear transient issues.

**Restart a single service:**
```bash
docker compose -f docker-compose.prod.yml restart web
docker compose -f docker-compose.prod.yml restart celery_worker
docker compose -f docker-compose.prod.yml restart celery_beat
docker compose -f docker-compose.prod.yml restart frontend
```

**Restart with recreation (applies config changes):**
```bash
docker compose -f docker-compose.prod.yml up -d --force-recreate web
```

**Full stack restart:**
```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod.local down
docker compose -f docker-compose.prod.yml --env-file .env.prod.local up -d
```

**Rolling restart (minimize downtime):**
```bash
# Restart web first (frontend depends on it)
docker compose -f docker-compose.prod.yml up -d --force-recreate web
# Wait for health
curl -f http://localhost:8000/health/ready
# Then restart workers
docker compose -f docker-compose.prod.yml up -d --force-recreate celery_worker celery_beat
# Finally restart frontend
docker compose -f docker-compose.prod.yml up -d --force-recreate frontend
```

---

## 4. Health Diagnosis

Use this procedure to diagnose health issues.

**Step 1: Check container status**
```bash
docker compose -f docker-compose.prod.yml ps
```

**Step 2: Check health endpoints**
```bash
# Liveness (is the process running?)
curl -v http://localhost:8000/health/live

# Readiness (are dependencies healthy?)
curl -v http://localhost:8000/health/ready

# Metrics subsystem
curl -v http://localhost:8000/metrics/health
```

**Step 3: Check container health details**
```bash
docker inspect --format='{{.State.Health.Status}}' ai_news_digest_web
docker inspect --format='{{.State.Health.Status}}' ai_news_digest_db
docker inspect --format='{{.State.Health.Status}}' ai_news_digest_redis
docker inspect --format='{{.State.Health.Status}}' ai_news_digest_worker
```

**Step 4: Review recent logs**
```bash
docker compose -f docker-compose.prod.yml logs --tail=100 web
docker compose -f docker-compose.prod.yml logs --tail=100 celery_worker
```

**Step 5: Check resource usage**
```bash
docker stats --no-stream
```

**Step 6: Verify network connectivity**
```bash
# From web container to database
docker compose -f docker-compose.prod.yml exec web python -c "
import asyncpg, asyncio
async def test():
    conn = await asyncpg.connect('postgresql://user:pass@postgres:5432/ai_news_digest')
    print(await conn.fetchval('SELECT 1'))
    await conn.close()
asyncio.run(test())
"

# From web container to Redis
docker compose -f docker-compose.prod.yml exec web python -c "
import redis, os
r = redis.from_url(os.environ['REDIS_URL'])
print(r.ping())
"
```

---

## 5. Database Outage

Use this procedure when PostgreSQL is unavailable.

**Symptoms:**
- `/health/ready` returns non-200 with `{"checks":{"database":"error"}}`
- Application logs show `database_connection_error`
- 5xx errors on all database-dependent endpoints

**Diagnosis:**
```bash
# Check PostgreSQL container
docker compose -f docker-compose.prod.yml ps postgres
docker inspect --format='{{.State.Health.Status}}' ai_news_digest_db

# Check PostgreSQL logs
docker compose -f docker-compose.prod.yml logs postgres

# Test connectivity from web container
docker compose -f docker-compose.prod.yml exec postgres pg_isready -U ${POSTGRES_USER}
```

**Recovery:**
1. Restart PostgreSQL:
   ```bash
   docker compose -f docker-compose.prod.yml restart postgres
   ```

2. If restart fails, check for disk space:
   ```bash
   df -h
   docker system df
   ```

3. If data corruption is suspected, restore from backup:
   ```bash
   bash scripts/restore_db.sh backup_20240101_000000.sql
   ```

4. Verify recovery:
   ```bash
   curl -f http://localhost:8000/health/ready
   ```

**Prevention:**
- Monitor disk usage (alert at 80%)
- Schedule regular backups
- Test restore procedure monthly

---

## 6. Redis Outage

Use this procedure when Redis is unavailable.

**Symptoms:**
- `/health/ready` returns non-200 with `{"checks":{"cache":"error"}}`
- Application logs show `redis_connection_error`
- Celery tasks fail to enqueue

**Diagnosis:**
```bash
# Check Redis container
docker compose -f docker-compose.prod.yml ps redis
docker inspect --format='{{.State.Health.Status}}' ai_news_digest_redis

# Check Redis logs
docker compose -f docker-compose.prod.yml logs redis

# Test connectivity
docker compose -f docker-compose.prod.yml exec redis redis-cli -a ${REDIS_PASSWORD} ping
```

**Recovery:**
1. Restart Redis:
   ```bash
   docker compose -f docker-compose.prod.yml restart redis
   ```

2. If restart fails, check for memory pressure:
   ```bash
   docker stats ai_news_digest_redis --no-stream
   ```

3. If data loss is acceptable (Redis is used as cache/broker):
   ```bash
   docker compose -f docker-compose.prod.yml stop redis
   docker volume rm ai-news-digest_redis_data
   docker compose -f docker-compose.prod.yml up -d redis
   ```

4. Verify recovery:
   ```bash
   curl -f http://localhost:8000/health/ready
   ```

**Prevention:**
- Monitor Redis memory usage
- Set appropriate `maxmemory` policy
- Use Redis persistence (AOF enabled in production)

---

## 7. Celery Failure

Use this procedure when Celery workers or beat are not processing tasks.

**Symptoms:**
- Scheduled tasks not executing (no new digests generated)
- Task queue backing up
- Worker or beat container unhealthy

**Diagnosis:**
```bash
# Check worker and beat status
docker compose -f docker-compose.prod.yml ps celery_worker celery_beat
docker inspect --format='{{.State.Health.Status}}' ai_news_digest_worker
docker inspect --format='{{.State.Health.Status}}' ai_news_digest_beat

# Check worker logs
docker compose -f docker-compose.prod.yml logs celery_worker --tail=100
docker compose -f docker-compose.prod.yml logs celery_beat --tail=100

# Check broker connectivity
docker compose -f docker-compose.prod.yml exec celery_worker celery -A ai_news_digest.workers.celery_app inspect active
```

**Recovery:**
1. Restart workers and beat:
   ```bash
   docker compose -f docker-compose.prod.yml restart celery_worker celery_beat
   ```

2. If tasks are stuck, purge the queue (use with caution):
   ```bash
   docker compose -f docker-compose.prod.yml exec celery_worker celery -A ai_news_digest.workers.celery_app purge
   ```

3. Manually trigger a task to verify:
   ```bash
   curl -X POST http://localhost:8000/api/v1/admin/ingestion/run \
     -H "Authorization: Bearer <admin_token>"
   ```

4. Monitor task execution:
   ```bash
   docker compose -f docker-compose.prod.yml logs -f celery_worker
   ```

**Prevention:**
- Monitor task failure rates
- Set up alerts for task backlog
- Test task execution after deployments

---

## 8. Frontend Failure

Use this procedure when the frontend is not serving or displaying errors.

**Symptoms:**
- Frontend URL returns 502/504 or connection refused
- Static assets not loading
- API requests from frontend failing

**Diagnosis:**
```bash
# Check frontend container
docker compose -f docker-compose.prod.yml ps frontend
docker inspect --format='{{.State.Health.Status}}' ai_news_digest_frontend

# Check frontend logs
docker compose -f docker-compose.prod.yml logs frontend --tail=100

# Test frontend directly
curl -v http://localhost:3000/

# Check Nginx configuration
docker compose -f docker-compose.prod.yml exec frontend nginx -t
```

**Recovery:**
1. Restart frontend:
   ```bash
   docker compose -f docker-compose.prod.yml restart frontend
   ```

2. If API requests fail, verify backend is healthy:
   ```bash
   curl -f http://localhost:8000/health/ready
   ```

3. If API base URL is misconfigured, rebuild with correct value:
   ```bash
   docker compose -f docker-compose.prod.yml build --build-arg VITE_API_BASE_URL=/api frontend
   docker compose -f docker-compose.prod.yml up -d --force-recreate frontend
   ```

4. Check reverse proxy configuration:
   ```bash
   # On the reverse proxy host
   nginx -t
   systemctl reload nginx
   ```

**Prevention:**
- Monitor frontend health endpoint
- Test frontend build in CI/CD
- Verify API base URL in deployment configuration

---

## 9. Backup Restoration

Use this procedure to restore the database from a backup.

**When to restore:**
- Data corruption
- Failed migration
- Accidental data deletion
- Disaster recovery

**Pre-restore:**
1. Identify the backup file to restore:
   ```bash
   ls -la backups/
   ```

2. Create a fresh backup of current state (for rollback):
   ```bash
   bash scripts/backup_db.sh
   ```

**Restore procedure:**
1. Run the restore script:
   ```bash
   bash scripts/restore_db.sh backup_20240101_000000.sql
   ```

2. The restore script will:
   - Stop Celery workers
   - Drop and recreate the database
   - Restore from the SQL dump
   - Run migrations
   - Restart workers

3. Verify restoration:
   ```bash
   curl -f http://localhost:8000/health/ready
   ```

4. Run smoke tests:
   ```bash
   poetry run python tests/smoke_prod.py
   ```

**Manual restore (if script fails):**
```bash
# Stop workers
docker compose -f docker-compose.prod.yml stop celery_worker celery_beat

# Restore database
docker compose -f docker-compose.prod.yml exec -T postgres psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} < backup_file.sql

# Run migrations
docker compose -f docker-compose.prod.yml exec web alembic upgrade head

# Restart workers
docker compose -f docker-compose.prod.yml start celery_worker celery_beat
```

**Prevention:**
- Schedule automated backups (daily recommended)
- Test restore procedure monthly
- Store backups in multiple locations

---

## 10. Secret Rotation

Use this procedure to rotate secrets (JWT secret, database password, Redis password).

### JWT Secret Rotation

**Impact:** All users must log in again (existing tokens invalidated).

1. Generate new secret:
   ```bash
   openssl rand -hex 32
   ```

2. Update `.env.prod.local`:
   ```
   JWT_SECRET_KEY=<new_secret>
   ```

3. Restart all services:
   ```bash
   docker compose -f docker-compose.prod.yml --env-file .env.prod.local up -d --force-recreate
   ```

4. Verify health:
   ```bash
   curl -f http://localhost:8000/health/live
   ```

### Database Password Rotation

1. Connect to PostgreSQL and change password:
   ```bash
   docker compose -f docker-compose.prod.yml exec postgres psql -U ${POSTGRES_USER} -c "ALTER USER ${POSTGRES_USER} PASSWORD 'new_password';"
   ```

2. Update `.env.prod.local`:
   ```
   POSTGRES_PASSWORD=new_password
   ```

3. Restart all services:
   ```bash
   docker compose -f docker-compose.prod.yml --env-file .env.prod.local up -d --force-recreate
   ```

### Redis Password Rotation

1. Update `.env.prod.local`:
   ```
   REDIS_PASSWORD=new_password
   ```

2. Restart Redis with new password:
   ```bash
   docker compose -f docker-compose.prod.yml --env-file .env.prod.local up -d --force-recreate redis
   ```

3. Restart all services that use Redis:
   ```bash
   docker compose -f docker-compose.prod.yml --env-file .env.prod.local up -d --force-recreate
   ```

**Prevention:**
- Rotate secrets on a regular schedule (90 days recommended)
- Rotate immediately if compromise is suspected
- Use a secrets manager for production environments

---

## 11. Certificate Renewal

Use this procedure to renew TLS certificates for the reverse proxy.

**Note:** This project does not manage TLS certificates directly. TLS is terminated at the reverse proxy (nginx/Traefik).

### Let's Encrypt (Certbot)

1. Renew certificates:
   ```bash
   certbot renew
   ```

2. Reload reverse proxy:
   ```bash
   systemctl reload nginx
   ```

### Manual Certificate Update

1. Copy new certificate files:
   ```bash
   cp /path/to/fullchain.pem /etc/ssl/certs/ai-news-digest.crt
   cp /path/to/privkey.pem /etc/ssl/private/ai-news-digest.key
   ```

2. Update reverse proxy configuration if paths changed.

3. Test configuration:
   ```bash
   nginx -t
   ```

4. Reload reverse proxy:
   ```bash
   systemctl reload nginx
   ```

5. Verify certificate:
   ```bash
   echo | openssl s_client -connect your-domain.com:443 2>/dev/null | openssl x509 -noout -dates
   ```

**Prevention:**
- Set up automatic renewal (certbot timer)
- Monitor certificate expiry (alert at 30 days, 7 days)
- Test renewal procedure in staging

---

## 12. Incident Investigation

Use this procedure to investigate production incidents.

### Step 1: Gather Information

1. Identify the incident start time and symptoms.

2. Check current system state:
   ```bash
   docker compose -f docker-compose.prod.yml ps
   docker stats --no-stream
   curl -f http://localhost:8000/health/ready
   ```

3. Review recent logs:
   ```bash
   # Last 500 lines from all services
   docker compose -f docker-compose.prod.yml logs --tail=500

   # Logs since incident start time
   docker compose -f docker-compose.prod.yml logs --since="2024-01-01T00:00:00"
   ```

### Step 2: Identify Root Cause

1. Check for recent changes:
   ```bash
   # Recent deployments
   git log --oneline -10

   # Recent configuration changes
   git diff HEAD~5 -- .env.prod.local.docker-compose.prod.yml
   ```

2. Analyze error patterns:
   ```bash
   # Count errors by type
   docker compose -f docker-compose.prod.yml logs web | grep -c "ERROR"

   # Find specific error patterns
   docker compose -f docker-compose.prod.yml logs web | grep -i "exception\|error\|failed"
   ```

3. Check metrics:
   ```bash
  # Get current metrics (requires admin token)
  curl -H "Authorization: Bearer <admin_token>" http://localhost:8000/metrics/
  
  # Check pipeline status for operational warnings
  curl -H "Authorization: Bearer <admin_token>" http://localhost:8000/api/v1/admin/pipeline/status
   ```

### Step 3: Document the Incident

Create an incident record with:
- Incident ID and timestamp
- Severity level (P1-P4)
- Symptoms observed
- Root cause identified
- Steps taken to resolve
- Time to resolution
- Follow-up actions

### Step 4: Post-Incident Review

1. Conduct a blameless post-mortem within 48 hours.

2. Identify what went well and what could be improved.

3. Create action items:
   - Monitoring gaps to address
   - Runbook updates needed
   - Code fixes required
   - Process improvements

4. Track action items to completion.

### Incident Classification

| Severity | Description | Response Time | Escalation |
|----------|-------------|---------------|------------|
| P1 | Application down, health checks failing | Immediate | Page on-call |
| P2 | Degraded performance, partial functionality | 15 minutes | Slack notification |
| P3 | Non-critical feature failure | 1 hour | Next business day |
| P4 | Cosmetic or documentation issue | Next business day | Backlog |

---

## Quick Reference

### Essential Commands

```bash
# Full status check
docker compose -f docker-compose.prod.yml ps
docker stats --no-stream
curl -f http://localhost:8000/health/live
curl -f http://localhost:8000/health/ready

# View logs
docker compose -f docker-compose.prod.yml logs -f web
docker compose -f docker-compose.prod.yml logs -f celery_worker

# Restart everything
docker compose -f docker-compose.prod.yml --env-file .env.prod.local up -d --force-recreate

# Backup database
bash scripts/backup_db.sh

# Run smoke tests
poetry run python tests/smoke_prod.py
```

### Contact Information

| Role | Contact | When to Escalate |
|------|---------|------------------|
| On-call Engineer | (configure PagerDuty/Opsgenie) | P1 incidents |
| Platform Team | (Slack channel) | Infrastructure issues |
| Development Team | (Slack channel) | Application bugs |

### Related Documentation

- [Monitoring Strategy](MONITORING.md) - Alert conditions and metrics
- [Deployment Guide](DEPLOYMENT.md) - Full deployment procedures
- [Incident Response](INCIDENT_RESPONSE.md) - Incident classification and common issues
- [Production Configuration](PRODUCTION_CONFIGURATION.md) - Environment variables and secrets
