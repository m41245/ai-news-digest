# Notification Operations Runbook

This runbook covers day-to-day operations for the notification subsystem introduced in Milestone 41.

## Monitoring

### Health Check

```bash
curl -s http://localhost:8000/api/v1/health/notifications | jq
```

Expected response:
```json
{
  "status": "healthy",
  "scheduled": 0,
  "processing": 0,
  "pending": 0,
  "retryable_failure": 0
}
```

### Key Metrics

| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| `notification.deliveries.scheduled` | Deliveries waiting to be processed | > 1000 |
| `notification.deliveries.processing` | Deliveries currently being sent | > 100 |
| `notification.deliveries.retryable_failure` | Deliveries retrying after failure | > 500 |
| `notification.deliveries.permanent_failure` | Deliveries that will not be retried | > 50 |
| `notification.deliveries.sent_per_minute` | Successful sends per minute | < 1 for > 5 min |
| `notification.tasks.failed` | Celery task failures | Any |

### Celery Task Health

```bash
# Check active scheduled tasks
celery -A ai_news_digest.workers.celery_app inspect scheduled

# Check active reservations
celery -A ai_news_digest.workers.celery_app inspect reserved

# Check worker stats
celery -A ai_news_digest.workers.celery_app inspect stats
```

## Common Operations

### Trigger Manual Scheduling

```bash
celery -A ai_news_digest.workers.celery_app call ai_news_digest.workers.tasks.notifications.schedule_notifications
```

### Trigger Immediate Delivery Processing

```bash
celery -A ai_news_digest.workers.celery_app call ai_news_digest.workers.tasks.notifications.process_immediate_deliveries
```

### Trigger Scheduled Delivery Processing

```bash
celery -A ai_news_digest.workers.celery_app call ai_news_digest.workers.tasks.notifications.process_scheduled_deliveries
```

### Retry Failed Deliverures

```bash
celery -A ai_news_digest.workers.celery_app call ai_news_digest.workers.tasks.notifications.retry_failed_deliveries
```

### Recover Stuck Deliverures

```bash
celery -A ai_news_digest.workers.celery_app call ai_news_digest.workers.tasks.notifications.recover_stuck_deliveries
```

### Run Cleanup Manually

```bash
# Clean up deliveries older than 30 days
celery -A ai_news_digest.workers.celery_app call ai_news_digest.workers.tasks.notifications.cleanup_old_notification_deliveries --args '[30]'

# Clean up notifications older than 90 days
celery -A ai_news_digest.workers.celery_app call ai_news_digest.workers.tasks.notifications.cleanup_old_notifications --args '[90]'
```

## Troubleshooting

### High `PROCESSING` Count

Deliveries stuck in `PROCESSING` state may indicate worker crashes or network timeouts.

1. Check worker logs for errors.
2. Run `recover_stuck_deliveries` to reset deliveries past `email_timeout`.
3. Verify SMTP connectivity if using SMTP provider.
4. Check Redis connectivity for rate limiting.

### High `RETRYABLE_FAILURE` Count

Deliveries retrying after transient failures.

1. Check provider-specific errors in `failure_reason`.
2. Verify SMTP credentials and connectivity.
3. Check rate limiting (`email_rate_limit`) — too-low limits may cause throttling.
4. Review `next_attempt_at` to ensure retries are scheduled correctly.

### High `PERMANENT_FAILURE` Count

Deliveries that exhausted retries or encountered non-retryable errors.

1. Review `failure_reason` for patterns (invalid addresses, provider blocks).
2. Check `notification_preferences.email_enabled` for affected users.
3. Consider adjusting `email_max_retries` if failures are transient.

### Duplicate Sends

If users receive duplicate emails:

1. Verify `provider_idempotency_key` is populated on deliveries.
2. Check for multiple Celery worker instances processing the same queue without proper claiming.
3. Ensure `process_scheduled_deliveries` and `process_immediate_deliveries` are not scheduled redundantly.

### Quiet Hours Not Respected

If notifications arrive during quiet hours:

1. Verify `NotificationPreference.timezone` is a valid IANA timezone name.
2. Check `NotificationSchedulingService._compute_scheduled_time` logs for timezone parsing errors.
3. Ensure `quiet_hours_start` and `quiet_hours_end` are set correctly in preferences.

## Rate Limiting

Rate limiting is per-user per-window. To adjust:

1. Update `EMAIL_RATE_LIMIT` and `EMAIL_RATE_LIMIT_WINDOW` in environment/config.
2. Restart workers to pick up new settings.
3. If using Redis, verify `REDIS_URL` is configured and Redis is healthy.

If Redis is unavailable, the rate limiter falls back to in-memory counters. This is safe for single-worker deployments but not for multi-worker — each worker will have its own counter, potentially exceeding the intended limit.

## Email Provider Debugging

### Console Mode

Set `EMAIL_DEVELOPMENT_MODE=true` to log all email content to the console instead of sending. Useful for development and debugging template rendering.

### Test Mode

Use `TestEmailSender` in tests to inspect sent messages without network I/O.

### SMTP Debugging

Enable SMTP debug logging:

```bash
export EMAIL_SMTP_DEBUG=true
```

This logs the full SMTP conversation for troubleshooting delivery issues.

## Database Maintenance

### Manual Cleanup

If automated cleanup is insufficient:

```sql
-- Check delivery counts by age
SELECT date_trunc('day', created_at) AS day, count(*) 
FROM notification_deliveries 
GROUP BY 1 ORDER BY 1 DESC LIMIT 30;

-- Check notification counts by age
SELECT date_trunc('day', created_at) AS day, count(*) 
FROM notifications 
GROUP BY 1 ORDER BY 1 DESC LIMIT 30;
```

### Index Maintenance

Migration 017 creates composite indexes on:
- `notification_deliveries(status, next_attempt_at)`
- `notification_deliveries(status, scheduled_for)`
- `notifications(scheduled_for)`

Monitor index usage with `pg_stat_user_indexes` if performance degrades.
