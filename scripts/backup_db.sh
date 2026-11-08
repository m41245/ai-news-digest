#!/usr/bin/env bash
set -euo pipefail
set -o pipefail 2>/dev/null || true

# PostgreSQL Backup Script for AI News Digest
# Usage: ./scripts/backup_db.sh [output_file]

OUTPUT_FILE="${1:-backup_$(date +%Y%m%d_%H%M%S).sql}"
CONTAINER_NAME="${CONTAINER_NAME:-ai_news_digest_db}"
DB_USER="${POSTGRES_USER:-postgres}"
DB_NAME="${POSTGRES_DB:-ai_news_digest}"

# Safety guard: never target production databases unless explicitly allowed.
case "${DB_NAME}" in
    *production*|*prod*|*prod_*)
        if [ "${ALLOW_PRODUCTION_TARGET:-0}" != "1" ]; then
            echo "ERROR: Refusing to target a production-looking database (${DB_NAME})." >&2
            echo "Set ALLOW_PRODUCTION_TARGET=1 to override (not recommended)." >&2
            exit 1
        fi
        ;;
esac

echo "Creating PostgreSQL backup..."
echo "Container: ${CONTAINER_NAME}"
echo "Database:  ${DB_NAME}"
echo "Output:    ${OUTPUT_FILE}"

TEMP_FILE="${OUTPUT_FILE}.tmp.$$"
trap 'rm -f "${TEMP_FILE}"' EXIT

if ! docker exec "${CONTAINER_NAME}" pg_dump \
    -U "${DB_USER}" \
    -d "${DB_NAME}" \
    --clean \
    --if-exists \
    --no-owner \
    --no-privileges \
    > "${TEMP_FILE}"; then
    echo "ERROR: pg_dump failed. Backup not created." >&2
    exit 1
fi

if [ ! -s "${TEMP_FILE}" ]; then
    echo "ERROR: Backup file is empty. pg_dump may have succeeded but produced no data." >&2
    exit 1
fi

mv "${TEMP_FILE}" "${OUTPUT_FILE}"
trap - EXIT

echo "Backup complete: ${OUTPUT_FILE}"
echo "Size: $(du -h "${OUTPUT_FILE}" | cut -f1)"

# Write a SHA-256 sidecar for integrity verification.
if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "${OUTPUT_FILE}" | awk '{print $1}' > "${OUTPUT_FILE}.sha256"
    echo "SHA-256: $(cat "${OUTPUT_FILE}.sha256")"
elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "${OUTPUT_FILE}" | awk '{print $1}' > "${OUTPUT_FILE}.sha256"
    echo "SHA-256: $(cat "${OUTPUT_FILE}.sha256")"
fi

if [ -f "${OUTPUT_FILE}" ] && [ -s "${OUTPUT_FILE}" ]; then
    echo "Backup verification: file exists and is non-empty."
else
    echo "ERROR: Backup verification failed." >&2
    exit 1
fi
