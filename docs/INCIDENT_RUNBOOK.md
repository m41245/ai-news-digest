# Incident Runbook

## Overview

This runbook provides step-by-step procedures for responding to common production incidents affecting the AI News Digest application.

## Incident Severity Levels

| Severity | Description | Response Time | Examples |
|----------|-------------|---------------|----------|
| P1 - Critical | Complete service outage or data loss | Immediate | Database down, application not responding |
| P2 - High | Major feature degradation | 30 minutes | Celery workers not processing, notifications not delivering |
| P3 - Medium | Minor feature degradation | 2 hours | Slow API responses, intermittent errors |
| P4 - Low | Cosmetic or non-urgent issues | Next business day | UI bugs, logging issues |

## Common Incidents

### 1. Application Down

**Symptoms:**
- `GET /health/live` returns non-200
- Application container not running
- Reverse proxy returning 502/503

**Diagnosis:**
```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs web --tail 50
docker compose -f docker-compose.prod.yml logs postgres --tail 20
docker compose -f docker-compose.prod.yml logs redis --tail 20
```

**Resolution:**
```bash
# Restart web service
docker compose -f docker-compose.prod.yml restart web

# If restart fails, check logs for OOM or configuration errors
docker compose -f docker-compose.prod.yml logs web --tail 100

# If database is the issue, check PostgreSQL logs
docker compose -f docker-compose.prod.yml logs postgres --tail 50
```

### 2. Database Unavailable

**Symptoms:**
- `GET /health/ready` shows `database: error`
- Application logs show connection pool exhausted
- PostgreSQL container not healthy

**Diagnosis:**
```bash
docker compose -f docker-compose.prod.yml exec postgres pg_isready -U ${POSTGRES_USER}
docker compose -f docker-compose.prod.yml logs postgres --tail 50
```

**Resolution:**
```bash
# Restart PostgreSQL
docker compose -f docker-compose.prod.yml restart postgres

# If data corruption suspected, restore from backup
# See docs/POSTGRES_BACKUP_RESTORE.md
```

### 3. Redis Unavailable

**Symptoms:**
- `GET /health/ready` shows `cache: error`
- Rate limiting not working
- Celery broker not responding

**Diagnosis:**
```bash
docker compose -f docker-compose.prod.yml exec redis redis-cli ping
docker compose -f docker-compose.prod.yml logs redis --tail 20
```

**Resolution:**
```bash
# Restart Redis
docker compose -f docker-compose.prod.yml restart redis

# If data loss is acceptable, restart without persistence
docker compose -f docker-compose.prod.yml exec redis redis-cli FLUSHALL
```

### 4. Celery Workers Not Processing

**Symptoms:**
- Tasks accumulating in queue
- No new digests generated
- Notifications not being sent

**Diagnosis:**
```bash
docker compose -f docker-compose.prod.yml logs celery_worker --tail 50
docker compose -f docker-compose.prod.yml exec redis redis-cli LLEN celery
docker compose -f docker-compose.prod.yml exec redis redis-cli LLEN celery:task:revoked
```

**Resolution:**
```bash
# Restart workers
docker compose -f docker-compose.prod.yml restart celery_worker celery_beat

# Purge stuck tasks (use with caution)
docker compose -f docker-compose.prod.yml exec celery_worker celery -A ai_news_digest.workers.celery_app purge
```

### 5. High Error Rate

**Symptoms:**
- HTTP 5xx rate spike
- Elevated error metrics

**Diagnosis:**
```bash
curl -s http://localhost:8000/metrics | grep http_error_total
docker compose -f docker-compose.prod.yml logs web --tail 100 | grep -i error
```

**Resolution:**
1. Identify error pattern from logs
2. Check if dependency (DB, Redis, AI provider) is failing
3. If AI provider failing, check `OPENAI_ENABLED` / `ANTHROPIC_ENABLED`
4. Roll back recent deployment if error coincides with deploy

### 6. Migration Failure

**Symptoms:**
- Application fails to start
- Alembic reports migration errors
- Database schema inconsistent

**Diagnosis:**
```bash
poetry run alembic current
poetry run alembic history
```

**Resolution:**
```bash
# Rollback one step
poetry run alembic downgrade -1

# Or restore from backup
# See docs/MIGRATION_ROLLBACK.md
```

## Escalation

| Issue | Escalation Path |
|-------|-----------------|
| Database corruption | DBA / Infrastructure team |
| Security breach | Security team / CISO |
| AI provider outage | Enable fallback provider or disable AI features |
| DNS/TLS issues | Infrastructure / DevOps |
| Data loss | Restore from backup, notify stakeholders |

## Communication

During an incident:
1. Update `docs/INCIDENT_LOG.md` with timeline and actions
2. Notify stakeholders via agreed channel
3. Post-mortem within 24 hours for P1/P2 incidents

## Post-Incident

1. **Root cause analysis**: Identify the underlying cause
2. **Remediation**: Implement fix to prevent recurrence
3. **Documentation**: Update runbooks and monitoring
4. **Follow-up**: Verify fix in production, close incident
