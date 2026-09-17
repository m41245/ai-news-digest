"""
Regression and validation tests for the GitHub Actions scheduled workflow.

Verifies:
- schedule triggers are prepared with correct cron expressions
- workflow_dispatch is preserved
- concurrency and timeout are configured
- AI and email are explicitly disabled
- production secrets are handled safely
- no unnecessary secrets are exposed
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


def test_github_actions_workflow_has_schedule_triggers() -> None:
    """The workflow must contain ``on.schedule`` triggers prepared for production."""
    assert _WORKFLOW_PATH.exists(), f"Workflow file not found at {_WORKFLOW_PATH}"

    workflow = yaml.safe_load(_WORKFLOW_PATH.read_text(encoding="utf-8"))
    triggers = workflow.get("on") or workflow.get(True) or {}
    assert triggers, "Workflow is missing the 'on' trigger block"
    assert "schedule" in triggers, (
        "GitHub Actions workflow must contain 'on.schedule' triggers for production scheduling."
    )
    assert "workflow_dispatch" in triggers, (
        "GitHub Actions workflow must retain 'workflow_dispatch' for manual/on-demand execution."
    )


def test_github_actions_workflow_schedule_has_expected_cron_count() -> None:
    """The schedule block must contain the expected number of cron entries."""
    workflow = yaml.safe_load(_WORKFLOW_PATH.read_text(encoding="utf-8"))
    triggers = workflow.get("on") or workflow.get(True) or {}
    schedule_entries = triggers.get("schedule", [])
    assert len(schedule_entries) >= 10, (
        f"Expected at least 10 schedule entries, got {len(schedule_entries)}"
    )


def test_github_actions_workflow_has_concurrency() -> None:
    """The scheduled job must have concurrency protection."""
    workflow = yaml.safe_load(_WORKFLOW_PATH.read_text(encoding="utf-8"))
    job = workflow["jobs"]["scheduled-task"]
    assert "concurrency" in job, "Job must have concurrency configuration"
    concurrency = job["concurrency"]
    assert "group" in concurrency, "Concurrency must have a group"
    assert concurrency.get("cancel-in-progress") is False, (
        "cancel-in-progress must be false to avoid unsafe cancellation"
    )


def test_github_actions_workflow_has_timeout() -> None:
    """The scheduled job must have a bounded timeout."""
    workflow = yaml.safe_load(_WORKFLOW_PATH.read_text(encoding="utf-8"))
    job = workflow["jobs"]["scheduled-task"]
    timeout = job.get("timeout-minutes")
    assert timeout is not None, "Job must have a timeout"
    assert 10 <= timeout <= 120, f"Timeout must be between 10 and 120 minutes, got {timeout}"


def test_github_actions_workflow_has_least_privilege_permissions() -> None:
    """The workflow must not request write permissions."""
    workflow = yaml.safe_load(_WORKFLOW_PATH.read_text(encoding="utf-8"))
    permissions = workflow.get("permissions", {})
    assert permissions.get("contents") == "read", (
        "Workflow must have contents: read permission"
    )


def test_github_actions_workflow_ai_disabled() -> None:
    """The workflow must explicitly disable AI."""
    workflow = yaml.safe_load(_WORKFLOW_PATH.read_text(encoding="utf-8"))
    job = workflow["jobs"]["scheduled-task"]
    env = job["steps"][-1]["env"]
    assert env.get("AI_ENABLED") == "false", "AI_ENABLED must be explicitly false"


def test_github_actions_workflow_email_disabled() -> None:
    """The workflow must explicitly disable email."""
    workflow = yaml.safe_load(_WORKFLOW_PATH.read_text(encoding="utf-8"))
    job = workflow["jobs"]["scheduled-task"]
    env = job["steps"][-1]["env"]
    assert env.get("EMAIL_ENABLED") == "false", "EMAIL_ENABLED must be explicitly false"
    assert env.get("EMAIL_DEVELOPMENT_MODE") == "false", (
        "EMAIL_DEVELOPMENT_MODE must be explicitly false"
    )


def test_github_actions_workflow_no_unnecessary_secrets() -> None:
    """The workflow must not pass AI or SMTP secrets when they are disabled."""
    workflow = yaml.safe_load(_WORKFLOW_PATH.read_text(encoding="utf-8"))
    job = workflow["jobs"]["scheduled-task"]
    env = job["steps"][-1]["env"]
    assert "OPENAI_API_KEY" not in env, "OPENAI_API_KEY must not be passed when AI is disabled"
    assert "ANTHROPIC_API_KEY" not in env, (
        "ANTHROPIC_API_KEY must not be passed when AI is disabled"
    )
    assert "SMTP_HOST" not in env, "SMTP_HOST must not be passed when email is disabled"
    assert "SMTP_USER" not in env, "SMTP_USER must not be passed when email is disabled"
    assert "SMTP_PASSWORD" not in env, "SMTP_PASSWORD must not be passed when email is disabled"


def test_github_actions_workflow_preserves_manual_task_choices() -> None:
    """The workflow must retain all existing manual task choices."""
    workflow = yaml.safe_load(_WORKFLOW_PATH.read_text(encoding="utf-8"))
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
    assert set(task_options) == expected_tasks, (
        f"Task options mismatch. Expected {expected_tasks}, got {set(task_options)}"
    )


def test_github_actions_workflow_has_no_misleading_environment_input() -> None:
    """The workflow must not have a misleading environment selector that is never used."""
    workflow = yaml.safe_load(_WORKFLOW_PATH.read_text(encoding="utf-8"))
    triggers = workflow.get("on") or workflow.get(True) or {}
    dispatch = triggers.get("workflow_dispatch", {})
    assert "environment" not in dispatch.get("inputs", {}), (
        "Workflow must not have an environment input that is never used"
    )


def test_github_actions_workflow_has_fail_fast_bash() -> None:
    """The run step must use set -euo pipefail for fail-fast behavior."""
    workflow = yaml.safe_load(_WORKFLOW_PATH.read_text(encoding="utf-8"))
    job = workflow["jobs"]["scheduled-task"]
    run_step = job["steps"][-1]
    run_script = run_step["run"]
    assert "set -euo pipefail" in run_script, (
        "Run script must use 'set -euo pipefail' for fail-fast behavior"
    )


def test_github_actions_workflow_schedule_task_default() -> None:
    """The default task for schedule runs must be the morning pipeline."""
    workflow = yaml.safe_load(_WORKFLOW_PATH.read_text(encoding="utf-8"))
    job = workflow["jobs"]["scheduled-task"]
    run_step = job["steps"][-1]
    run_script = run_step["run"]
    assert 'github.event_name' in run_script, (
        "Run script must distinguish between schedule and workflow_dispatch"
    )
    assert "ingest" in run_script, "Morning pipeline must start with ingest"
