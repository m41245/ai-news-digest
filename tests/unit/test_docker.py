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


def test_docker_compose_staging_exists() -> None:
    assert (ROOT / "docker-compose.staging.yml").exists()


def test_docker_compose_staging_has_explicit_project_name() -> None:
    with (ROOT / "docker-compose.staging.yml").open() as f:
        data = yaml.safe_load(f)
    assert data.get("name") == "ai-news-digest-staging", (
        "Staging compose must have an explicit project name to isolate volumes from development"
    )


def test_docker_compose_staging_has_isolated_postgres_volume() -> None:
    with (ROOT / "docker-compose.staging.yml").open() as f:
        data = yaml.safe_load(f)
    postgres_service = data["services"]["postgres"]
    volumes = postgres_service.get("volumes", [])
    volume_names = []
    for vol in volumes:
        if isinstance(vol, str) and ":" in vol:
            volume_names.append(vol.split(":")[0])
        elif isinstance(vol, dict):
            volume_names.extend(vol.keys())
    assert "postgres_data" in volume_names


def test_docker_compose_staging_has_isolated_redis_volume() -> None:
    with (ROOT / "docker-compose.staging.yml").open() as f:
        data = yaml.safe_load(f)
    redis_service = data["services"]["redis"]
    volumes = redis_service.get("volumes", [])
    volume_names = []
    for vol in volumes:
        if isinstance(vol, str) and ":" in vol:
            volume_names.append(vol.split(":")[0])
        elif isinstance(vol, dict):
            volume_names.extend(vol.keys())
    assert "redis_data" in volume_names


def test_docker_compose_staging_project_name_differs_from_development() -> None:
    with (ROOT / "docker-compose.staging.yml").open() as f:
        staging_data = yaml.safe_load(f)
    staging_name = staging_data.get("name")
    assert staging_name is not None
    assert staging_name != "ai-news-digest", (
        f"Staging project name '{staging_name}' must differ from development project name"
    )


def test_docker_compose_development_unchanged() -> None:
    with (ROOT / "docker-compose.yml").open() as f:
        data = yaml.safe_load(f)
    assert data.get("name") is None, "Development compose should not have an explicit project name"


def test_env_staging_email_disabled() -> None:
    env_staging = (ROOT / ".env.staging").read_text()
    assert "EMAIL_ENABLED=false" in env_staging, (
        ".env.staging must explicitly disable email delivery"
    )


def test_env_staging_has_required_fields() -> None:
    env_staging = (ROOT / ".env.staging").read_text()
    assert "ENVIRONMENT=staging" in env_staging
    assert "AI_ENABLED=false" in env_staging
    assert "POSTGRES_DB=ai_news_digest_staging" in env_staging
