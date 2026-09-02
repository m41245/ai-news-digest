#!/usr/bin/env bash
set -euo pipefail

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

# Check 4: Contains data (at least INSERT statements)
INSERT_COUNT=$(grep -c "INSERT INTO" "${BACKUP_FILE}" || true)
if [ "${INSERT_COUNT}" -gt 0 ]; then
    echo "[PASS] Contains ${INSERT_COUNT} INSERT statements"
    PASS=$((PASS + 1))
else
    echo "[FAIL] No INSERT statements found (backup may be empty of data)"
    FAIL=$((FAIL + 1))
fi

# Check 5: File ends cleanly
if tail -n 1 "${BACKUP_FILE}" | grep -q "\\."; then
    echo "[PASS] File ends cleanly"
    PASS=$((PASS + 1))
else
    echo "[FAIL] File may be truncated"
    FAIL=$((FAIL + 1))
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
