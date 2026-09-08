#!/bin/bash
set -euo pipefail

export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1

log() {
    echo "[entrypoint] $*"
}

fail() {
    echo "[entrypoint][ERROR] $*" >&2
    exit 1
}

log "Running pre-flight checks..."

if [ -z "${DATABASE_URL:-}" ]; then
    fail "DATABASE_URL is not set. Cannot start application."
fi

if [ -z "${JWT_SECRET_KEY:-}" ]; then
    fail "JWT_SECRET_KEY is not set. Cannot start application."
fi

log "Waiting for PostgreSQL to become available..."
python -c "
import sys
import time

import asyncpg

dsn = '${DATABASE_URL}'
max_attempts = 60
for attempt in range(1, max_attempts + 1):
    try:
        import asyncio
        async def check():
            conn = await asyncpg.connect(dsn)
            await conn.execute('SELECT 1')
            await conn.close()
            return True
        if asyncio.run(check()):
            print(f'PostgreSQL is ready (attempt {attempt})')
            sys.exit(0)
    except Exception:
        pass
    print(f'Waiting for PostgreSQL... (attempt {attempt}/{max_attempts})')
    time.sleep(2)

print('PostgreSQL did not become ready in time')
sys.exit(1)
" || fail "PostgreSQL pre-flight check failed"

log "Running database migrations..."
python -m alembic upgrade head

log "Migrations complete. Starting application..."
exec "$@"
