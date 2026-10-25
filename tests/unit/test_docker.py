"""
Unit tests for Docker and container configuration.

Phase 9: Docker and migration tests.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent.parent

ENV_STAGING = ROOT / ".env.staging"

# Why these two assertions are conditional instead of unconditional:
#
# ``.env.staging`` is a *host* file that is passed to Compose via
# ``--env-file .env.staging`` (see docs/DEPLOYMENT.md). It holds real staging
# credentials, so ``.gitignore`` keeps it out of version control and
# ``scripts/check_secret_hygiene.py`` treats it as a local secret store. It is
# therefore intentionally absent from a fresh clone and from CI. Committing a
# stub would defeat the gitignore, and fabricating placeholder secrets would
# only exercise the placeholder, so the value of these assertions is guarded by
# the file's presence: they are enforced wherever the file legitimately exists
# and skipped, never failed, where it does not.
ENV_STAGING_SKIP_REASON = (
    ".env.staging is gitignored because it contains real staging credentials, so it "
    "exists only on hosts that deploy staging; the assertion is skipped here"
)


def _read_env_staging(path: Path = ENV_STAGING) -> str:
    """Return the contents of a local env file, skipping when it is absent."""
    if not path.exists():
        pytest.skip(ENV_STAGING_SKIP_REASON)
    return path.read_text(encoding="utf-8")


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
    assert (
        data.get("name") == "ai-news-digest-staging"
    ), "Staging compose must have an explicit project name to isolate volumes from development"


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
    assert (
        staging_name != "ai-news-digest"
    ), f"Staging project name '{staging_name}' must differ from development project name"


def test_docker_compose_development_unchanged() -> None:
    with (ROOT / "docker-compose.yml").open() as f:
        data = yaml.safe_load(f)
    assert data.get("name") is None, "Development compose should not have an explicit project name"


def test_env_staging_email_disabled() -> None:
    env_staging = _read_env_staging()
    assert (
        "EMAIL_ENABLED=false" in env_staging
    ), ".env.staging must explicitly disable email delivery"


def test_env_staging_has_required_fields() -> None:
    env_staging = _read_env_staging()
    assert "ENVIRONMENT=staging" in env_staging
    assert "AI_ENABLED=false" in env_staging
    assert "POSTGRES_DB=ai_news_digest_staging" in env_staging


def test_env_staging_is_gitignored() -> None:
    """.env.staging must stay out of version control (secret hygiene policy)."""
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    patterns = {line.strip() for line in gitignore.splitlines() if line.strip()}
    assert ".env.staging" in patterns, ".env.staging must be listed in .gitignore"


def test_read_env_staging_skips_when_absent(tmp_path: Path) -> None:
    """Missing local env file must skip, not fail, so CI never red-fails on it."""
    missing = tmp_path / ".env.staging"

    with pytest.raises(pytest.skip.Exception) as exc_info:
        _read_env_staging(missing)

    assert ENV_STAGING_SKIP_REASON in str(exc_info.value)


def test_read_env_staging_returns_contents_when_present(tmp_path: Path) -> None:
    """The helper still returns the real file contents when the file exists."""
    env_file = tmp_path / ".env.staging"
    env_file.write_text("ENVIRONMENT=staging\nEMAIL_ENABLED=false\n", encoding="utf-8")

    assert _read_env_staging(env_file) == "ENVIRONMENT=staging\nEMAIL_ENABLED=false\n"


def test_docker_compose_prod_exists() -> None:
    assert (ROOT / "docker-compose.prod.yml").exists()


def test_docker_compose_prod_is_valid_yaml() -> None:
    with (ROOT / "docker-compose.prod.yml").open() as f:
        data = yaml.safe_load(f)
    assert "services" in data


def test_docker_compose_prod_frontend_uses_image_not_build() -> None:
    with (ROOT / "docker-compose.prod.yml").open() as f:
        data = yaml.safe_load(f)
    frontend = data["services"]["frontend"]
    assert "image" in frontend, "Prod frontend must use a published image, not build"
    assert "build" not in frontend, "Prod frontend must not rebuild on the remote host"
    assert (
        "${FRONTEND_IMAGE" in frontend["image"]
    ), "Prod frontend image must reference FRONTEND_IMAGE for CI-published image"


def test_docker_compose_prod_frontend_not_latest_by_default() -> None:
    with (ROOT / "docker-compose.prod.yml").open() as f:
        data = yaml.safe_load(f)
    frontend = data["services"]["frontend"]
    assert (
        "FRONTEND_IMAGE" in frontend["image"]
    ), "Frontend must use FRONTEND_IMAGE variable, not a hardcoded latest tag"


def test_docker_compose_prod_backend_services_use_docker_image() -> None:
    with (ROOT / "docker-compose.prod.yml").open() as f:
        data = yaml.safe_load(f)
    for svc_name in ("web", "celery_worker", "celery_beat"):
        svc = data["services"][svc_name]
        assert "image" in svc, f"{svc_name} must have an image directive"
        assert (
            "${DOCKER_IMAGE" in svc["image"]
        ), f"{svc_name} must reference DOCKER_IMAGE for the CI-published backend image"


def test_docker_compose_prod_validation_frontend_uses_image() -> None:
    with (ROOT / "docker-compose.prod.validation.yml").open() as f:
        data = yaml.safe_load(f)
    frontend = data["services"]["frontend"]
    assert "image" in frontend
    assert "build" not in frontend
    assert "${FRONTEND_IMAGE" in frontend["image"]


def test_docker_compose_staging_frontend_preserves_build() -> None:
    """Local/staging development compose should still build from source."""
    with (ROOT / "docker-compose.staging.yml").open() as f:
        data = yaml.safe_load(f)
    frontend = data["services"]["frontend"]
    assert "build" in frontend, "Staging compose frontend must keep build for local development"


def test_dockerfile_ends_with_newline() -> None:
    content = (ROOT / "Dockerfile").read_bytes()
    assert content.endswith(b"\n"), "Dockerfile must end with a trailing newline"


def test_dockerfile_healthcheck_skips_non_web_containers() -> None:
    content = (ROOT / "Dockerfile").read_text()
    assert "HEALTHCHECK" in content
    assert "RUN_MIGRATIONS" in content
    # Non-web (worker/beat) containers must not be forced through the HTTP check.
    assert "sys.exit(0)" in content


def test_dockerfile_healthcheck_handles_empty_port() -> None:
    content = (ROOT / "Dockerfile").read_text()
    assert (
        'os.environ.get("PORT") or "8000"' in content
        or "os.environ.get('PORT') or '8000'" in content
    )


def test_dockerfile_preserves_migration_gating() -> None:
    content = (ROOT / "Dockerfile").read_text()
    assert "RUN_MIGRATIONS:-true" in content
    assert "alembic upgrade head" in content
