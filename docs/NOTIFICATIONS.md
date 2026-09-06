# Notification System

## Overview

Milestone 41 delivers production-ready notification scheduling, email delivery, digest batching, rate limiting, retry logic, and cleanup for the AI News Digest platform. It builds on the Milestone 40 notification foundation, adding timezone-aware scheduling, provider-agnostic email delivery, bounded retry pipelines, and comprehensive observability.

## Architecture

### Domain Models

- **Notification** — Core notification entity with type, severity, title, body, story/article/company/topic/digest associations, metadata, deduplication key, and expiry.
- **NotificationDelivery** — Tracks delivery attempts per channel (in-app, email) with status, provider message ID, attempt count, and failure reason.
- **NotificationPreference** — Per-user preferences including channel toggles, quiet hours, timezone, importance/confidence thresholds, daily cap, and secure unsubscribe token.

### Enums

- **NotificationType** — `IMPORTANT_STORY`, `FOLLOWED_COMPANY_UPDATE`, `FOLLOWED_TOPIC_UPDATE`, `STORY_EVOLUTION`, `CONTRADICTION_DETECTED`, `CORRECTION_PUBLISHED`, `DIGEST_READY`, `SYSTEM`
- **NotificationSeverity** — `INFO`, `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`
- **DeliveryChannel** — `IN_APP`, `EMAIL`
- **DeliveryStatus** — `PENDING`, `SENT`, `DELIVERED`, `FAILED`, `BOUNCED`, `SUPPRESSED`, `SCHEDULED`, `PROCESSING`, `DEFERRED`, `RETRYABLE_FAILURE`, `PERMANENT_FAILURE`, `EXPIRED`, `CANCELLED`

### Eligibility Engine

`NotificationEligibilityEngine` evaluates whether a user should receive a notification. Checks are applied in order:

1. **Channel disabled** — If both in-app and email are disabled, suppress.
2. **Type-specific rules**:
   - `IMPORTANT_STORY`: importance score >= `min_importance` AND confidence >= `min_confidence`
   - `FOLLOWED_COMPANY_UPDATE` / `FOLLOWED_TOPIC_UPDATE`: followed-updates enabled, and entity not muted
   - `CONTRADICTION_DETECTED` / `CORRECTION_PUBLISHED`: corrections enabled
   - `STORY_EVOLUTION`: story evolution enabled
   - `DIGEST_READY`: daily or weekly digest enabled
3. **Quiet hours** — Evaluated using IANA timezone-aware `ZoneInfo`. Supports overnight ranges (e.g., 22:00–06:00).
4. **Daily cap** — Counts unread notifications since midnight UTC. If count >= `max_per_day`, suppress.
5. **Deduplication** — A deterministic key (`user_id:type:story_id:article_id:company_id:topic_id:digest_id`) prevents duplicate notifications.

### Notification Service

`NotificationService` manages the notification lifecycle:

- **Idempotent creation** — Checks `get_by_deduplication_key` before inserting. Returns the existing notification on duplicate.
- **Delivery fan-out** — Always creates an in-app delivery. Creates an email delivery only if `email_enabled` and `immediate_enabled` are both true.
- **Preference management** — `ensure_default_preferences` creates defaults with a secure unsubscribe token. `update_preferences` applies partial updates. `reset_preferences` deletes and recreates defaults.
- **State transitions** — `mark_read`, `mark_all_read`, `dismiss`, and `get_unread_count`.
- **Secure unsubscribe** — Uses `secrets.token_urlsafe(32)` tokens. The `/notifications/unsubscribe/{token}` endpoint disables email without requiring authentication.

### Scheduling Service

`NotificationSchedulingService` computes timezone-aware delivery windows:

- Accepts a user `NotificationPreference` and a delivery window (`daily` or `weekly`).
- Uses IANA `ZoneInfo` for timezone-aware datetime computation, with `UTC` fallback for invalid timezone names.
- Respects quiet hours: if the computed delivery time falls within `quiet_hours_start`–`quiet_hours_end`, it is deferred to the end of quiet hours.
- Returns a timezone-aware `datetime` suitable for `NotificationDelivery.scheduled_for`.

### Email Providers

The email layer is provider-agnostic via `create_email_sender`:

- **`ConsoleEmailSender`** — Logs rendered HTML and plain-text bodies to the console. Used when `email_development_mode=true` or no SMTP credentials are configured.
- **`TestEmailSender`** — In-memory sender used in tests. Records sent messages for assertions without network I/O.
- **`SMTPSender`** — Production SMTP provider using `aiosmtplib`. Configured via `email_from_address`, `email_from_name`, `email_reply_to`, and standard `EMAIL_HOST`/`EMAIL_PORT`/`EMAIL_HOST_USER`/`EMAIL_HOST_PASSWORD` settings.

