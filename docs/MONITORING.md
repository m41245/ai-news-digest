# Production Monitoring

## Overview

This document describes the monitoring strategy for the AI News Digest production deployment, including alert conditions, metrics endpoints, log analysis, and container health checks.

The monitoring stack is designed to be lightweight and observable with standard tooling (Prometheus, Grafana, or any container-aware monitoring platform).

---

## Monitoring Targets

### Application Availability

**What to monitor:** The web service must respond to HTTP requests on port 8000.

**How to monitor:**
- Poll `GET /health/live` every 30 seconds
- Expect HTTP 200 with `{"status":"alive"}`

**Alert condition:**
- `application_down`: `/health/live` returns non-200 or is unreachable for > 60 seconds

---

### Readiness Failures

**What to monitor:** The application's ability to serve traffic (dependencies healthy).

**How to monitor:**
- Poll `GET /health/ready` every 30 seconds
- Expect HTTP 200 with `{"status":"ready","checks":{"database":"ok","cache":"ok"}}`

**Alert condition:**
- `readiness_failing`: `/health/ready` returns non-200 for > 90 seconds
- `database_unavailable`: `checks.database` != "ok" for > 60 seconds
- `cache_unavailable`: `checks.cache` != "ok" for > 60 seconds

---

### HTTP 5xx Rate

**What to monitor:** Server-side errors indicating application or dependency failures.

**How to monitor:**
- Scrape `GET /metrics` (admin auth required)
- Track `http_error_total` counter
- Calculate 5xx rate: `rate(http_error_total{status=~"5.."}[5m])`

**Alert condition:**
- `high_error_rate`: 5xx rate > 5% of total requests over 5 minutes
- `error_spike`: Absolute 5xx count > 10 in 5 minutes

---

### HTTP Latency

**What to monitor:** Response time for API requests.

**How to monitor:**
- Scrape `http_request_duration_avg_seconds` from `/metrics`
- Track per-route latency

**Alert condition:**
- `high_latency`: p95 latency > 2000ms over 5 minutes
- `latency_degradation`: Average latency > 1000ms over 10 minutes

---

### Database Availability

**What to monitor:** PostgreSQL container health and connectivity.

**How to monitor:**
- Docker healthcheck: `pg_isready -U ${POSTGRES_USER}` (runs every 10s)
- Application readiness probe includes database check
- Pool metrics via `get_pool_metrics()` (size, checkedin, checkedout, overflow)

**Alert condition:**
- `database_down`: PostgreSQL healthcheck fails for > 30 seconds
- `database_pool_exhausted`: `overflow` > 0 for > 2 minutes
- `database_slow_queries`: Query duration > 5s (requires pg_stat_statements)

---

### Redis Availability

**What to monitor:** Redis container health and connectivity.

**How to monitor:**
- Docker healthcheck: `redis-cli -a ${REDIS_PASSWORD} ping` (runs every 10s)
- Application readiness probe includes cache check

**Alert condition:**
- `redis_down`: Redis healthcheck fails for > 30 seconds
- `redis_memory_high`: Memory usage > 90% of container limit (256M)

---

### Celery Worker Health

**What to monitor:** Celery worker and beat process availability.

**How to monitor:**
- Docker healthcheck verifies celery process in `/proc/1/cmdline`
- Monitor worker logs for task processing activity
- Track task success/failure via `task_total` metric (in-process only)

**Alert condition:**
- `celery_worker_down`: Worker healthcheck fails for > 60 seconds
- `celery_beat_down`: Beat healthcheck fails for > 60 seconds
- `celery_task_backlog`: No tasks processed in 30 minutes during active hours (06:00-09:00 UTC)

---

### Celery Task Failures

**What to monitor:** Task execution success/failure rates.

**How to monitor:**
- Scrape `task_total{status="failure"}` from `/metrics`
- Monitor Celery worker logs for `TaskFailed` or retry events

**Alert condition:**
- `celery_task_failures`: Failure rate > 10% over 15 minutes
- `critical_task_failed`: Ingestion or digest task fails 3+ consecutive times

---

### Disk Usage

**What to monitor:** Persistent volume utilization for PostgreSQL and Redis.

**How to monitor:**
- Host-level disk monitoring (node_exporter or equivalent)
- PostgreSQL volume: `/var/lib/docker/volumes/.../postgres_data`
- Redis volume: `/var/lib/docker/volumes/.../redis_data`

**Alert condition:**
- `disk_usage_warning`: Disk usage > 80%
- `disk_usage_critical`: Disk usage > 90%

---

### Memory Usage

**What to monitor:** Container memory utilization.

**How to monitor:**
- Docker stats or cgroup memory metrics
- Container limits: web (512M), worker (512M), beat (256M), postgres (512M), redis (256M), frontend (128M)

