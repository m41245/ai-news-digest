FROM python:3.12-alpine AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app


FROM base AS builder

RUN apk add --no-cache \
    gcc \
    musl-dev \
    postgresql-dev

RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir "poetry>=2.0,<3.0"

COPY pyproject.toml poetry.lock README.md ./
RUN poetry config virtualenvs.create false \
    && poetry install --without dev --no-interaction --no-ansi --no-root

COPY src/ ./src/
RUN poetry install --only-root --no-interaction --no-ansi


FROM base AS runtime

RUN apk add --no-cache libpq

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Remove build-time tooling and its vendored vulnerable dependencies from the runtime image.
RUN rm -rf /usr/local/lib/python3.12/site-packages/pip \
           /usr/local/lib/python3.12/site-packages/pip-*.dist-info \
           /usr/local/lib/python3.12/site-packages/poetry \
           /usr/local/lib/python3.12/site-packages/poetry-*.dist-info \
           /usr/local/lib/python3.12/site-packages/poetry_core* \
           /usr/local/bin/pip /usr/local/bin/pip3 /usr/local/bin/pip3.12 \
           /usr/local/bin/poetry

COPY --from=builder /app/src ./src/
COPY README.md alembic.ini ./
COPY migrations/ ./migrations/

RUN printf '%s\n' \
  '#!/bin/sh' \
  'set -e' \
  '' \
  'echo "Running database migrations..."' \
  'python -m alembic upgrade head' \
  '' \
  'echo "Starting application..."' \
  'exec "$@"' \
  > /app/entrypoint.sh \
  && chmod +x /app/entrypoint.sh

RUN adduser -D -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/live', timeout=5)"

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["uvicorn", "ai_news_digest.main:app", "--host", "0.0.0.0", "--port", "8000"]