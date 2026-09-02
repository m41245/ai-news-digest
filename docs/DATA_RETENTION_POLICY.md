# Data Retention Policy

## 1. Scope

This policy defines how long AI News Digest retains different categories of data and the procedures for data deletion.

## 2. Data Categories and Retention Periods

### 2.1 Account Data

| Data Type | Retention Period | Deletion Trigger |
|-----------|-----------------|------------------|
| Email address | Account lifetime | Account deletion by admin |
| Password hash | Account lifetime | Account deletion by admin |
| Account metadata (created_at, role) | Account lifetime | Account deletion by admin |

**CURRENT IMPLEMENTATION:** Account data is retained until an administrator deletes the user via `DELETE /api/v1/admin/users/{id}`. There is no self-service account deletion feature.

### 2.2 Article Data

| Data Type | Retention Period | Notes |
|-----------|-----------------|-------|
| Article content | 30 days (default) | Automatically purged by cleanup task `cleanup_old_articles` |
| Article summaries | 30 days (default) | Automatically purged by cleanup task `cleanup_old_articles` |
| Article metadata (URL, title, source) | 30 days (default) | Automatically purged by cleanup task `cleanup_old_articles` |

**CURRENT IMPLEMENTATION:** The cleanup task `cleanup_old_articles(days=30)` deletes articles older than the specified number of days. The default is 30 days (configurable via the `days` parameter). The cleanup is triggered manually via `POST /api/v1/admin/cleanup` - it is NOT on an automated schedule.

**INTENDED POLICY:** The policy target is 90 days for article content. To align with intended policy, either:
- Change the default `days` parameter to 90, or
- Add the cleanup task to the Celery Beat schedule with `days=90`

### 2.3 Digest Data

| Data Type | Retention Period | Notes |
|-----------|-----------------|-------|
| Digest content | 90 days (default) | Automatically purged by cleanup task `cleanup_old_digests` |
| Digest metadata | 90 days (default) | Automatically purged by cleanup task `cleanup_old_digests` |

**CURRENT IMPLEMENTATION:** The cleanup task `cleanup_old_digests(days=90)` deletes digests older than the specified number of days. The default is 90 days (configurable via the `days` parameter). The cleanup is triggered manually via `POST /api/v1/admin/cleanup`.

**INTENDED POLICY:** The policy target is 1 year for digest content. To align with intended policy, either:
- Change the default `days` parameter to 365, or
- Add the cleanup task to the Celery Beat schedule with `days=365`

### 2.4 Delivery Records

| Data Type | Retention Period | Notes |
|-----------|-----------------|-------|
| Delivery status records | Indefinite | NOT YET ENFORCED - no cleanup task exists |
| Email delivery logs | Indefinite | NOT YET ENFORCED - no cleanup task exists |

**NOT YET ENFORCED:** There is no `cleanup_old_deliveries` task implemented. Delivery records are retained indefinitely. To implement this policy, a new cleanup task must be created.

### 2.5 Operational Logs

| Data Type | Retention Period | Notes |
|-----------|-----------------|-------|
| Application logs | 30 days | Structured JSON logs - enforced by log rotation |
| Access logs | 90 days | HTTP request logs - enforced by log rotation |
| Error logs | 90 days | Application error logs - enforced by log rotation |

**NOTE:** Operational log retention is enforced at the infrastructure level (Docker/log rotation), not by the application.

### 2.6 Cache Data

| Data Type | Retention Period | Notes |
|-----------|-----------------|-------|
| Rate limit counters | 60 seconds | Sliding window |
| Brute force protection | 5 minutes | Lockout window |
| Session tokens | 60 minutes | JWT expiration |
| Readiness cache | 5 seconds | Health check cache |

**VERIFIED:** These retention periods are enforced by the Redis cache implementation.

## 3. Automated Cleanup

**CURRENT IMPLEMENTATION:**
The following Celery tasks exist for data cleanup:
- `cleanup_old_articles(days=30)`: Deletes articles older than specified days
- `cleanup_old_digests(days=90)`: Deletes digests older than specified days

**IMPORTANT:** These tasks are NOT on an automated schedule. They must be triggered manually via:
```
POST /api/v1/admin/cleanup
```

**INTENDED POLICY:** Cleanup tasks should be added to the Celery Beat schedule for automatic execution. Currently, they require manual triggering.

## 4. Manual Data Deletion

**CURRENT IMPLEMENTATION:**
Users cannot delete their own accounts. Only administrators can delete users via:
```
DELETE /api/v1/admin/users/{user_id}
```

**NOT YET ENFORCED:**
- Self-service account deletion
- Account settings page with deletion option
- Data deletion verification emails
- Grace period for accidental deletion

## 5. Legal Holds

In the event of a legal dispute or regulatory investigation, data retention may be extended beyond the standard periods. Such extensions require approval from the system owner and are documented in a separate legal hold register.

## 6. Data Deletion Verification

**NOT YET ENFORCED:**
The following features are described in the policy but not yet implemented:
1. Deletion event logging (without personal data)
2. Email confirmation of deletion
3. 7-day grace period for accidental deletion recovery

## 7. Compliance

This policy is designed to comply with:
- GDPR (General Data Protection Regulation) - Right to erasure
- CCPA (California Consumer Privacy Act) - Right to delete
- Other applicable data protection regulations

## 8. Policy Review

This policy is reviewed annually or when significant changes are made to the data processing infrastructure.

---

**Last updated:** August 2026
**Next review:** August 2027

**IMPLEMENTATION STATUS:**
- Account deletion: Admin-only (self-service NOT IMPLEMENTED)
- Article cleanup: Implemented (30 days default, manual trigger)
- Digest cleanup: Implemented (90 days default, manual trigger)
- Delivery cleanup: NOT IMPLEMENTED
- Automated schedule: NOT IMPLEMENTED (manual trigger only)
