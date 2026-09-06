# PostgreSQL Backup and Restore

## Overview

This document describes the procedures for backing up and restoring the PostgreSQL database for the AI News Digest application.

## Backup Methods

### 1. Logical Backup with `pg_dump`

**Recommended for:** Regular backups, migrations, and point-in-time recovery.

```bash
# Full backup
docker compose -f docker-compose.prod.yml exec postgres pg_dump -U ${POSTGRES_USER} ${POSTGRES_DB} > backup_$(date +%Y%m%d_%H%M%S).sql

# Compressed backup
docker compose -f docker-compose.prod.yml exec postgres pg_dump -U ${POSTGRES_USER} ${POSTGRES_DB} | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz

# Custom format (allows selective restore)
docker compose -f docker-compose.prod.yml exec postgres pg_dump -U ${POSTGRES_USER} -F c ${POSTGRES_DB} > backup_$(date +%Y%m%d_%H%M%S).dump

# With compression
docker compose -f docker-compose.prod.yml exec postgres pg_dump -U ${POSTGRES_USER} -F c -Z 9 ${POSTGRES_DB} > backup_$(date +%Y%m%d_%H%M%S).dump
```

### 2. Volume Backup

**Recommended for:** Quick snapshots of the entire PostgreSQL data directory.

```bash
# Stop PostgreSQL to ensure consistency
docker compose -f docker-compose.prod.yml stop postgres

# Backup volume
docker run --rm -v ai_news_digest_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_volume_backup_$(date +%Y%m%d_%H%M%S).tar.gz /data

# Restart PostgreSQL
docker compose -f docker-compose.prod.yml start postgres
```

### 3. Continuous Archiving (WAL)

For production deployments requiring point-in-time recovery, enable WAL archiving:

```sql
-- postgresql.conf settings
wal_level = replica
archive_mode = on
archive_command = 'cp %p /var/lib/postgresql/wal_archive/%f'
archive_timeout = 300
```

## Restore Procedures

### Restore from `pg_dump` SQL file

```bash
# Drop and recreate database
docker compose -f docker-compose.prod.yml exec postgres psql -U ${POSTGRES_USER} -c "DROP DATABASE IF EXISTS ${POSTGRES_DB};"
docker compose -f docker-compose.prod.yml exec postgres psql -U ${POSTGRES_USER} -c "CREATE DATABASE ${POSTGRES_DB};"

# Restore
docker compose -f docker-compose.prod.yml exec postgres psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} < backup_20260906_120000.sql

# Run migrations
poetry run alembic upgrade head
```

### Restore from custom format dump

```bash
# Restore specific tables
pg_restore -U ${POSTGRES_USER} -d ${POSTGRES_DB} -t articles -t categories backup.dump

# Full restore
pg_restore -U ${POSTGRES_USER} -d ${POSTGRES_DB} backup.dump
```

### Restore from volume backup

```bash
# Stop PostgreSQL
docker compose -f docker-compose.prod.yml stop postgres

# Remove current volume data
docker volume rm ai_news_digest_postgres_data

# Restore volume from backup
docker run --rm -v ai_news_digest_postgres_data:/data -v $(pwd):/backup alpine tar xzf /backup/postgres_volume_backup_20260906_120000.tar.gz -C /

# Start PostgreSQL
docker compose -f docker-compose.prod.yml start postgres
```

## Automated Backup Script

Create a cron job for automated backups:

```bash
#!/bin/bash
# /opt/ai-news-digest/backup.sh

BACKUP_DIR="/opt/ai-news-digest/backups"
RETENTION_DAYS=7
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p ${BACKUP_DIR}

docker compose -f /opt/ai-news-digest/docker-compose.prod.yml exec -T postgres pg_dump -U ${POSTGRES_USER} ${POSTGRES_DB} | gzip > ${BACKUP_DIR}/backup_${DATE}.sql.gz

# Retention policy
find ${BACKUP_DIR} -name "backup_*.sql.gz" -mtime +${RETENTION_DAYS} -delete

echo "Backup completed: backup_${DATE}.sql.gz"
```

Add to crontab:
```bash
0 2 * * * /opt/ai-news-digest/backup.sh >> /var/log/ai-news-digest/backup.log 2>&1
```

## Verification

After restore, verify the database:

```bash
# Check row counts
docker compose -f docker-compose.prod.yml exec postgres psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c "SELECT count(*) FROM articles;"
docker compose -f docker-compose.prod.yml exec postgres psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c "SELECT count(*) FROM users;"

# Check migrations
poetry run alembic current

# Run application health check
curl -f http://localhost:8000/health/ready
```

## Disaster Recovery

In case of complete data loss:

1. Restore from the most recent backup
2. Apply any migrations newer than the backup
3. Verify application health
4. Resume normal operations

## Backup Storage Recommendations

- Store backups on a separate physical volume or remote storage
- Encrypt backups containing sensitive data
- Test restore procedures quarterly
- Maintain at least 7 days of daily backups
- Maintain at least 4 weeks of weekly backups
- Maintain at least 12 months of monthly backups
