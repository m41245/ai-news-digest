"""Regression checks for production entrypoint configuration."""

from __future__ import annotations

from pathlib import Path


def test_entrypoint_does_not_require_redis_password() -> None:
    entrypoint = Path("entrypoint.sh").read_text(encoding="utf-8")
    assert 'if [ -z "${REDIS_PASSWORD:-}" ]' not in entrypoint
    assert "REDIS_PASSWORD is not set" not in entrypoint
    assert "REDIS_URL is not set" in entrypoint


def test_entrypoint_keeps_redis_url_preflight() -> None:
    entrypoint = Path("entrypoint.sh").read_text(encoding="utf-8")
    assert 'if [ -z "${REDIS_URL:-}" ]; then' in entrypoint
    assert 'if [ -z "${CELERY_BROKER_URL:-}" ]; then' in entrypoint
