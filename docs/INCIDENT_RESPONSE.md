# Incident Response & Recovery

## Incident Classification

| Severity | Description | Response Time |
|----------|-------------|---------------|
| P1 | Application down, health checks failing | Immediate |
| P2 | Degraded performance, partial functionality | 15 minutes |
| P3 | Non-critical feature failure | 1 hour |
| P4 | Cosmetic or documentation issue | Next business day |

---

## Common Incidents

### Container won't start

**Diagnosis:**
```bash
docker compose -f docker-compose.prod.yml logs web
```

**Common causes:**
- Missing environment variables
- Database connection failure
- Migration failure
- Port conflict

**Recovery:**
```bash
docker compose -f docker-compose.prod.yml up -d --force-recreate
```

---

### Database connection failed

**Diagnosis:**
```bash
docker compose -f docker-compose.prod.yml exec postgres pg_isready -U postgres
docker compose -f docker-compose.prod.yml logs web | grep -i database
```

**Recovery:**
1. Verify PostgreSQL container is healthy:
   ```bash
   docker compose -f docker-compose.prod.yml ps postgres
   ```
2. Verify `DATABASE_URL` format and credentials
3. Restart PostgreSQL if healthy check fails:
   ```bash
   docker compose -f docker-compose.prod.yml restart postgres
   ```

---

### Redis connection failed

**Diagnosis:**
```bash
docker compose -f docker-compose.prod.yml exec redis redis-cli -a redis ping
```

**Recovery:**
1. Verify Redis container is healthy
2. Verify `REDIS_PASSWORD` matches in `.env.prod.local`
3. Restart Redis:
   ```bash
   docker compose -f docker-compose.prod.yml restart redis
   ```

---

### Migrations failing

**Diagnosis:**
```bash
docker compose -f docker-compose.prod.yml logs web | grep -i alembic
docker compose -f docker-compose.prod.yml exec web alembic current
```

**Recovery:**
1. Check migration file syntax
2. Restore from backup if migration partially applied
3. Fix migration, then restart web container

---

### Auth failures

**Diagnosis:**
- Verify `JWT_SECRET_KEY` is set and consistent
- Check logs for JWT validation errors

**Recovery:**
- Restore previous `JWT_SECRET_KEY` if changed
- Invalidate all sessions by rotating the secret (users must re-login)

---

### Worker not processing

**Diagnosis:**
```bash
docker compose -f docker-compose.prod.yml logs celery_worker
docker compose -f docker-compose.prod.yml logs celery_beat
```

**Recovery:**
```bash
docker compose -f docker-compose.prod.yml restart celery_worker celery_beat
```

---

## Recovery Procedure

### Full stack restart

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod.local down
docker compose -f docker-compose.prod.yml --env-file .env.prod.local up -d
```

### Database restore

```bash
bash scripts/backup_db.sh
bash scripts/restore_db.sh backup_20240101_000000.sql
```

### Image rollback

```bash
DOCKER_IMAGE=ghcr.io/m41245/ai-news-digest:v0.9.0 docker compose -f docker-compose.prod.yml --env-file .env.prod.local up -d --force-recreate
```

---

## Escalation

1. Check application logs first
2. Verify dependent services (PostgreSQL, Redis)
3. Check reverse proxy / TLS status
4. Review recent deployments or configuration changes
5. Escalate to on-call engineer if unresolved within SLA
