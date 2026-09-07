"""Tests for celery app timezone configuration."""

from __future__ import annotations

from ai_news_digest.workers.celery_app import celery_app


def test_celery_app_timezone_is_configurable() -> None:
    """Celery app picks up the configured timezone."""
    assert celery_app.conf.timezone is not None


def test_celery_app_default_timezone_is_utc() -> None:
    """The default timezone (no env override) is UTC."""
    assert celery_app.conf.timezone == "UTC"


def test_beat_schedule_present() -> None:
    schedule = celery_app.conf.beat_schedule
    assert "daily-digest-generation" in schedule
    assert "daily-rss-ingestion" in schedule
    assert "daily-article-summarization" in schedule
    assert "daily-article-categorization" in schedule
    assert "daily-email-delivery" in schedule
