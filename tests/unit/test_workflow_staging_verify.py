"""
Tests for the staging database verification GitHub Actions workflow.

Validates:
- workflow_dispatch only (no schedule, no push)
- uses STAGING_DATABASE_URL secret
- does not reference production secrets
- least-privilege permissions
- bounded timeout
- AI and email disabled
- verification script is invoked
- no credentials printed in the workflow
- no production or local secrets referenced
"""

from __future__ import annotations

import pathlib

import yaml

_WORKFLOW_PATH = (
    pathlib.Path(__file__).resolve().parents[2] / ".github" / "workflows" / "staging-verify-db.yml"
)


def _load_workflow() -> dict:
    assert _WORKFLOW_PATH.exists(), f"Workflow file not found at {_WORKFLOW_PATH}"
    return yaml.safe_load(_WORKFLOW_PATH.read_text(encoding="utf-8"))


def test_workflow_has_expected_name() -> None:
    workflow = _load_workflow()
    assert workflow.get("name") == "Staging Database Verification"


def test_workflow_is_manual_only() -> None:
    workflow = _load_workflow()
    triggers = workflow.get("on") or workflow.get(True) or {}
    assert "workflow_dispatch" in triggers
    assert "schedule" not in triggers
    assert "push" not in triggers
    assert "pull_request" not in triggers


def test_workflow_has_least_privilege_permissions() -> None:
    workflow = _load_workflow()
    permissions = workflow.get("permissions", {})
    assert permissions == {"contents": "read"}


def test_workflow_job_has_bounded_timeout() -> None:
    workflow = _load_workflow()
    job = workflow["jobs"]["verify-staging-db"]
    timeout = job.get("timeout-minutes")
    assert timeout is not None
    assert 5 <= timeout <= 30


def test_workflow_uses_staging_specific_concurrency() -> None:
    workflow = _load_workflow()
    job = workflow["jobs"]["verify-staging-db"]
    concurrency = job.get("concurrency", {})
    assert concurrency.get("group") == "staging-verify-db"
    assert concurrency.get("cancel-in-progress") is False


def test_workflow_uses_staging_database_secret() -> None:
    workflow = _load_workflow()
    job = workflow["jobs"]["verify-staging-db"]
    run_step = job["steps"][-1]
    env = run_step["env"]
    assert env.get("DATABASE_URL") == "${{ secrets.STAGING_DATABASE_URL }}"


def test_workflow_does_not_reference_production_secrets() -> None:
    workflow_str = _WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "FREE_DATABASE_URL" not in workflow_str
    assert "PROD_DATABASE_URL" not in workflow_str
    assert "FREE_REDIS_URL" not in workflow_str
    assert "FREE_JWT_SECRET_KEY" not in workflow_str


def test_workflow_does_not_pass_credentials_in_script() -> None:
    workflow = _load_workflow()
    job = workflow["jobs"]["verify-staging-db"]
    run_step = job["steps"][-1]
    script = run_step["run"]
    assert "DATABASE_URL" not in script
    assert "password" not in script.lower()


def test_workflow_disables_ai_and_email() -> None:
    workflow = _load_workflow()
    job = workflow["jobs"]["verify-staging-db"]
    run_step = job["steps"][-1]
    env = run_step["env"]
    assert env.get("ENVIRONMENT") == "staging"
    assert env.get("AI_ENABLED") == "false"
    assert env.get("EMAIL_ENABLED") == "false"
    assert "OPENAI_API_KEY" not in env
    assert "ANTHROPIC_API_KEY" not in env


def test_workflow_invokes_verification_script() -> None:
    workflow = _load_workflow()
    job = workflow["jobs"]["verify-staging-db"]
    run_step = job["steps"][-1]
    assert "scripts/verify_staging_db.py" in run_step["run"]


def test_workflow_uses_fail_fast_bash() -> None:
    workflow = _load_workflow()
    job = workflow["jobs"]["verify-staging-db"]
    run_step = job["steps"][-1]
    assert "set -euo pipefail" in run_step["run"]


def test_workflow_installs_dependencies_with_pip() -> None:
    workflow_str = _WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "pip install -e ." in workflow_str
    assert "poetry install" not in workflow_str


def test_workflow_has_no_secret_values_in_yaml() -> None:
    workflow_str = _WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "postgresql://" not in workflow_str
    assert "redis://" not in workflow_str
    assert "password" not in workflow_str.lower() or "password" not in workflow_str


def test_workflow_job_count_is_single() -> None:
    workflow = _load_workflow()
    assert len(workflow["jobs"]) == 1
