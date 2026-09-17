"""
Tests for the staging GitHub Actions workflow.

Validates:
- workflow_dispatch is present
- no schedule triggers
- staging-specific secrets are used
- staging environment semantics are hardcoded
- AI and email are explicitly disabled
- permissions are least-privilege
- concurrency group is staging-specific
"""

from __future__ import annotations

import pathlib

import yaml

_WORKFLOW_PATH = (
    pathlib.Path(__file__).resolve().parents[2]
    / ".github"
    / "workflows"
    / "scheduled-tasks-staging.yml"
)


def _load_workflow() -> dict:
    assert _WORKFLOW_PATH.exists(), f"Staging workflow file not found at {_WORKFLOW_PATH}"
    return yaml.safe_load(_WORKFLOW_PATH.read_text(encoding="utf-8"))


def test_staging_workflow_has_expected_name() -> None:
    workflow = _load_workflow()
    assert workflow.get("name") == "Scheduled Tasks (Staging)"


def test_staging_workflow_has_only_workflow_dispatch() -> None:
    workflow = _load_workflow()
    triggers = workflow.get("on") or workflow.get(True) or {}
    assert "workflow_dispatch" in triggers
    assert "schedule" not in triggers


def test_staging_workflow_has_manual_task_choices() -> None:
    workflow = _load_workflow()
    triggers = workflow.get("on") or workflow.get(True) or {}
    dispatch = triggers.get("workflow_dispatch", {})
    task_options = dispatch.get("inputs", {}).get("task", {}).get("options", [])
    expected_tasks = {
        "ingest",
        "summarize",
        "categorize",
        "analyze",
        "cluster",
        "timeline",
        "ranking",
        "conflict",
        "story-activity",
        "trend",
        "evaluation",
        "quality-gates",
        "digest",
        "deliver",
        "notifications-schedule",
        "notifications-scheduled",
        "notifications-immediate",
        "notifications-retry",
        "notifications-recover",
        "notifications-cleanup-deliveries",
        "notifications-cleanup",
        "cleanup-articles",
        "cleanup-digests",
    }
    assert set(task_options) == expected_tasks


def test_staging_workflow_has_least_privilege_permissions() -> None:
    workflow = _load_workflow()
    permissions = workflow.get("permissions", {})
    assert permissions.get("contents") == "read"


def test_staging_workflow_uses_staging_concurrency_group() -> None:
    workflow = _load_workflow()
    job = workflow["jobs"]["staging-scheduled-task"]
    concurrency = job.get("concurrency", {})
    assert concurrency.get("group") == "staging-scheduler"
    assert concurrency.get("cancel-in-progress") is False


def test_staging_workflow_does_not_reuse_production_concurrency() -> None:
    workflow = _load_workflow()
    job = workflow["jobs"]["staging-scheduled-task"]
    concurrency = job.get("concurrency", {})
    assert concurrency.get("group") != "production-scheduler"


def test_staging_workflow_uses_staging_secrets() -> None:
    workflow = _load_workflow()
    job = workflow["jobs"]["staging-scheduled-task"]
    run_step = job["steps"][-1]
    env = run_step["env"]
    assert env.get("DATABASE_URL") == "${{ secrets.STAGING_DATABASE_URL }}"
    assert env.get("REDIS_URL") == "${{ secrets.STAGING_REDIS_URL }}"
    assert env.get("CELERY_BROKER_URL") == "${{ secrets.STAGING_CELERY_BROKER_URL }}"
    assert env.get("CELERY_RESULT_BACKEND") == "${{ secrets.STAGING_CELERY_RESULT_BACKEND }}"
    assert env.get("JWT_SECRET_KEY") == "${{ secrets.STAGING_JWT_SECRET_KEY }}"


def test_staging_workflow_does_not_reference_production_secrets() -> None:
    workflow_str = _WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "FREE_DATABASE_URL" not in workflow_str
    assert "FREE_REDIS_URL" not in workflow_str
    assert "FREE_CELERY_BROKER_URL" not in workflow_str
    assert "FREE_CELERY_RESULT_BACKEND" not in workflow_str
    assert "FREE_JWT_SECRET_KEY" not in workflow_str


def test_staging_workflow_hardcodes_staging_environment() -> None:
    workflow = _load_workflow()
    job = workflow["jobs"]["staging-scheduled-task"]
    run_step = job["steps"][-1]
    env = run_step["env"]
    assert env.get("ENVIRONMENT") == "staging"
    assert env.get("AI_ENABLED") == "false"
    assert env.get("EMAIL_ENABLED") == "false"
    assert env.get("EMAIL_PROVIDER") == "console"


def test_staging_workflow_does_not_enable_ai_or_email() -> None:
    workflow = _load_workflow()
    job = workflow["jobs"]["staging-scheduled-task"]
    run_step = job["steps"][-1]
    env = run_step["env"]
    assert "OPENAI_API_KEY" not in env
    assert "ANTHROPIC_API_KEY" not in env
    assert "SMTP_HOST" not in env
    assert "SMTP_USER" not in env
    assert "SMTP_PASSWORD" not in env


def test_staging_workflow_uses_fail_fast_bash() -> None:
    workflow = _load_workflow()
    job = workflow["jobs"]["staging-scheduled-task"]
    run_step = job["steps"][-1]
    assert "set -euo pipefail" in run_step["run"]


def test_staging_workflow_does_not_log_secrets() -> None:
    workflow = _load_workflow()
    job = workflow["jobs"]["staging-scheduled-task"]
    run_step = job["steps"][-1]
    script = run_step["run"]
    assert "DATABASE_URL" not in script
    assert "REDIS_URL" not in script
    assert "CELERY_BROKER_URL" not in script
    assert "CELERY_RESULT_BACKEND" not in script
    assert "JWT_SECRET_KEY" not in script


def test_staging_workflow_has_no_secret_values_in_yaml() -> None:
    workflow_str = _WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "postgresql://" not in workflow_str
    assert "redis://" not in workflow_str
    assert "password" not in workflow_str.lower() or "secrets." in workflow_str


def test_staging_workflow_job_has_bounded_timeout() -> None:
    workflow = _load_workflow()
    job = workflow["jobs"]["staging-scheduled-task"]
    timeout = job.get("timeout-minutes")
    assert timeout is not None
    assert 10 <= timeout <= 120
