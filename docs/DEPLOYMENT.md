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
- PostgreSQL (`5432/tcp`) and Redis (`6379/tcp`) must NOT be exposed externally

### Disk

- Persistent volume for PostgreSQL: `/var/lib/docker/volumes/.../postgres_data` (minimum 10 GB recommended)
- Persistent volume for Redis: `/var/lib/docker/volumes/.../redis_data` (minimum 2 GB recommended)
- Backup storage: sufficient space for periodic PostgreSQL dumps

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

5. Pull the production image from GHCR:
   ```bash
   docker pull ghcr.io/m41245/ai-news-digest:v1.0.0
   ```

---

## Deployment Procedure

### Automated Steps (CI/CD)

1. Push a tag matching `v*` to GitHub:
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

2. GitHub Actions `Deploy` workflow builds and pushes the image to GHCR.

3. Image is available at:
   ```
   ghcr.io/m41245/ai-news-digest:v1.0.0
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

## Environment Variables

See `docs/PRODUCTION_CONFIGURATION.md` for the full list of required and optional variables.

Key variables:
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
- `REDIS_PASSWORD`
- `JWT_SECRET_KEY` (must be production-specific, min 32 chars)
- `CORS_ORIGINS` (restrict to production frontend origins)
- `ENVIRONMENT=production`
- `DEBUG=false`

---

## Health Checks

| Endpoint | Auth | Expected |
|----------|------|----------|
| `GET /health/live` | Public | `200` with `{"status":"alive"}` |
| `GET /health/ready` | Public | `200` with `{"status":"ready","checks":{"database":"ok","cache":"ok"}}` |
| `GET /metrics/health` | Public | `200` with `{"status":"ok"}` |

---

## Logs

```bash
docker compose -f docker-compose.prod.yml logs -f web
docker compose -f docker-compose.prod.yml logs -f celery_worker
docker compose -f docker-compose.prod.yml logs -f celery_beat
```

Production logs are structured JSON. Look for:
- `event: request_started` / `event: request_completed`
- `request_id` for request tracing
- `status_code` for HTTP status
- `level: info|warning|error` for severity

---

## Monitoring

- Metrics endpoint: `GET /metrics` (requires admin authentication)
- Request counts, latencies, and error counts are exposed in Prometheus text format.

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
docker compose -f docker-compose.prod.yml --env-file .env.prod.local up -d --force-recreate
```

Use a previous image tag:
```bash
DOCKER_IMAGE=ghcr.io/m41245/ai-news-digest:v0.9.0 docker compose -f docker-compose.prod.yml --env-file .env.prod.local up -d --force-recreate
```

**Important:** The `JWT_SECRET_KEY` must remain consistent across rollouts. Changing it invalidates all active sessions.

Database migrations are forward-only. To roll back schema changes, restore from a backup taken before the migration.
