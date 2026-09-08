#!/usr/bin/env bash
set -eu
set -o pipefail 2>/dev/null || true

# Backup Integrity Verification Script
# Usage: ./scripts/verify_backup.sh <backup_file>

BACKUP_FILE="${1:-}"

if [ -z "${BACKUP_FILE}" ]; then
    echo "Error: Backup file not specified."
    echo "Usage: $0 <backup_file>"
    exit 1
fi

if [ ! -f "${BACKUP_FILE}" ]; then
    echo "Error: Backup file not found: ${BACKUP_FILE}"
    exit 1
fi

echo "Verifying backup: ${BACKUP_FILE}"
echo ""

# Convert UTF-16 encoded backups (Windows pg_dump) to UTF-8 for processing
TEMP_FILE=""
if command -v iconv >/dev/null 2>&1; then
    if grep -q $'\xFE\xFF' "${BACKUP_FILE}" 2>/dev/null || grep -q $'\xFF\xFE' "${BACKUP_FILE}" 2>/dev/null; then
        TEMP_FILE="$(mktemp)"
        iconv -f UTF-16 -t UTF-8 "${BACKUP_FILE}" > "${TEMP_FILE}" 2>/dev/null || iconv -f UTF-16LE -t UTF-8 "${BACKUP_FILE}" > "${TEMP_FILE}" 2>/dev/null
        BACKUP_FILE="${TEMP_FILE}"
    fi
fi

PASS=0
FAIL=0

# Check 1: File is non-empty
if [ -s "${BACKUP_FILE}" ]; then
    echo "[PASS] File is non-empty"
    PASS=$((PASS + 1))
else
    echo "[FAIL] File is empty"
    FAIL=$((FAIL + 1))
fi

# Check 2: Contains PostgreSQL dump header
if grep -q "PostgreSQL database dump" "${BACKUP_FILE}"; then
    echo "[PASS] Valid PostgreSQL dump header found"
    PASS=$((PASS + 1))
else
    echo "[FAIL] Missing PostgreSQL dump header"
    FAIL=$((FAIL + 1))
fi

# Check 3: Contains expected table definitions
TABLES=("articles" "sources" "categories" "digests" "digest_articles" "users" "deliveries")
for table in "${TABLES[@]}"; do
    if grep -qi "create table.*${table}" "${BACKUP_FILE}"; then
        echo "[PASS] Table '${table}' definition found"
        PASS=$((PASS + 1))
    else
        echo "[FAIL] Table '${table}' definition missing"
        FAIL=$((FAIL + 1))
    fi
done

# Check 4: Contains data (INSERT or COPY statements)
INSERT_COUNT=$(grep -c "INSERT INTO" "${BACKUP_FILE}" || true)
COPY_COUNT=$(grep -c "COPY public\." "${BACKUP_FILE}" 2>/dev/null || true)
if [ "${INSERT_COUNT}" -gt 0 ] || [ "${COPY_COUNT}" -gt 0 ]; then
    echo "[PASS] Contains ${INSERT_COUNT} INSERT statements, ${COPY_COUNT} COPY data blocks"
    PASS=$((PASS + 1))
else
    echo "[FAIL] No INSERT or COPY data found (backup may be empty of data)"
    FAIL=$((FAIL + 1))
fi

# Check 5: File ends cleanly
if tail -n 5 "${BACKUP_FILE}" | grep -q "PostgreSQL database dump complete"; then
    echo "[PASS] File ends cleanly"
    PASS=$((PASS + 1))
else
    echo "[FAIL] File may be truncated"
    FAIL=$((FAIL + 1))
fi

if [ -n "${TEMP_FILE}" ] && [ -f "${TEMP_FILE}" ]; then
    rm -f "${TEMP_FILE}"
fi

echo ""
echo "================================"
echo "Results: ${PASS} passed, ${FAIL} failed"
echo "================================"

if [ "${FAIL}" -gt 0 ]; then
    echo "Backup verification FAILED."
    exit 1
else
    echo "Backup verification PASSED."
    exit 0
fi
