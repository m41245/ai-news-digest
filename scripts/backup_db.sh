#!/usr/bin/env bash
set -eu
set -o pipefail 2>/dev/null || true

# PostgreSQL Backup Script for AI News Digest
# Usage: ./scripts/backup_db.sh [output_file]

OUTPUT_FILE="${1:-backup_$(date +%Y%m%d_%H%M%S).sql}"
CONTAINER_NAME="${CONTAINER_NAME:-ai_news_digest_db}"
DB_USER="${POSTGRES_USER:-postgres}"
DB_NAME="${POSTGRES_DB:-ai_news_digest}"

echo "Creating PostgreSQL backup..."
echo "Container: ${CONTAINER_NAME}"
echo "Database:  ${DB_NAME}"
echo "Output:    ${OUTPUT_FILE}"

docker exec "${CONTAINER_NAME}" pg_dump \
    -U "${DB_USER}" \
    -d "${DB_NAME}" \
    --clean \
    --if-exists \
    --no-owner \
    --no-privileges \
    > "${OUTPUT_FILE}"

echo "Backup complete: ${OUTPUT_FILE}"
echo "Size: $(du -h "${OUTPUT_FILE}" | cut -f1)"
