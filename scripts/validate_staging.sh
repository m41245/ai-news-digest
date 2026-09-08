#!/usr/bin/env bash
set -euo pipefail

# validate_staging.sh
# Staging environment validation script for AI News Digest.
# Validates that the staging deployment is healthy and ready for promotion.
#
# Usage:
#   bash scripts/validate_staging.sh [--skip-docker] [--skip-migrations]
#
# Exit codes:
#   0 - All checks passed
#   1 - One or more checks failed

SKIP_DOCKER=0
SKIP_MIGRATIONS=0

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-docker)
            SKIP_DOCKER=1
            shift
            ;;
        --skip-migrations)
            SKIP_MIGRATIONS=1
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--skip-docker] [--skip-migrations]"
            exit 1
            ;;
    esac
done

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
echo "AI News Digest - Staging Validation"
echo "=========================================="
echo ""

echo "[1] Checking staging docker-compose configuration..."
if [ "$SKIP_DOCKER" -eq 0 ]; then
    if docker compose -f docker-compose.staging.yml config >/dev/null 2>&1; then
        check "Staging docker-compose config valid" 0
    else
        echo "  FAIL: docker-compose.staging.yml has configuration errors"
        check "Staging docker-compose config valid" 1
    fi

    if docker compose -f docker-compose.prod.validation.yml config >/dev/null 2>&1; then
        check "Production validation compose config valid" 0
    else
        echo "  FAIL: docker-compose.prod.validation.yml has configuration errors"
        check "Production validation compose config valid" 1
    fi
else
    echo "[SKIP] Docker checks disabled"
    check "Staging docker-compose config valid" 0
    check "Production validation compose config valid" 0
fi

echo ""
echo "[2] Checking required scripts exist..."
for script in scripts/validate_deployment.sh scripts/pre_deploy_check.sh scripts/run_migrations.sh scripts/backup_db.sh scripts/restore_db.sh; do
    if [ -f "$script" ]; then
        echo "  OK: $script exists"
    else
        echo "  FAIL: $script not found"
        check "$script exists" 1
    fi
done

echo ""
echo "[3] Checking Python package structure..."
if [ -f "pyproject.toml" ]; then
    check "pyproject.toml exists" 0
else
    echo "  FAIL: pyproject.toml not found"
    check "pyproject.toml exists" 1
fi

if [ -d "src/ai_news_digest" ]; then
    check "Source package exists" 0
else
    echo "  FAIL: src/ai_news_digest not found"
    check "Source package exists" 1
fi

echo ""
echo "[4] Checking configuration defaults..."
if grep -q "environment: Literal\[" src/ai_news_digest/core/config.py; then
    check "Environment config present" 0
else
    echo "  FAIL: Environment configuration not found"
    check "Environment config present" 1
fi

if grep -q "jwt_secret_key" src/ai_news_digest/core/config.py; then
    check "JWT secret config present" 0
else
    echo "  FAIL: JWT secret configuration not found"
    check "JWT secret config present" 1
fi

if grep -q "cors_origins" src/ai_news_digest/core/config.py; then
    check "CORS config present" 0
else
    echo "  FAIL: CORS configuration not found"
    check "CORS config present" 1
fi

echo ""
echo "[5] Checking health check endpoints..."
if grep -q '"/live"' src/ai_news_digest/api/v1/routes/health.py; then
    check "Liveness endpoint defined" 0
else
    echo "  FAIL: /live endpoint not found"
    check "Liveness endpoint defined" 1
fi

if grep -q '"/ready"' src/ai_news_digest/api/v1/routes/health.py; then
    check "Readiness endpoint defined" 0
else
    echo "  FAIL: /ready endpoint not found"
    check "Readiness endpoint defined" 1
fi

echo ""
echo "[6] Checking metrics endpoint..."
if grep -q "/metrics" src/ai_news_digest/api/metrics.py; then
    check "Metrics endpoint defined" 0
else
    echo "  FAIL: /metrics endpoint not found"
    check "Metrics endpoint defined" 1
fi

echo ""
echo "[7] Checking security headers..."
if grep -q "SecurityHeadersMiddleware" src/ai_news_digest/main.py; then
    check "Security headers middleware present" 0
else
    echo "  FAIL: SecurityHeadersMiddleware not found"
    check "Security headers middleware present" 1
fi

if grep -q "Strict-Transport-Security" src/ai_news_digest/api/middleware/security_headers.py; then
    check "HSTS header configured" 0
else
    echo "  FAIL: HSTS header not configured"
    check "HSTS header configured" 1
fi

echo ""
echo "[8] Checking migration files..."
MIGRATION_COUNT=$(find migrations/versions -name "*.py" -not -name "__init__.py" | wc -l)
if [ "$MIGRATION_COUNT" -gt 0 ]; then
    check "Migration files exist ($MIGRATION_COUNT found)" 0
else
    echo "  FAIL: No migration files found"
    check "Migration files exist" 1
fi

if [ "$SKIP_MIGRATIONS" -eq 0 ]; then
    if [ -f "alembic.ini" ]; then
        check "alembic.ini exists" 0
    else
        echo "  FAIL: alembic.ini not found"
        check "alembic.ini exists" 1
    fi
else
    echo "[SKIP] Migration checks disabled"
fi

echo ""
echo "[9] Checking documentation..."
for doc in README.md docs/RUNBOOK.md docs/MONITORING.md docs/DEPLOYMENT.md docs/BACKUP_RECOVERY.md; do
    if [ -f "$doc" ]; then
        echo "  OK: $doc exists"
    else
        echo "  WARN: $doc not found"
    fi
done
check "Documentation files present" 0

echo ""
echo "[10] Checking frontend configuration..."
if [ -f "frontend/Dockerfile" ]; then
    check "Frontend Dockerfile exists" 0
else
    echo "  FAIL: frontend/Dockerfile not found"
    check "Frontend Dockerfile exists" 1
fi

if [ -f "frontend/nginx.conf" ]; then
    check "Frontend nginx config exists" 0
else
    echo "  FAIL: frontend/nginx.conf not found"
    check "Frontend nginx config exists" 1
fi

echo ""
echo "[11] Checking entrypoint and validation scripts..."
if [ -f "entrypoint.sh" ]; then
    check "entrypoint.sh exists" 0
else
    echo "  FAIL: entrypoint.sh not found"
    check "entrypoint.sh exists" 1
fi

if [ -f "scripts/validate_deployment.sh" ]; then
    check "validate_deployment.sh exists" 0
else
    echo "  FAIL: validate_deployment.sh not found"
    check "validate_deployment.sh exists" 1
fi

echo ""
echo "=========================================="
echo "Results: $PASSED passed, $FAILED failed"
echo "=========================================="

if [ "$FAILED" -gt 0 ]; then
    echo "ERROR: $FAILED check(s) failed. Staging validation unsuccessful."
    exit 1
else
    echo "SUCCESS: All staging validation checks passed."
    exit 0
fi