**Alert condition:**
- `memory_usage_warning`: Container memory > 80% of limit for > 5 minutes
- `memory_usage_critical`: Container memory > 95% of limit for > 2 minutes

---

### CPU Usage

**What to monitor:** Container CPU utilization.

**How to monitor:**
- Docker stats or cgroup CPU metrics
- Track CPU throttling for limited containers

**Alert condition:**
- `cpu_usage_high`: Container CPU > 80% for > 10 minutes
- `cpu_throttling`: CPU throttling events increasing (indicates under-provisioned)

---

### Container Restart Count

**What to monitor:** Unexpected container restarts indicating crashes or health failures.

**How to monitor:**
- Docker event stream or `docker inspect` restart count
- Track restart events over time

**Alert condition:**
- `container_restart`: Any container restarts more than 3 times in 1 hour
- `container_crash_loop`: Container in restart loop (restarting every < 60 seconds)

---

## Metrics Endpoints

### `/metrics` (Admin Only)

Prometheus-text format metrics. Requires admin JWT authentication.

```
GET /metrics
Authorization: Bearer <admin_token>
```

**Available metrics:**

| Metric | Type | Description |
|--------|------|-------------|
| `http_request_total` | Counter | Request counts by `method:path` route |
| `http_request_duration_avg_seconds` | Gauge | Average latency per route |
| `http_request_duration_count` | Counter | Sample count for latency average |
| `http_error_total` | Counter | Error counts (status >= 400) by route |
| `task_total` | Counter | Celery task executions by `task_name:status` |
| `rss_ingestion_total` | Counter | RSS feed ingestion results by `source:status` |
| `email_delivery_total` | Counter | Email delivery results by `status` with `sent_count` |
| `ai_request_total` | Counter | AI provider requests by `provider:status` |
| `notification_evaluations` | Counter | Notification eligibility evaluations |
| `notifications_created` | Counter | Notifications created |
| `deliveries_attempted` | Counter | Delivery attempts |
| `deliveries_succeeded` | Counter | Successful deliveries |
| `deliveries_deferred` | Counter | Deferred deliveries |
| `deliveries_failed_permanently` | Counter | Permanently failed deliveries |
| `deliveries_recovered` | Counter | Recovered stuck deliveries |
| `digest_batches_created` | Counter | Digest batches created |
| `cleanup_operations` | Counter | Cleanup task executions |
| `auth_failures` | Counter | Authentication failures |
| `rate_limit_events` | Counter | Rate limit trigger events |

**Note:** `task_total` metrics are in-process only. When Celery workers run in separate containers, task metrics are not shared across processes. A shared backend (Redis or Prometheus Push Gateway) is required for distributed task metrics.

### `/metrics/health` (Public)

Health check for the metrics subsystem itself.

```
GET /metrics/health
```

Response: `{"status": "ok"}`

### `/health/live` (Public)

Liveness probe. Returns 200 if the application process is running.

```
GET /health/live
```

Response: `{"status": "alive"}`

### `/health/ready` (Public)

Readiness probe. Returns 200 only if all dependencies (database, cache) are healthy.

```
GET /health/ready
```

Response: `{"status": "ready", "checks": {"database": "ok", "cache": "ok"}}`

---

## Log Analysis

### Structured JSON Logs

Production logs are structured JSON with the following fields:

| Field | Description |
|-------|-------------|
| `timestamp` | ISO 8601 timestamp (UTC) |
| `level` | Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `event` | Event type identifier |
| `request_id` | Correlation ID from `X-Request-ID` header |
| `message` | Human-readable log message |
| `component` | Source component/module |

### Key Log Events

| Event | Level | Description |
|-------|-------|-------------|
| `request_started` | INFO | Incoming HTTP request received |
| `request_completed` | INFO | HTTP request completed (includes status_code, duration) |
| `database_connection_error` | ERROR | Failed to connect to PostgreSQL |
| `redis_connection_error` | ERROR | Failed to connect to Redis |
| `task_failed` | ERROR | Celery task execution failed |
| `migration_applied` | INFO | Database migration applied |
| `health_check_failed` | WARNING | Health check dependency failure |

### Log Queries

**Find all 5xx errors:**
```bash
docker compose -f docker-compose.prod.yml logs web | grep '"status_code": 5'
```

**Find database connection errors:**
```bash
docker compose -f docker-compose.prod.yml logs web | grep 'database_connection_error'
```

**Find slow requests (>2s):**
```bash
docker compose -f docker-compose.prod.yml logs web | grep 'request_completed' | grep -E '"duration":[2-9]\.'
```

**Trace a specific request:**
```bash
docker compose -f docker-compose.prod.yml logs web | grep '"request_id": "<request-id>"'
```

---

## Container Health Checks

### Health Check Configuration

All production containers have Docker healthchecks configured:

