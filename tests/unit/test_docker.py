"""
Unit tests for Docker and container configuration.

Phase 9: Docker and migration tests.
"""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent.parent


def test_dockerfile_exists() -> None:
    assert (ROOT / "Dockerfile").exists()


def test_dockerfile_has_non_root_user() -> None:
    content = (ROOT / "Dockerfile").read_text()
    assert "USER appuser" in content


def test_dockerfile_runs_migrations() -> None:
    content = (ROOT / "Dockerfile").read_text()
    assert "alembic upgrade head" in content


def test_docker_compose_exists() -> None:
    assert (ROOT / "docker-compose.yml").exists()


def test_docker_compose_is_valid_yaml() -> None:
    with (ROOT / "docker-compose.yml").open() as f:
        data = yaml.safe_load(f)
    assert "services" in data


def test_docker_compose_has_required_services() -> None:
    with (ROOT / "docker-compose.yml").open() as f:
        data = yaml.safe_load(f)
    services = data.get("services", {})
    assert "postgres" in services
    assert "redis" in services
    assert "web" in services


def test_docker_compose_services_have_healthchecks() -> None:
    with (ROOT / "docker-compose.yml").open() as f:
        data = yaml.safe_load(f)
    for name, service in data.get("services", {}).items():
        if name in ("postgres", "redis", "web"):
            assert "healthcheck" in service, f"{name} missing healthcheck"


def test_docker_compose_web_has_required_env_vars() -> None:
    with (ROOT / "docker-compose.yml").open() as f:
        data = yaml.safe_load(f)
    web_env = data["services"]["web"].get("environment", {})
    assert "DATABASE_URL" in web_env
    assert "REDIS_URL" in web_env
    assert "CELERY_BROKER_URL" in web_env
