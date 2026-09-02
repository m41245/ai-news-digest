# Production Deployment Guide

## Host Requirements

### Software

- **Docker Engine** 24.0+ (tested with 29.6.2)
- **Docker Compose** v2.0+ (tested with v5.3.1)
- **Git** (for cloning and tagging)
- **curl** or equivalent HTTP client (for health checks)

### Network / Firewall

- Outbound HTTPS (443) for pulling images from GHCR
- Outbound HTTP/HTTPS for AI provider APIs (if enabled)
- Inbound port `8000/tcp` on `127.0.0.1` for the reverse proxy
- Inbound port `3000/tcp` on `127.0.0.1` for the frontend (if accessed directly)
- PostgreSQL (`5432/tcp`) and Redis (`6379/tcp`) must NOT be exposed externally

### Disk

- Persistent volume for PostgreSQL: `/var/lib/docker/volumes/.../postgres_data` (minimum 10 GB recommended)
- Persistent volume for Redis: `/var/lib/docker/volumes/.../redis_data` (minimum 2 GB recommended)
- Backup storage: sufficient space for periodic PostgreSQL dumps

### Known Environmental Limitations

- **Windows host volume permissions:** On Windows, Docker volumes for PostgreSQL may fail with `chmod: /var/lib/postgresql/data: Operation not permitted`. This prevents the PostgreSQL container from starting when using bind mounts or named volumes. On Linux hosts this issue does not occur. If encountered on Windows, use Linux-based CI runners or WSL2 with proper volume configuration for clean-environment deployment and backup/restore testing.

---

## Pre-Deployment Checklist

1. Clone the repository and checkout the production tag:
   ```bash
   git clone https://github.com/m41245/ai-news-digest.git
   cd ai-news-digest
   git checkout v1.0.0
   ```

2. Create `.env.prod.local` (DO NOT commit this file):
   ```bash
   cp .env.example .env.prod.local
   ```

3. Set production values in `.env.prod.local` (see `docs/PRODUCTION_CONFIGURATION.md`).

4. Ensure `.env` and `.env.prod.local` are ignored by Git:
   ```bash
   git check-ignore .env .env.prod.local
   ```

5. Pull the production images from GHCR:
   ```bash
   docker pull ghcr.io/m41245/ai-news-digest:v1.0.0
   docker pull ghcr.io/m41245/ai-news-digest-frontend:v1.0.0
   ```

---

## Deployment Procedure

### Automated Steps (CI/CD)

1. Push a tag matching `v*` to GitHub:
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

2. GitHub Actions `Deploy` workflow builds and pushes images to GHCR.

3. Images are available at:
   ```
   ghcr.io/m41245/ai-news-digest:v1.0.0
   ghcr.io/m41245/ai-news-digest-frontend:v1.0.0
   ```

### Manual Steps (Operator)

1. Export or load environment variables on the production host.

2. Start the stack:
   ```bash
   docker compose -f docker-compose.prod.yml --env-file .env.prod.local up -d
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

5. Configure reverse proxy (see `docs/REVERSE_PROXY.md`).

---

## Rolling Deployment (Zero Downtime)

Use this procedure to minimize downtime during deployments.

1. Pull the new image:
   ```bash
   docker pull ghcr.io/m41245/ai-news-digest:v1.1.0
   ```

2. Back up the database:
   ```bash
   bash scripts/backup_db.sh
   ```

3. Restart web service (frontend depends on it):
   ```bash
   DOCKER_IMAGE=ghcr.io/m41245/ai-news-digest:v1.1.0 docker compose -f docker-compose.prod.yml --env-file .env.prod.local up -d --force-recreate web
   ```

4. Wait for web health:
   ```bash
   until curl -f http://localhost:8000/health/ready; do sleep 2; done
   ```

5. Restart workers:
   ```bash
   DOCKER_IMAGE=ghcr.io/m41245/ai-news-digest:v1.1.0 docker compose -f docker-compose.prod.yml --env-file .env.prod.local up -d --force-recreate celery_worker celery_beat
   ```

6. Restart frontend:
   ```bash
   docker compose -f docker-compose.prod.yml --env-file .env.prod.local up -d --force-recreate frontend
   ```

7. Verify health and run smoke tests:
   ```bash
   curl -f http://localhost:8000/health/live
   curl -f http://localhost:8000/health/ready
   poetry run python tests/smoke_prod.py
   ```

8. Monitor error rates for 15 minutes post-deployment.

---

## Environment Variables

See `docs/PRODUCTION_CONFIGURATION.md` for the full list of required and optional variables.

Key variables:
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
- `REDIS_PASSWORD`
- `JWT_SECRET_KEY` (must be production-specific, min 32 chars)
- `CORS_ORIGINS` (restrict to production frontend origins)
- `ENVIRONMENT=production`
- `DEBUG=false`
- `VITE_API_BASE_URL` (frontend API base URL)

---

## Health Checks

| Endpoint | Auth | Expected |
|----------|------|----------|
| `GET /health/live` | Public | `200` with `{"status":"alive"}` |
| `GET /health/ready` | Public | `200` with `{"status":"ready","checks":{"database":"ok","cache":"ok"}}` |
| `GET /metrics/health` | Public | `200` with `{"status":"ok"}` |

### Container Health Status

```bash
# Check all container health
docker compose -f docker-compose.prod.yml ps

