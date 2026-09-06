# Migration Deployment and Rollback Procedures

## Overview

This document describes the procedures for applying and rolling back Alembic database migrations in the AI News Digest application.

## Pre-Migration Checklist

1. **Backup the database** before any migration:
   ```bash
   docker compose -f docker-compose.prod.yml exec postgres pg_dump -U ${POSTGRES_USER} ${POSTGRES_DB} > backup_before_migration_$(date +%Y%m%d_%H%M%S).sql
   ```

2. **Review the migration**:
   ```bash
   alembic history --verbose
   alembic show <revision_id>
   ```

3. **Verify migration compatibility**:
   - Ensure the migration is reversible (has a proper `downgrade()` function)
   - Ensure the migration does not drop columns or tables that contain active data
   - Ensure the migration handles both empty and populated databases

## Applying Migrations

### Automated (CI/CD)

Migrations are applied automatically in the Docker entrypoint:

```bash
# In entrypoint.sh
python -m alembic upgrade head
```

### Manual

1. **Check current migration status**:
   ```bash
   poetry run alembic current
   ```

2. **Apply all pending migrations**:
   ```bash
   poetry run alembic upgrade head
   ```

3. **Apply a specific migration**:
   ```bash
   poetry run alembic upgrade <revision_id>
   ```

4. **Verify migration applied**:
   ```bash
   poetry run alembic current
   poetry run alembic history
   ```

## Rolling Back Migrations

### Single-Step Rollback

```bash
poetry run alembic downgrade -1
```

### Multi-Step Rollback

```bash
poetry run alembic downgroll <target_revision_id>
```

### Full Rollback (Not Recommended)

```bash
poetry run alembic downgrade base
```

**Warning:** Full rollback will drop all tables. Only use this on fresh databases or when you have a full backup.

## Emergency Rollback Procedure

If a migration causes production issues:

1. **Stop the application**:
   ```bash
   docker compose -f docker-compose.prod.yml stop web celery_worker celery_beat
   ```

2. **Rollback the database**:
   ```bash
   docker compose -f docker-compose.prod.yml exec postgres psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
   docker compose -f docker-compose.prod.yml exec postgres psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -f /backup/backup_before_migration.sql
   ```

   Or use Alembic:
   ```bash
   poetry run alembic downgrade -1
   ```

3. **Restore from backup if needed**:
   ```bash
   docker compose -f docker-compose.prod.yml exec postgres psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} < backup_file.sql
   ```

4. **Restart the application**:
   ```bash
   docker compose -f docker-compose.prod.yml up -d web celery_worker celery_beat
   ```

5. **Verify health**:
   ```bash
   curl -f http://localhost:8000/health/live
   curl -f http://localhost:8000/health/ready
   ```

## Migration Best Practices

1. **Always backup before migrating**
2. **Test migrations in staging first**
3. **Never modify committed migrations** — create new migrations instead
4. **Ensure `downgrade()` is implemented and tested**
5. **Use `batch_alter_table` for SQLite compatibility** when adding non-nullable columns
6. **Avoid destructive operations** (dropping columns, truncating tables) without explicit data archival
7. **Run migrations with `--sql` flag first** to review generated SQL:
   ```bash
   poetry run alembic upgrade head --sql
   ```

## Troubleshooting

### Migration fails with "column already exists"

This typically means a previous migration was partially applied. Fix by:
```bash
poetry run alembic stamp head
poetry run alembic upgrade head
```

### Migration fails with "relation does not exist"

The migration is trying to modify a table that doesn't exist. Ensure all prior migrations are applied:
```bash
poetry run alembic upgrade head
```

### Need to force a specific revision

```bash
poetry run alembic stamp <revision_id>
```

This marks the database as being at a specific revision without running the migration. Use only for recovery.