All senders implement the `EmailSender` port (`send` returning `MessageResult`).

### Email Templates

- **Per-type templates** (`notification_templates.py`) — 8 functions rendering HTML and plain-text bodies for each `NotificationType`.
- **Digest templates** (`digest_templates.py`) — `render_daily_digest_email` and `render_weekly_digest_email` render batched digests.
- All user-facing strings are escaped with `html.escape` to prevent XSS.

### Rate Limiter

`NotificationRateLimiter` enforces per-user rate limits:

- Redis-backed sliding-window counter when `redis_url` is configured.
- In-memory fallback when Redis is unavailable.
- Configurable via `email_rate_limit` (max sends per window) and `email_rate_limit_window` (window seconds).
- Returns `RateLimitDecision` with `allowed`, `remaining`, `reset_at`, and `retry_after`.

### Delivery Service

`NotificationDeliveryService` processes notification deliveries:

- Claims `SCHEDULED` deliveries atomically to prevent duplicate processing.
- Updates status through the validated state machine (`SCHEDULED` → `PROCESSING` → `SENT` → `DELIVERED` / `RETRYABLE_FAILURE` / `PERMANENT_FAILURE` / `DEFERRED`).
- Records `provider_idempotency_key` to prevent duplicate sends.
- Processes bounded batches to avoid unbounded memory growth.

### Digest Batching

`DigestBatchingService` groups pending notifications into digest-ready batches:

- Filters by user preferences (`daily_digest_enabled`, `weekly_digest_enabled`).
- Groups notifications by user and digest window.
- Returns `DigestBatch` objects containing the user, notifications, and computed digest window.

### Retry and Recovery

- **`retry_failed_deliveries`** — Re-queues `RETRYABLE_FAILURE` deliveries whose `next_attempt_at` has passed, with exponential back-off up to `email_max_retries`.
- **`recover_stuck_deliveries`** — Resets `PROCESSING` deliveries stuck beyond `email_timeout` back to `SCHEDULED`.
- **`expire_old_notifications`** — Marks notifications past `expires_at` as expired.

### Cleanup

