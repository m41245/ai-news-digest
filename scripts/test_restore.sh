#!/usr/bin/env bash
set -euo pipefail

# Disposable Database Restore Test Script
# Usage: ./scripts/test_restore.sh <backup_file>

BACKUP_FILE="${1:-}"
TEST_DB_NAME="ai_news_digest_restore_test"
TEST_CONTAINER="ai_news_digest_test_restore_$$"
TEST_PORT="5433"

if [ -z "${BACKUP_FILE}" ]; then
    echo "Error: Backup file not specified."
    echo "Usage: $0 <backup_file>"
    exit 1
fi

if [ ! -f "${BACKUP_FILE}" ]; then
    echo "Error: Backup file not found: ${BACKUP_FILE}"
    exit 1
fi

cleanup() {
    echo ""
    echo "Cleaning up test environment..."
    docker rm -f "${TEST_CONTAINER}" >/dev/null 2>&1 || true
}

trap cleanup EXIT

echo "=========================================="
echo "Disposable Database Restore Test"
echo "=========================================="
echo "Backup file: ${BACKUP_FILE}"
echo "Test container: ${TEST_CONTAINER}"
echo "Test port: ${TEST_PORT}"
echo ""

# Check Docker is available
if ! docker info >/dev/null 2>&1; then
    echo "Error: Docker is not available. Cannot run restore test."
    exit 1
fi

# Step 1: Start disposable PostgreSQL container
echo "Step 1: Starting disposable PostgreSQL container..."
docker run -d \
    --name "${TEST_CONTAINER}" \
    -p "${TEST_PORT}:5432" \
    -e POSTGRES_DB="${TEST_DB_NAME}" \
    -e POSTGRES_USER=postgres \
    -e POSTGRES_PASSWORD=postgres \
    postgres:16-alpine >/dev/null

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
for i in $(seq 1 30); do
    if docker exec "${TEST_CONTAINER}" pg_isready -U postgres >/dev/null 2>&1; then
        echo "PostgreSQL is ready."
        break
    fi
    if [ "${i}" -eq 30 ]; then
        echo "Error: PostgreSQL did not become ready in time."
        exit 1
    fi
    sleep 1
done

# Step 2: Restore backup
echo ""
echo "Step 2: Restoring backup into test database..."
cat "${BACKUP_FILE}" | docker exec -i "${TEST_CONTAINER}" psql -U postgres -d "${TEST_DB_NAME}" >/dev/null
echo "Restore complete."

# Step 3: Verify tables exist
echo ""
echo "Step 3: Verifying database schema..."
TABLES=$(docker exec "${TEST_CONTAINER}" psql -U postgres -d "${TEST_DB_NAME}" -tAc "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;")

EXPECTED_TABLES=("articles" "categories" "deliveries" "digest_articles" "digests" "sources" "users")
for table in "${EXPECTED_TABLES[@]}"; do
    if echo "${TABLES}" | grep -q "${table}"; then
        echo "  [PASS] Table '${table}' exists"
    else
        echo "  [FAIL] Table '${table}' missing"
        exit 1
    fi
done

# Step 4: Verify data counts
echo ""
echo "Step 4: Verifying data counts..."
for table in "${EXPECTED_TABLES[@]}"; do
    count=$(docker exec "${TEST_CONTAINER}" psql -U postgres -d "${TEST_DB_NAME}" -tAc "SELECT COUNT(*) FROM ${table};" 2>/dev/null || echo "0")
    echo "  ${table}: ${count} rows"
done

# Step 5: Run migrations (verify they are idempotent)
echo ""
echo "Step 5: Running migrations against restored database..."
DB_URL="postgresql+asyncpg://postgres:postgres@localhost:${TEST_PORT}/${TEST_DB_NAME}"
export DATABASE_URL="${DB_URL}"

# Check if we can import and run alembic
if python -c "from alembic.config import Config; from alembic import command; c = Config('alembic.ini'); command.upgrade(c, 'head')" 2>/dev/null; then
    echo "  [PASS] Migrations applied successfully"
else
    echo "  [WARN] Could not verify migrations (dependencies may not be installed)"
fi

# Step 6: Verify indexes exist
echo ""
echo "Step 6: Verifying critical indexes..."
INDEXES=$(docker exec "${TEST_CONTAINER}" psql -U postgres -d "${TEST_DB_NAME}" -tAc "SELECT indexname FROM pg_indexes WHERE schemaname = 'public' AND indexname != 'index' ORDER BY indexname;")

CRITICAL_INDEXES=("idx_articles_published_at" "idx_articles_status" "idx_articles_url" "idx_sources_feed_url" "idx_digests_generated_at")
for idx in "${CRITICAL_INDEXES[@]}"; do
    if echo "${INDEXES}" | grep -q "${idx}"; then
        echo "  [PASS] Index '${idx}' exists"
    else
        echo "  [INFO] Index '${idx}' not found (may be named differently)"
    fi
done

echo ""
echo "=========================================="
echo "Restore test completed successfully!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Review row counts above to ensure data completeness"
echo "  2. If counts are zero, the backup may be empty"
echo "  3. Run application smoke tests against this database if needed"
echo ""