| Container | Check | Interval | Timeout | Retries |
|-----------|-------|----------|---------|---------|
| `postgres` | `pg_isready` | 10s | 5s | 5 |
| `redis` | `redis-cli ping` | 10s | 5s | 5 |
| `web` | `curl /health/live` | 30s | 10s | 3 |
| `celery_worker` | Process check | 30s | 5s | 3 |
| `celery_beat` | Process check | 30s | 5s | 3 |
| `frontend` | `wget /` | 30s | 5s | 3 |

### Health Check States

- **starting**: Container starting, healthcheck not yet passed
- **healthy**: Healthcheck passing
- **unhealthy**: Healthcheck failing (triggers restart with `unless-stopped` policy)

### Manual Health Verification

```bash
# Check all container health
docker compose -f docker-compose.prod.yml ps

# Inspect specific container health
docker inspect --format='{{.State.Health.Status}}' ai_news_digest_web

# View health check logs
docker inspect --format='{{range .State.Health.Log}}{{.Output}}{{end}}' ai_news_digest_web
```

---

## Alert Routing

### Severity Levels

| Severity | Channel | Response |
|----------|---------|----------|
| Critical (P1) | Page on-call immediately | Application down, data loss risk |
| Warning (P2) | Slack/email notification | Degraded performance, elevated errors |
| Info (P3) | Dashboard only | Non-urgent issues |

### Recommended Alert Rules

```yaml
groups:
  - name: ai-news-digest
    rules:
      - alert: ApplicationDown
        expr: up{job="ai-news-digest"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "AI News Digest is down"

      - alert: HighErrorRate
        expr: rate(http_error_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High 5xx error rate"

      - alert: HighLatency
        expr: http_request_duration_avg_seconds > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High API latency"

      - alert: DatabaseDown
        expr: ai_news_digest_database_up == 0
        for: 30s
        labels:
          severity: critical
        annotations:
          summary: "PostgreSQL is down"

      - alert: RedisDown
        expr: ai_news_digest_redis_up == 0
        for: 30s
        labels:
          severity: critical
        annotations:
          summary: "Redis is down"

      - alert: ContainerRestartLoop
        expr: increase(docker_container_restart_count[1h]) > 3
        labels:
          severity: warning
        annotations:
          summary: "Container restarting frequently"
```

---

## Avoiding Noisy Alerts

### Best Practices

1. **Use appropriate `for` durations**: Require sustained conditions before alerting (e.g., 1-5 minutes) to avoid transient spike alerts.

2. **Set meaningful thresholds**: Base thresholds on observed baseline performance, not arbitrary values.

3. **Group related alerts**: Use alert grouping to prevent alert storms during outages.

4. **Implement alert inhibition**: Suppress dependent alerts when a root cause is already firing (e.g., suppress high latency alerts when database is down).

5. **Use warning severity for recoverable issues**: Reserve critical severity for issues requiring immediate human intervention.

6. **Test alert rules**: Validate alert thresholds during load testing and failure drills.

### Maintenance Windows

Schedule maintenance windows for:
- Database backups (low-traffic period)
- Deployment rollouts
- Certificate renewals
- Infrastructure updates

During maintenance windows, silence non-critical alerts to prevent noise.

---

## Milestone 44 Monitoring Enhancements

M44 adds new metrics for notification and delivery observability:

### New Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `notification_evaluations` | Counter | Notification eligibility evaluations |
| `notifications_created` | Counter | Notifications created |
| `deliveries_attempted` | Counter | Delivery attempts |
| `deliveries_succeeded` | Counter | Successful deliveries |
| `deliveries_deferred` | Counter | Deferred deliveries |
| `deliveries_failed_permanently` | Counter | Permanently failed deliveries |
| `deliveries_recovered` | Counter | Recovered stuck deliveries |
| `digest_batches_created` | Counter | Digest batches created |
| `cleanup_operations` | Counter | Cleanup task executions |
| `auth_failures` | Counter | Authentication failures |
| `rate_limit_events` | Counter | Rate limit trigger events |

### Recommended Alert Rules

```yaml
groups:
  - name: ai-news-digest-notifications
    rules:
      - alert: HighDeliveryFailureRate
        expr: rate(deliveries_failed_permanently[15m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High email delivery failure rate"

      - alert: AuthFailureSpike
        expr: rate(auth_failures[5m]) > 10
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "Authentication failure spike detected"

      - alert: RateLimitSpike
        expr: rate(rate_limit_events[5m]) > 20
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "Rate limit events spike detected"
```

### Security Monitoring

Monitor security-related events:
- `auth_failures` — track authentication failures per client
- `rate_limit_events` — track rate limit triggers
- `login_brute_force_lockout` — log event for brute force protection
- Security headers presence on all responses
- CORS configuration validation
