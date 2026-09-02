# Backup and Disaster Recovery

## Phase 14: Backup and Disaster Recovery

---

## 1. Backup Strategy

### Database Backups

The PostgreSQL database is backed up using `pg_dump` with the following options:

- `--clean` - Include DROP statements before each create statement
- `--if-exists` - Use IF EXISTS when dropping objects
- `--no-owner` - Skip ownership restoration
- `--no-privileges` - Skip privilege restoration

This produces portable SQL dumps that can be restored on any PostgreSQL instance.

### Backup Script

Location: `scripts/backup_db.sh`

Usage:
```bash
./scripts/backup_db.sh [output_file]
```

Default output: `backup_YYYYMMDD_HHMMSS.sql`

### Backup Schedule

Backups should be scheduled via cron or a containerized cron job:

```bash
# Daily at 2:00 AM
0 2 * * * /path/to/ai-news-digest/scripts/backup_db.sh
```

### Backup Retention

Retain backups according to the following schedule:

- Daily backups: 7 days
- Weekly backups: 4 weeks
- Monthly backups: 12 months

Implement retention using a simple cleanup script or filesystem TTL policies.

---

## 2. RPO (Recovery Point Objective)

**RPO: 24 hours**

In the event of a complete data loss, the maximum acceptable data loss is 24 hours of article, digest, and delivery data. This is bounded by the daily backup schedule.

For reduced RPO, consider:
- Increasing backup frequency to hourly
- Using PostgreSQL continuous archiving (WAL shipping)
- Implementing application-level event sourcing for critical data

---

## 3. RTO (Recovery Time Objective)

**RTO: 2 hours**

The maximum acceptable downtime for recovery includes:
- Restoring the database backup (~10-30 minutes depending on size)
- Running database migrations (~5 minutes)
- Restarting application services (~5 minutes)
- Verification testing (~30 minutes)

Total estimated recovery time: 1-2 hours.

---

## 4. Restore Procedure

### Prerequisites

- A valid backup SQL file
- Access to the PostgreSQL container
- Application credentials in `.env`

### Steps

1. **Stop application services**
   ```bash
   docker compose stop celery_worker celery_beat
   ```

2. **Create a fresh database**
   ```bash
   docker exec ai_news_digest_db psql -U postgres -c "DROP DATABASE IF EXISTS ai_news_digest;"
   docker exec ai_news_digest_db psql -U postgres -c "CREATE DATABASE ai_news_digest;"
   ```

3. **Restore from backup**
   ```bash
   cat backup_YYYYMMDD_HHMMSS.sql | docker exec -i ai_news_digest_db psql -U postgres -d ai_news_digest
   ```

4. **Run migrations**
    ```bash
    poetry run alembic upgrade head
    ```

5. **Restart services**
   ```bash
   docker compose start celery_worker celery_beat
   ```

6. **Verify**
   - Check application health endpoint: `curl http://localhost:8000/health/live`
   - Verify database connectivity
   - Spot-check recent articles/digests via API

### Automated Restore Script

Location: `scripts/restore_db.sh`

Usage:
```bash
./scripts/restore_db.sh backup_YYYYMMDD_HHMMSS.sql
```

---

## 5. Rollback Procedure

### Application Rollback

If a deployment introduces bugs or performance regressions:

1. **Identify the last known good Docker image tag**
    ```bash
    docker images | grep ai-news-digest
    ```

2. **Update docker-compose.prod.yml** to use the previous image tag:
    ```yaml
    services:
      web:
        image: ai-news-digest:<previous-tag>
    ```

3. **Redeploy**
    ```bash
    docker compose -f docker-compose.prod.yml up -d
    ```

4. **Verify**
    ```bash
    curl http://localhost:8000/health/live
    ```

### Database Schema Rollback

Database migrations are forward-only. To revert schema changes, restore from a backup taken before the migration:

1. Stop application services
2. Restore from pre-migration backup:
    ```bash
    bash scripts/restore_db.sh backup_pre_migration.sql
    ```
3. Redeploy the previous application version
4. Verify health

### Database Schema Rollback

If a migration causes issues:

1. **Check current migration version**
    ```bash
    docker compose exec web alembic current
    ```

2. **Restore from the most recent database backup** taken before the migration:
    ```bash
    bash scripts/restore_db.sh backup_pre_migration.sql
    ```

3. **Redeploy the previous application version** if needed.

**Note:** Database migrations are forward-only. `alembic downgrade` is not supported as a rollback mechanism in production. Always restore from a backup to revert schema changes.

---

## 6. Migration Rollback Strategy

### Alembic Migrations

All schema changes are managed through Alembic migrations stored in `migrations/`.

### Best Practices

- **Always generate reversible migrations** when possible:
  ```bash
  alembic revision --autogenerate -m "description"
  ```

- **Test migrations up before deploying to production:**
  ```bash
  alembic upgrade head
  ```

- **Never modify committed migrations** - generate a new migration to fix issues.

- **Backup before migration**:
  ```bash
  ./scripts/backup_db.sh pre_migration_backup.sql
  ```

### Emergency Rollback

If a migration breaks the application:

1. Stop application services
2. Restore from pre-migration backup
3. Redeploy the previous application version
4. Investigate and fix the migration offline
5. Test the fixed migration against a staging database

---

## 7. Disaster Recovery Scenarios

| Scenario | Recovery Steps | Estimated Time |
|----------|---------------|----------------|
| Single table corruption | Restore from backup, filter data if possible | 1-2 hours |
| Complete database loss | Full restore from backup | 1-2 hours |
| Application deployment failure | Rollback Docker image | 5-15 minutes |
| Migration failure | Alembic downgrade or full restore | 15 minutes - 2 hours |
| Host failure | Restore on new host from backup + image | 2-4 hours |

---

## 8. Backup Integrity Verification

Run the backup verification script after each backup:

```bash
./scripts/verify_backup.sh backup_YYYYMMDD_HHMMSS.sql
```

The script validates:
- File exists and is non-empty
- SQL dump contains expected table definitions
- SQL syntax is valid (basic check)

---

## 9. Testing Restore Procedure

Periodically test the restore procedure against a disposable database:

```bash
./scripts/test_restore.sh backup_YYYYMMDD_HHMMSS.sql
```

This script:
1. Spins up a temporary PostgreSQL container
2. Restores the backup
3. Runs migrations
4. Verifies data integrity
5. Tears down the temporary environment

**Recommended frequency:** Monthly or after every major schema change.
