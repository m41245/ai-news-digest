FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app


FROM base AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip && pip install "poetry>=2.0,<3.0"

COPY pyproject.toml poetry.lock README.md ./
RUN poetry config virtualenvs.create false \
    && poetry install --without dev --no-interaction --no-ansi --no-root

COPY src/ ./src/
RUN poetry install --only-root --no-interaction --no-ansi


FROM base AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app/src ./src/
COPY README.md alembic.ini ./
COPY migrations/ ./migrations/

RUN printf '%s\n' \
  '#!/bin/bash' \
  'set -e' \
  '' \
  'echo "Running database migrations..."' \
  'python -m alembic upgrade head' \
  '' \
  'echo "Starting application..."' \
  'exec "$@"' \
  > /app/entrypoint.sh \
  && chmod +x /app/entrypoint.sh

RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/live', timeout=5)"

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["uvicorn", "ai_news_digest.main:app", "--host", "0.0.0.0", "--port", "8000"]