- **`cleanup_old_notification_deliveries`** — Hard-deletes `DELIVERED`, `FAILED`, and `CANCELLED` deliveries older than `notification_retention_days` (default 30) in bounded batches.
- **`cleanup_old_notifications`** — Hard-deletes notifications older than `notification_retention_days` (default 90) in bounded batches, cascading to deliveries.

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/notifications` | List current user's notifications (paginated) |
| GET | `/api/v1/notifications/unread/count` | Get unread notification count |
| GET | `/api/v1/notifications/{id}` | Get a single notification |
| POST | `/api/v1/notifications/{id}/read` | Mark notification as read |
| POST | `/api/v1/notifications/read-all` | Mark all notifications as read |
| POST | `/api/v1/notifications/{id}/dismiss` | Dismiss a notification |
| GET | `/api/v1/notifications/preferences` | Get notification preferences |
| PUT | `/api/v1/notifications/preferences` | Update notification preferences |
| POST | `/api/v1/notifications/preferences/reset` | Reset preferences to defaults |
| GET | `/api/v1/notifications/unsubscribe/{token}` | Unsubscribe from email notifications |
| GET | `/api/v1/notifications/deliveries` | List current user's notification deliveries |
| GET | `/api/v1/notifications/deliveries/{id}` | Get a single delivery record |
| GET | `/api/v1/notifications/stats` | Get notification and delivery statistics |
| GET | `/api/v1/notifications/schedule-preview` | Preview computed delivery time for a window |
| POST | `/api/v1/notifications/test-delivery` | Send a test notification to the current user |
| GET | `/api/v1/health/notifications` | Notification subsystem health check |

All endpoints except `/unsubscribe/{token}` and `/health/notifications` require authentication. Results are scoped to the authenticated user.

### Email Composer

`NotificationEmailComposer` builds HTML and plain-text notification emails:

- HTML template with embedded CSS, story link, notification center link, app name, and unsubscribe link.
- All user-facing strings are escaped with `html.escape` to prevent XSS.
- Plain-text fallback includes title, separator, body, optional story link, and unsubscribe info.

### Frontend Components

- **`NotificationBell`** — Dropdown bell icon in the header showing unread count and recent notifications. Supports mark-as-read and link to full notifications page.
- **`NotificationsPage`** — Full notification list with pagination, severity badges, mark-read, and dismiss actions.
- **`NotificationPreferencesPage`** — Form for configuring delivery channels, digest notifications, content preferences, thresholds, and daily caps.

### Celery Tasks

- **`evaluate_notifications(story_id)`** — Evaluates notification eligibility for all active users for a given story. Creates notifications for eligible users. Retries up to 3 times with 60s delay. Records metrics (success, failure, duration).
- **`expire_old_notifications()`** — Expires notifications past their `expires_at` timestamp. Retries up to 3 times with 60s delay.
- **`schedule_notifications()`** — Creates `SCHEDULED` delivery records for notifications with `scheduled_for` in the future, respecting user preferences and quiet hours.
- **`process_scheduled_deliveries()`** — Claims and processes `SCHEDULED` deliveries, sending via the configured email provider and updating status through the state machine.
- **`process_immediate_deliveries()`** — Processes `PENDING` deliveries that are due for immediate sending.
- **`retry_failed_deliveries()`** — Re-queues `RETRYABLE_FAILURE` deliveries whose `next_attempt_at` has passed, with exponential back-off.
- **`recover_stuck_deliveries()`** — Resets `PROCESSING` deliveries stuck beyond the configured timeout back to `SCHEDULED`.
- **`cleanup_old_notification_deliveries(days=30)`** — Hard-deletes old delivery records in bounded batches.
- **`cleanup_old_notifications(days=90)`** — Hard-deletes old notifications and cascading deliveries in bounded batches.

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/notifications` | List current user's notifications (paginated) |
| GET | `/api/v1/notifications/unread/count` | Get unread notification count |
| GET | `/api/v1/notifications/{id}` | Get a single notification |
| POST | `/api/v1/notifications/{id}/read` | Mark notification as read |
| POST | `/api/v1/notifications/read-all` | Mark all notifications as read |
| POST | `/api/v1/notifications/{id}/dismiss` | Dismiss a notification |
| GET | `/api/v1/notifications/preferences` | Get notification preferences |
| PUT | `/api/v1/notifications/preferences` | Update notification preferences |
| POST | `/api/v1/notifications/preferences/reset` | Reset preferences to defaults |
| GET | `/api/v1/notifications/unsubscribe/{token}` | Unsubscribe from email notifications |

All endpoints except `/unsubscribe/{token}` require authentication. Results are scoped to the authenticated user.

### Database Schema (Migration 016 + 017)

**`notifications`**
- `id` (UUID PK), `user_id` (UUID FK → users), `notification_type`, `title`, `body`, `severity`
- `story_id`, `article_id`, `company_id`, `topic_id`, `digest_id` (optional FKs)
- `extra_data` (JSONB), `deduplication_key` (unique), `created_at`, `read_at`, `dismissed_at`, `expires_at`
- `scheduled_for` (timezone-aware datetime, added in migration 017)

**`notification_deliveries`**
- `id` (UUID PK), `notification_id` (UUID FK → notifications), `channel`, `status`
- `provider_message_id`, `attempt_count`, `last_attempt_at`, `delivered_at`, `failure_reason`, `created_at`, `updated_at`
- `scheduled_for` (timezone-aware datetime, added in migration 017)
- `claimed_at` (timezone-aware datetime, added in migration 017)
- `processing_started_at` (timezone-aware datetime, added in migration 017)
- `next_attempt_at` (timezone-aware datetime, added in migration 017)
- `provider_idempotency_key` (string 255, added in migration 017)
- `delivery_window` (string 50, added in migration 017)
- `suppression_reason` (string 100, added in migration 017)

Composite indexes (migration 017):
- `ix_notification_deliveries_status_next_attempt_at` (`status`, `next_attempt_at`)
- `ix_notification_deliveries_status_scheduled_for` (`status`, `scheduled_for`)
- `ix_notifications_scheduled_for` (`scheduled_for`)

**`notification_preferences`**
- `user_id` (UUID PK FK → users), `in_app_enabled`, `email_enabled`, `immediate_enabled`
- `daily_digest_enabled`, `weekly_digest_enabled`, `min_importance`, `min_confidence`
- `notify_followed_companies`, `notify_followed_topics`, `notify_corrections`, `notify_story_evolution`
- `quiet_hours_start`, `quiet_hours_end`, `timezone`, `max_per_day`, `unsubscribe_token` (unique)
- `created_at`, `updated_at`

### Frontend Components

