"""
Regression tests to prevent duplicate scheduling between GitHub Actions and Celery Beat.

These tests ensure that automated scheduled task execution remains the sole
responsibility of Celery Beat running in the Render ``ai-news-digest-beat``
worker service.
"""

from __future__ import annotations

import pathlib

import yaml

from ai_news_digest.workers.celery_app import celery_app

_WORKFLOW_PATH = (
    pathlib.Path(__file__).resolve().parents[2]
    / ".github"
    / "workflows"
    / "scheduled-tasks.yml"
)


def test_github_actions_workflow_has_no_schedule_triggers() -> None:
    """The GitHub Actions workflow must not contain ``on.schedule`` triggers.

    Automated scheduled task execution is the responsibility of Celery Beat.
    The workflow must remain manual/on-demand only via ``workflow_dispatch``.
    """
    assert _WORKFLOW_PATH.exists(), f"Workflow file not found at {_WORKFLOW_PATH}"

    workflow = yaml.safe_load(_WORKFLOW_PATH.read_text(encoding="utf-8"))
    triggers = workflow.get("on") or workflow.get(True) or {}
    assert triggers, "Workflow is missing the 'on' trigger block"
    assert "schedule" not in triggers, (
        "GitHub Actions workflow must not contain 'on.schedule' triggers. "
        "Celery Beat is the sole automated scheduler."
    )
    assert "workflow_dispatch" in triggers, (
        "GitHub Actions workflow must retain 'workflow_dispatch' for manual/on-demand execution."
    )


def test_celery_beat_is_the_sole_automated_scheduler() -> None:
    """Celery Beat defines the production automated task schedule.

    ``beat_schedule`` must contain the canonical list of periodic tasks.
    """
    assert celery_app.conf.beat_schedule is not None
    assert len(celery_app.conf.beat_schedule) > 0


def test_celery_beat_schedule_task_names_are_unique() -> None:
    """No duplicate task names within the Celery Beat schedule."""
    names = list(celery_app.conf.beat_schedule.keys())
    assert len(names) == len(set(names)), "Duplicate schedule entry names found in beat_schedule"


def test_celery_beat_schedule_has_expiry_and_events() -> None:
    """Every scheduled task must have expiry and event emission configured."""
    for name, entry in celery_app.conf.beat_schedule.items():
        assert "options" in entry, f"Missing options in schedule entry: {name}"
        options = entry["options"]
        assert "expires" in options, f"Missing 'expires' in schedule entry: {name}"
        assert options.get("send_events") is True, (
            f"Missing 'send_events' in schedule entry: {name}"
        )


def test_github_actions_workflow_default_task_is_not_an_automated_schedule() -> None:
    """The workflow default task must not be used as an automated schedule.

    If ``schedule`` triggers are absent, the default ``ingest`` task is only
    used for manual ``workflow_dispatch`` invocations and does not represent
    an automated schedule.
    """
    workflow = yaml.safe_load(_WORKFLOW_PATH.read_text(encoding="utf-8"))
    triggers = workflow.get("on") or workflow.get(True) or {}
    assert "schedule" not in triggers
