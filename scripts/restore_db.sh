#!/usr/bin/env bash
set -euo pipefail

# PostgreSQL Restore Script for AI News Digest
# Usage: ./scripts/restore_db.sh [--yes] <backup_file>

YES=0
if [ "${1:-}" = "--yes" ]; then
    YES=1
    shift
fi

BACKUP_FILE="${1:-}"
CONTAINER_NAME="${CONTAINER_NAME:-ai_news_digest_db}"
DB_USER="${POSTGRES_USER:-postgres}"
DB_NAME="${POSTGRES_DB:-ai_news_digest}"

if [ -z "${BACKUP_FILE}" ]; then
    echo "Error: Backup file not specified."
    echo "Usage: $0 [--yes] <backup_file>"
    exit 1
fi

if [ ! -f "${BACKUP_FILE}" ]; then
    echo "Error: Backup file not found: ${BACKUP_FILE}"
    exit 1
fi

echo "WARNING: This will REPLACE the current database with the backup."
echo "Container: ${CONTAINER_NAME}"
echo "Database:  ${DB_NAME}"
echo "Backup:    ${BACKUP_FILE}"

if [ "${YES}" -ne 1 ]; then
    read -p "Are you sure? (yes/no): " CONFIRM
    if [ "${CONFIRM}" != "yes" ]; then
        echo "Restore cancelled."
        exit 0
    fi
fi

echo "Stopping Celery workers..."
docker compose stop celery_worker celery_beat || true

echo "Dropping and recreating database..."
docker exec "${CONTAINER_NAME}" psql -U "${DB_USER}" -c "DROP DATABASE IF EXISTS ${DB_NAME};"
docker exec "${CONTAINER_NAME}" psql -U "${DB_USER}" -c "CREATE DATABASE ${DB_NAME};"

echo "Restoring from backup..."
cat "${BACKUP_FILE}" | docker exec -i "${CONTAINER_NAME}" psql -U "${DB_USER}" -d "${DB_NAME}"

echo "Running migrations..."
poetry run alembic upgrade head || true

echo "Restarting services..."
docker compose start celery_worker celery_beat || true

echo "Restore complete."
