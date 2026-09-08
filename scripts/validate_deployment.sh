#!/usr/bin/env bash
set -euo pipefail

# validate_deployment.sh
# Pre-deployment validation script for AI News Digest.
# Checks that all required services, configurations, and secrets are in place.
#
# Usage:
#   bash scripts/validate_deployment.sh [--env-file .env.prod.local]
#
# Exit codes:
#   0 - All checks passed
#   1 - One or more checks failed

ENV_FILE="${1:-}"
if [ -n "${ENV_FILE}" ]; then
    if [ ! -f "${ENV_FILE}" ]; then
        echo "ERROR: Environment file not found: ${ENV_FILE}"
        exit 1
    fi
    echo "Loading environment from: ${ENV_FILE}"
    set -a
    source "${ENV_FILE}"
    set +a
fi

FAILED=0
PASSED=0

check() {
    local name="$1"
    local result="$2"
    if [ "$result" -eq 0 ]; then
        echo "[PASS] $name"
        PASSED=$((PASSED + 1))
    else
        echo "[FAIL] $name"
        FAILED=$((FAILED + 1))
    fi
}

echo "=========================================="
echo "AI News Digest - Pre-Deployment Validation"
echo "=========================================="
echo ""

echo "[1] Checking required environment variables..."
missing=0
for var in DATABASE_URL REDIS_URL CELERY_BROKER_URL CELERY_RESULT_BACKEND JWT_SECRET_KEY; do
    if [ -z "${!var:-}" ]; then
        echo "  MISSING: $var"
        missing=$((missing + 1))
    else
        echo "  OK: $var is set"
    fi
done
check "Required environment variables" $([ "$missing" -eq 0 ] && echo 0 || echo 1)

echo ""
echo "[2] Checking Docker images..."
if docker image inspect ai-news-digest:latest >/dev/null 2>&1; then
    check "Backend Docker image exists" 0
else
    echo "  WARN: ai-news-digest:latest not found locally. Will use DOCKER_IMAGE if set."
    check "Backend Docker image exists" 1
fi

if docker image inspect ai-news-digest-frontend:latest >/dev/null 2>&1; then
    check "Frontend Docker image exists" 0
else
    echo "  WARN: ai-news-digest-frontend:latest not found locally."
    check "Frontend Docker image exists" 1
fi

echo ""
echo "[3] Checking Docker Compose configuration..."
if docker compose config >/dev/null 2>&1; then
    check "docker-compose.yml config valid" 0
else
    check "docker-compose.yml config valid" 1
fi

if docker compose -f docker-compose.prod.yml config >/dev/null 2>&1; then
    check "docker-compose.prod.yml config valid" 0
else
    check "docker-compose.prod.yml config valid" 1
fi

echo ""
echo "[4] Checking JWT_SECRET_KEY strength..."
if [ -n "${JWT_SECRET_KEY:-}" ]; then
    secret_len=${#JWT_SECRET_KEY}
    if [ "$secret_len" -lt 32 ]; then
        echo "  FAIL: JWT_SECRET_KEY is too short ($secret_len chars, minimum 32)"
        check "JWT_SECRET_KEY strength" 1
    else
        weak_patterns="change.me changeme secret please-replace your-secret-key-here test-secret ci-fake fake-key not-for-production local-dev"
        is_weak=0
        for pattern in $weak_patterns; do
            if echo "$JWT_SECRET_KEY" | grep -qi "$pattern"; then
                is_weak=1
                break
            fi
        done
        if [ "$is_weak" -eq 1 ]; then
            echo "  FAIL: JWT_SECRET_KEY contains weak/placeholder pattern"
            check "JWT_SECRET_KEY strength" 1
        else
            echo "  OK: JWT_SECRET_KEY looks strong ($secret_len chars)"
            check "JWT_SECRET_KEY strength" 0
        fi
    fi
else
    echo "  FAIL: JWT_SECRET_KEY is not set"
    check "JWT_SECRET_KEY strength" 1
fi

echo ""
echo "[5] Checking Redis password configuration..."
if [ -n "${REDIS_PASSWORD:-}" ]; then
    if [ -z "$REDIS_PASSWORD" ]; then
        echo "  WARN: REDIS_PASSWORD is set but empty. Redis will not require authentication."
    else
        echo "  OK: REDIS_PASSWORD is set"
    fi
else
    echo "  WARN: REDIS_PASSWORD is not set. Redis will not require authentication."
fi
check "Redis password check" 0

echo ""
echo "[6] Checking CORS configuration..."
if [ -n "${CORS_ORIGINS:-}" ]; then
    echo "  OK: CORS_ORIGINS is configured: $CORS_ORIGINS"
    check "CORS configuration" 0
else
    echo "  WARN: CORS_ORIGINS is not set. Using fail-closed empty list in production."
    check "CORS configuration" 1
fi

echo ""
echo "[7] Checking database URL format..."
if echo "${DATABASE_URL:-}" | grep -q "^postgresql+asyncpg://"; then
    echo "  OK: DATABASE_URL uses asyncpg driver"
    check "Database URL format" 0
elif echo "${DATABASE_URL:-}" | grep -q "^postgresql+psycopg://"; then
    echo "  OK: DATABASE_URL uses psycopg driver"
    check "Database URL format" 0
elif echo "${DATABASE_URL:-}" | grep -q "^postgresql://"; then
    echo "  WARN: DATABASE_URL missing driver specification, will use default"
    check "Database URL format" 0
else
    echo "  FAIL: DATABASE_URL has unexpected format: ${DATABASE_URL:-<empty>}"
    check "Database URL format" 1
fi

echo ""
echo "[8] Checking secret hygiene..."
if [ -f scripts/check_secret_hygiene.py ]; then
    if python scripts/check_secret_hygiene.py >/dev/null 2>&1; then
        check "Secret hygiene check" 0
    else
        check "Secret hygiene check" 1
    fi
else
    echo "  SKIP: check_secret_hygiene.py not found"
    check "Secret hygiene check" 0
fi

echo ""
echo "[9] Checking migration status..."
if command -v poetry >/dev/null 2>&1; then
    if poetry run alembic current >/dev/null 2>&1; then
        check "Alembic current migration check" 0
    else
        echo "  WARN: Could not check alembic current (database not available?)"
        check "Alembic current migration check" 1
    fi
else
    echo "  SKIP: Poetry not found"
    check "Poetry availability" 0
fi

echo ""
echo "[10] Checking .gitignore for secret files..."
gitignore_ok=0
for pattern in ".env" ".env.prod.local" ".env.*.local"; do
    if grep -qF "$pattern" .gitignore 2>/dev/null; then
        echo "  OK: $pattern is gitignored"
    else
        echo "  FAIL: $pattern is NOT gitignored"
        gitignore_ok=1
    fi
done
check "Gitignore secret patterns" $gitignore_ok

echo ""
echo "=========================================="
echo "Results: $PASSED passed, $FAILED failed"
echo "=========================================="

if [ "$FAILED" -gt 0 ]; then
    echo "ERROR: $FAILED check(s) failed. Fix the issues above before deploying."
    exit 1
else
    echo "SUCCESS: All pre-deployment checks passed."
    exit 0
fi
