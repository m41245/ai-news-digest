"""Unit tests for render.yaml blueprint invariants."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
RENDER = ROOT / "render.yaml"


def _load() -> dict:
    with RENDER.open() as f:
        return yaml.safe_load(f)


def test_render_yaml_is_valid_yaml() -> None:
    data = _load()
    assert "services" in data


def test_render_web_health_check_path() -> None:
    data = _load()
    web = next(s for s in data["services"] if s["name"] == "ai-news-digest-api")
    assert web["healthCheckPath"] == "/health/live"


def test_render_web_does_not_disable_migrations() -> None:
    data = _load()
    web = next(s for s in data["services"] if s["name"] == "ai-news-digest-api")
    env = {e["key"]: e.get("value") for e in web.get("envVars", []) if "key" in e}
    assert env.get("RUN_MIGRATIONS") != "false"


def test_render_worker_services_disable_migrations() -> None:
    data = _load()
    workers = [s for s in data["services"] if s["type"] == "worker"]
    if not workers:
        pytest.skip("No worker services defined")
    for worker in workers:
        env = {e["key"]: e.get("value") for e in worker.get("envVars", []) if "key" in e}
        assert env.get("RUN_MIGRATIONS") == "false", worker["name"]


def test_render_workers_do_not_claim_free_plan() -> None:
    data = _load()
    for worker in (s for s in data["services"] if s["type"] == "worker"):
        assert worker.get("plan") != "free", worker["name"]


def test_render_workers_share_jwt_secret() -> None:
    data = _load()
    for worker in (s for s in data["services"] if s["type"] == "worker"):
        jwt_entries = [e for e in worker.get("envVars", []) if e.get("key") == "JWT_SECRET_KEY"]
        assert jwt_entries, worker["name"]
        entry = jwt_entries[0]
        assert "fromService" in entry, worker["name"]
        assert entry["fromService"]["envVarKey"] == "JWT_SECRET_KEY"


def test_render_web_generates_jwt_secret() -> None:
    data = _load()
    web = next(s for s in data["services"] if s["name"] == "ai-news-digest-api")
    jwt_entries = [e for e in web.get("envVars", []) if e.get("key") == "JWT_SECRET_KEY"]
    assert jwt_entries and jwt_entries[0].get("generateValue") is True
