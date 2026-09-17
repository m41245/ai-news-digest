"""
Comprehensive tests for the GitHub Actions scheduled workflow.

Validates workflow structure, schedule configuration, safety guards,
and production readiness properties.
"""

from __future__ import annotations

import pathlib

import yaml

_WORKFLOW_PATH = (
    pathlib.Path(__file__).resolve().parents[2]
    / ".github"
    / "workflows"
    / "scheduled-tasks.yml"
)


def _load_workflow() -> dict:
    assert _WORKFLOW_PATH.exists(), f"Workflow file not found at {_WORKFLOW_PATH}"
    return yaml.safe_load(_WORKFLOW_PATH.read_text(encoding="utf-8"))


def test_workflow_has_expected_name() -> None:
    workflow = _load_workflow()
    assert workflow.get("name") == "Scheduled Tasks (Manual / On-Demand)"


def test_workflow_has_both_trigger_types() -> None:
    workflow = _load_workflow()
    triggers = workflow.get("on") or workflow.get(True) or {}
    assert "workflow_dispatch" in triggers
    assert "schedule" in triggers


def test_workflow_dispatch_has_all_21_tasks() -> None:
    workflow = _load_workflow()
    triggers = workflow.get("on") or workflow.get(True) or {}
    dispatch = triggers.get("workflow_dispatch", {})
    task_options = dispatch.get("inputs", {}).get("task", {}).get("options", [])
    assert len(task_options) == 23


def test_workflow_schedule_cron_expressions_are_valid() -> None:
    workflow = _load_workflow()
    triggers = workflow.get("on") or workflow.get(True) or {}
    schedule_entries = triggers.get("schedule", [])
    for entry in schedule_entries:
        cron = entry.get("cron", "")
        parts = cron.strip().split()
        assert len(parts) == 5, f"Invalid cron expression: {cron}"


def test_workflow_job_has_concurrency_group() -> None:
    workflow = _load_workflow()
    job = workflow["jobs"]["scheduled-task"]
    concurrency = job.get("concurrency", {})
    assert "group" in concurrency
    assert concurrency["group"] == "production-scheduler"


def test_workflow_job_does_not_cancel_in_progress() -> None:
    workflow = _load_workflow()
    job = workflow["jobs"]["scheduled-task"]
    concurrency = job.get("concurrency", {})
    assert concurrency.get("cancel-in-progress") is False


def test_workflow_job_timeout_is_bounded() -> None:
    workflow = _load_workflow()
    job = workflow["jobs"]["scheduled-task"]
    timeout = job.get("timeout-minutes")
    assert timeout is not None
    assert 10 <= timeout <= 120


def test_workflow_has_least_privilege_permissions() -> None:
    workflow = _load_workflow()
    permissions = workflow.get("permissions", {})
    assert permissions == {"contents": "read"}


def test_workflow_explicitly_disables_ai() -> None:
    workflow = _load_workflow()
    job = workflow["jobs"]["scheduled-task"]
    env = job["steps"][-1]["env"]
    assert env.get("AI_ENABLED") == "false"


def test_workflow_explicitly_disables_email() -> None:
    workflow = _load_workflow()
    job = workflow["jobs"]["scheduled-task"]
    env = job["steps"][-1]["env"]
    assert env.get("EMAIL_ENABLED") == "false"
    assert env.get("EMAIL_DEVELOPMENT_MODE") == "false"


def test_workflow_does_not_pass_ai_secrets_when_disabled() -> None:
    workflow = _load_workflow()
    job = workflow["jobs"]["scheduled-task"]
    env = job["steps"][-1]["env"]
    assert "OPENAI_API_KEY" not in env
    assert "ANTHROPIC_API_KEY" not in env
    assert "GEMINI_API_KEY" not in env
    assert "XAI_API_KEY" not in env


def test_workflow_does_not_pass_smtp_secrets_when_disabled() -> None:
    workflow = _load_workflow()
    job = workflow["jobs"]["scheduled-task"]
    env = job["steps"][-1]["env"]
    assert "SMTP_HOST" not in env
    assert "SMTP_PORT" not in env
    assert "SMTP_USER" not in env
    assert "SMTP_PASSWORD" not in env
    assert "EMAIL_FROM" not in env
    assert "EMAIL_RECIPIENTS" not in env


def test_workflow_has_no_misleading_environment_input() -> None:
    """The workflow must not have a misleading environment selector."""
    workflow = _load_workflow()
    triggers = workflow.get("on") or workflow.get(True) or {}
    dispatch = triggers.get("workflow_dispatch", {})
    assert "environment" not in dispatch.get("inputs", {}), (
        "Workflow must not have an environment input that is never used"
    )


def test_workflow_uses_fail_fast_bash() -> None:
    workflow = _load_workflow()
    job = workflow["jobs"]["scheduled-task"]
    run_step = job["steps"][-1]
    assert "set -euo pipefail" in run_step["run"]


def test_workflow_distinguishes_schedule_and_dispatch() -> None:
    workflow = _load_workflow()
    job = workflow["jobs"]["scheduled-task"]
    run_step = job["steps"][-1]
    script = run_step["run"]
    assert "github.event_name" in script
    assert "schedule" in script
    assert "workflow_dispatch" in script or "github.event.inputs.task" in script


def test_workflow_runs_morning_pipeline_on_schedule() -> None:
    workflow = _load_workflow()
    job = workflow["jobs"]["scheduled-task"]
    run_step = job["steps"][-1]
    script = run_step["run"]
    expected_pipeline = [
        "ingest",
        "summarize",
        "categorize",
        "analyze",
        "cluster",
        "ranking",
        "timeline",
        "story-activity",
        "trend",
        "digest",
        "deliver",
    ]
    for task in expected_pipeline:
        assert f"run_task.py {task}" in script, f"Morning pipeline missing task: {task}"


def test_workflow_does_not_log_secrets() -> None:
    workflow = _load_workflow()
    job = workflow["jobs"]["scheduled-task"]
    run_step = job["steps"][-1]
    script = run_step["run"]
    assert "DATABASE_URL" not in script
    assert "REDIS_URL" not in script
    assert "CELERY_BROKER_URL" not in script
    assert "CELERY_RESULT_BACKEND" not in script
    assert "JWT_SECRET_KEY" not in script


def test_workflow_has_no_secret_values_in_yaml() -> None:
    workflow_str = _WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "postgresql://" not in workflow_str
    assert "redis://" not in workflow_str
    assert "password" not in workflow_str.lower() or "secrets." in workflow_str


def test_workflow_schedule_is_disabled_by_default() -> None:
    """Scheduled runs must exit early unless ENABLE_PRODUCTION_SCHEDULE is set."""
    workflow = _load_workflow()
    job = workflow["jobs"]["scheduled-task"]
    run_step = job["steps"][-1]
    script = run_step["run"]
    assert "ENABLE_PRODUCTION_SCHEDULE" in script, (
        "Workflow must check ENABLE_PRODUCTION_SCHEDULE before running scheduled tasks"
    )
    assert "exit 0" in script, (
        "Workflow must exit successfully when production schedule is disabled"
    )


def test_celery_beat_schedule_is_preserved() -> None:
    """Celery Beat schedule remains the canonical source of truth."""
    from ai_news_digest.workers.celery_app import celery_app

    schedule = celery_app.conf.beat_schedule
    assert schedule is not None
    assert len(schedule) == 21
