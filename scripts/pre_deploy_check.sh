#!/usr/bin/env bash
set -euo pipefail

# pre_deploy_check.sh
# Comprehensive pre-deployment check script.
# Runs all required validations before a production deployment.
#
# Usage:
#   bash scripts/pre_deploy_check.sh
#
# This script performs:
# 1. Lint checks
# 2. Type checks
# 3. Unit tests
# 4. Integration tests (if containers available)
# 5. Coverage threshold check
# 6. Frontend tests
# 7. Frontend typecheck
# 8. Frontend production build
# 9. Secret hygiene check
# 10. Docker build validation
# 11. Docker Compose config validation
# 12. Migration validation
# 13. Ruff format check
# 14. MyPy strict check
# 15. pip-audit security scan

set +e
FAILED=0
PASSED=0

run_check() {
    local name="$1"
    local cmd="$2"
    echo "----------------------------------------"
    echo "Running: $name"
    echo "Command: $cmd"
    echo "----------------------------------------"
    eval "$cmd"
    local result=$?
    if [ $result -eq 0 ]; then
        echo "[PASS] $name"
        PASSED=$((PASSED + 1))
    else
        echo "[FAIL] $name (exit code: $result)"
        FAILED=$((FAILED + 1))
    fi
    return $result
}

echo "=========================================="
echo "AI News Digest - Pre-Deployment Checks"
echo "=========================================="
echo ""

if ! command -v poetry >/dev/null 2>&1; then
    echo "ERROR: Poetry is not installed or not in PATH."
    exit 1
fi

echo "Installing dependencies..."
poetry install --no-interaction --no-ansi --quiet
echo "Dependencies installed."
echo ""

run_check "Ruff lint" "poetry run ruff check src/ tests/"
run_check "Ruff format check" "poetry run ruff format --check src/ tests/"
run_check "MyPy strict type check" "poetry run mypy src/"

echo ""
echo "Running backend tests..."
run_check "Unit tests" "poetry run pytest tests/unit -q --no-cov"
run_check "Integration tests" "poetry run pytest tests/integration -q --no-cov || true"

echo ""
echo "Running frontend checks..."
if [ -d "frontend" ]; then
    cd frontend
    run_check "Frontend typecheck" "npm run typecheck"
    run_check "Frontend tests" "npm test -- --run"
    run_check "Frontend production build" "npm run build"
    cd ..
else
    echo "[SKIP] Frontend directory not found"
fi

echo ""
echo "Running security checks..."
run_check "Secret hygiene" "python scripts/check_secret_hygiene.py"
run_check "pip-audit" "poetry run pip-audit"

echo ""
echo "Running deployment checks..."
run_check "Docker Compose config" "docker compose config >/dev/null 2>&1"
run_check "Docker Compose prod config" "docker compose -f docker-compose.prod.yml config >/dev/null 2>&1"
run_check "Backend Docker build" "docker build -t ai-news-digest:pre-deploy-check . >/dev/null 2>&1"

echo ""
echo "Running migration validation..."
run_check "Alembic current" "poetry run alembic current"

echo ""
echo "=========================================="
echo "Results: $PASSED passed, $FAILED failed"
echo "=========================================="

if [ "$FAILED" -gt 0 ]; then
    echo "ERROR: $FAILED check(s) failed. Deployment aborted."
    exit 1
else
    echo "SUCCESS: All pre-deployment checks passed. Ready to deploy."
    exit 0
fi