- **`NotificationBell`** — Dropdown bell icon in the header showing unread count and recent notifications. Supports mark-as-read and link to full notifications page.
- **`NotificationsPage`** — Full notification list with pagination, severity badges, mark-read, and dismiss actions.
- **`NotificationPreferencesPage`** — Form for configuring delivery channels, digest notifications, content preferences, thresholds, and daily caps.

### Security and Privacy

- All notification API endpoints are authenticated and user-scoped.
- Unsubscribe tokens are cryptographically random (`secrets.token_urlsafe(32)`) and do not expose user IDs.
- Email content is HTML-escaped to prevent injection.
- Deduplication keys are deterministic per user+event, preventing notification spam on retries.
- Cross-user access is prevented at the service layer (`get_notification` returns `None` if `notification.user_id != user_id`).

### Idempotency and Retry Strategy

- **Deduplication** — Before creating a notification, the service queries by `(user_id, deduplication_key)`. On retry, the existing notification is returned.
- **Celery retries** — Both notification tasks declare `max_retries=3` and `default_retry_delay=60`. Retries are safe because notification creation is idempotent.
- **Transaction safety** — Notification and delivery records are committed immediately via `_add_and_refresh`. The worker container uses `async with SessionLocal()` ensuring commit/rollback semantics.

### Testing

| Suite | Tests | Coverage |
|-------|-------|----------|
| Eligibility engine | 13 | All notification types, thresholds, quiet hours, daily caps, deduplication |
| Notification service | 15 | CRUD, preferences, unsubscribe, cross-user access |
| API routes | 15 | Auth, scoping, preferences, unsubscribe, 404 handling |
| Email composer | 5 | HTML structure, escaping, optional links |
| Celery tasks | 6 | Eligibility evaluation, inactive users, missing stories, expiry |
| Scheduling service | 6 | Timezone-aware windows, quiet hours, daily/weekly scheduling |
| Rate limiter | 5 | Redis/in-memory backends, window enforcement, retry-after |
| Delivery service | 8 | Batch processing, claiming, state transitions, idempotency |
| Digest batching | 6 | User preference filtering, grouping, window computation |
| Email providers | 10 | Console, test, SMTP senders, factory selection |
| Worker tasks | 6 | Scheduling, processing, retry, recovery, cleanup |
| Domain models | 90 | State machine transitions, field validation, edge cases |
| **Total notification tests** | **184** | — |

## Configuration

Notification features require:

- Database migration 017 applied (`notifications.scheduled_for`, `notification_deliveries` scheduling columns).
- Existing SMTP configuration (for email delivery) or `EMAIL_DEVELOPMENT_MODE=true` for console logging.
- Existing Celery broker configuration (for background evaluation, scheduling, delivery, retry, and cleanup).

### Email Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `EMAIL_ENABLED` | Enable email notifications | `true` |
| `EMAIL_PROVIDER` | Provider: `smtp`, `console`, `test` | `smtp` |
| `EMAIL_FROM_ADDRESS` | Sender address | `noreply@example.com` |
| `EMAIL_FROM_NAME` | Sender display name | `AI News Digest` |
| `EMAIL_REPLY_TO` | Reply-to address | — |
| `EMAIL_BASE_URL` | Base URL for email links | `http://localhost:8000` |
| `EMAIL_MAX_RETRIES` | Max retry attempts for failed deliveries | `3` |
| `EMAIL_RETRY_DELAY` | Base retry delay in seconds | `60` |
| `EMAIL_BATCH_SIZE` | Max deliveries per processing batch | `100` |
| `EMAIL_RATE_LIMIT` | Max sends per rate-limit window | `100` |
| `EMAIL_RATE_LIMIT_WINDOW` | Rate-limit window in seconds | `60` |
| `EMAIL_TIMEOUT` | Processing timeout in seconds | `300` |
| `EMAIL_DEVELOPMENT_MODE` | Use console sender instead of SMTP | `false` |
| `NOTIFICATION_RETENTION_DAYS` | Days to retain delivery records | `30` |
| `NOTIFICATION_RETENTION_DAYS_NOTIFICATIONS` | Days to retain notifications | `90` |

### Retention

- Delivery records older than `NOTIFICATION_RETENTION_DAYS` are deleted by `cleanup_old_notification_deliveries`.
- Notifications older than `NOTIFICATION_RETENTION_DAYS_NOTIFICATIONS` are deleted by `cleanup_old_notifications`, cascading to deliveries.

### Rate Limiting

- Rate limiting uses Redis when `REDIS_URL` is configured.
- Falls back to in-memory counters when Redis is unavailable.
- Limits are per-user per-window to prevent a single user from exhausting delivery capacity.