# Inspect specific container health
docker inspect --format='{{.State.Health.Status}}' ai_news_digest_web

# View health check logs
docker inspect --format='{{range .State.Health.Log}}{{.Output}}{{end}}' ai_news_digest_web
```

### Health Check Configuration

| Container | Check | Interval | Timeout | Retries |
|-----------|-------|----------|---------|---------|
| `postgres` | `pg_isready` | 10s | 5s | 5 |
| `redis` | `redis-cli ping` | 10s | 5s | 5 |
| `web` | `curl /health/live` | 30s | 10s | 3 |
| `celery_worker` | Process check | 30s | 5s | 3 |
| `celery_beat` | Process check | 30s | 5s | 3 |
| `frontend` | `wget /` | 30s | 5s | 3 |

---

## Logs

```bash
docker compose -f docker-compose.prod.yml logs -f web
docker compose -f docker-compose.prod.yml logs -f celery_worker
docker compose -f docker-compose.prod.yml logs -f celery_beat
docker compose -f docker-compose.prod.yml logs -f frontend
```

Production logs are structured JSON. Look for:
- `event: request_started` / `event: request_completed`
- `request_id` for request tracing
- `status_code` for HTTP status
- `level: info|warning|error` for severity

### Log Analysis

**Find all 5xx errors:**
```bash
docker compose -f docker-compose.prod.yml logs web | grep '"status_code": 5'
```

**Find database connection errors:**
```bash
docker compose -f docker-compose.prod.yml logs web | grep 'database_connection_error'
```

**Trace a specific request:**
```bash
docker compose -f docker-compose.prod.yml logs web | grep '"request_id": "<request-id>"'
```

For comprehensive log analysis documentation, see [`docs/MONITORING.md`](MONITORING.md).

---

## Monitoring

- Metrics endpoint: `GET /metrics` (requires admin authentication)
- Request counts, latencies, and error counts are exposed in Prometheus text format.

### Key Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `http_request_total` | Counter | Request counts by `method:path` route |
| `http_request_duration_avg_seconds` | Gauge | Average latency per route |
| `http_request_duration_count` | Counter | Sample count for latency average |
| `http_error_total` | Counter | Error counts (status >= 400) by route |
| `task_total` | Counter | Celery task executions by `task_name:status` |

### Alert Conditions

See [`docs/MONITORING.md`](MONITORING.md) for comprehensive alert conditions including:
- Application availability
- Readiness failures
- HTTP 5xx rate
- HTTP latency
- Database/Redis availability
- Celery worker health and task failures
- Resource usage (disk, memory, CPU)
- Container restart count

---

## Backup

```bash
bash scripts/backup_db.sh
```

Backups are plain SQL dumps with `--clean --if-exists`.

---

## Restore

```bash
bash scripts/restore_db.sh backup_20240101_000000.sql
```

The restore script:
1. Stops Celery workers
2. Drops and recreates the database
3. Restores from the SQL dump
4. Runs migrations
5. Restarts workers

**Always back up before restoring.**

---

## Rollback

To roll back the application image:

```bash
DOCKER_IMAGE=ghcr.io/m41245/ai-news-digest:v0.9.0 docker compose -f docker-compose.prod.yml --env-file .env.prod.local up -d --force-recreate
```

**Important:** The `JWT_SECRET_KEY` must remain consistent across rollouts. Changing it invalidates all active sessions.

Database migrations are forward-only. To roll back schema changes, restore from a backup taken before the migration.

### Rollback Procedure

1. Pull the previous image:
   ```bash
   docker pull ghcr.io/m41245/ai-news-digest:v1.0.0
   ```

2. If database migration was applied, restore from backup:
   ```bash
   bash scripts/restore_db.sh backup_pre_v1.1.0.sql
   ```

3. Deploy previous version:
   ```bash
   DOCKER_IMAGE=ghcr.io/m41245/ai-news-digest:v1.0.0 docker compose -f docker-compose.prod.yml --env-file .env.prod.local up -d --force-recreate
   ```

4. Verify health:
   ```bash
   curl -f http://localhost:8000/health/live
   curl -f http://localhost:8000/health/ready
   ```

---

## Restart Procedures

### Single Service Restart

```bash
docker compose -f docker-compose.prod.yml restart web
docker compose -f docker-compose.prod.yml restart celery_worker
docker compose -f docker-compose.prod.yml restart celery_beat
docker compose -f docker-compose.prod.yml restart frontend
```

### Full Stack Restart

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod.local down
docker compose -f docker-compose.prod.yml --env-file .env.prod.local up -d
```

### Rolling Restart (Minimize Downtime)

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

## Operational Runbook

For comprehensive operational procedures, see [`docs/RUNBOOK.md`](RUNBOOK.md), which covers:
- Deployment procedure
- Rollback procedure
- Restart procedure
- Health diagnosis
- Database outage response
- Redis outage response
- Celery failure response
- Frontend failure response
- Backup restoration
- Secret rotation
- Certificate renewal
- Incident investigation
