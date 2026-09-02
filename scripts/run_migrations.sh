#!/usr/bin/env bash
set -euo pipefail

# Run Alembic database migrations
# Usage: ./scripts/run_migrations.sh

echo "Running database migrations..."
poetry run alembic upgrade head
echo "Migrations applied successfully."
