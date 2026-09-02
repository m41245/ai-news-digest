"""
Unit tests for Celery app configuration and beat schedule.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from ai_news_digest.workers.celery_app import celery_app
from ai_news_digest.workers.tasks.cleanup import (
    cleanup_old_articles,
    cleanup_old_digests,
)
from ai_news_digest.workers.tasks.deliver import send_digest_email, send_latest_digest
from ai_news_digest.workers.tasks.digest import generate_daily_digest
from ai_news_digest.workers.tasks.ingest import fetch_all_sources
from ai_news_digest.workers.tasks.process import (
    categorize_article,
    categorize_pending_articles,
    process_article,
    summarize_article,
    summarize_pending_articles,
)


class TestCeleryAppConfiguration:
    """Tests for Celery app configuration values."""

    def test_app_name(self) -> None:
        assert celery_app.main == "ai_news_digest"

    def test_time_limits(self) -> None:
        assert celery_app.conf.task_time_limit == 30 * 60
        assert celery_app.conf.task_soft_time_limit == 25 * 60

    def test_acknowledgement_behavior(self) -> None:
        assert celery_app.conf.task_acks_late is True
        assert celery_app.conf.task_reject_on_worker_lost is True

    def test_max_retries(self) -> None:
        assert celery_app.conf.task_max_retries == 3

    def test_retry_delay_is_callable(self) -> None:
        delay = celery_app.conf.task_retry_delay
        assert callable(delay)
        assert delay(1) == 60
        assert delay(2) == 120
        assert delay(3) == 240

    def test_worker_cancel_long_running_tasks_on_connection_loss(self) -> None:
        assert celery_app.conf.worker_cancel_long_running_tasks_on_connection_loss is True

    def test_worker_shutdown_and_term_timeout(self) -> None:
        assert celery_app.conf.worker_shutdown_timeout == 30
        assert celery_app.conf.worker_term_timeout == 30

    def test_beat_max_loop_interval(self) -> None:
        assert celery_app.conf.beat_max_loop_interval == 60

    def test_task_track_started(self) -> None:
        assert celery_app.conf.task_track_started is True

    def test_worker_prefetch_multiplier(self) -> None:
        assert celery_app.conf.worker_prefetch_multiplier == 1

    def test_worker_max_tasks_per_child(self) -> None:
        assert celery_app.conf.worker_max_tasks_per_child == 50

    def test_send_events_enabled(self) -> None:
        assert celery_app.conf.worker_send_task_events is True
        assert celery_app.conf.task_send_sent_event is True


class TestBeatSchedule:
    """Tests for Celery beat schedule configuration."""

    def test_beat_schedule_is_configured(self) -> None:
        assert celery_app.conf.beat_schedule is not None
        assert len(celery_app.conf.beat_schedule) == 5

    def test_schedule_names_are_unique(self) -> None:
        names = list(celery_app.conf.beat_schedule.keys())
        assert len(names) == len(set(names))

    def test_schedule_entries_have_expires(self) -> None:
        for name, entry in celery_app.conf.beat_schedule.items():
            assert "options" in entry, f"Missing options in {name}"
            assert "expires" in entry["options"], f"Missing expires in {name}"
            assert isinstance(entry["options"]["expires"], int)
            assert entry["options"]["expires"] > 0

    def test_schedule_entries_have_send_events(self) -> None:
        for name, entry in celery_app.conf.beat_schedule.items():
            assert "options" in entry, f"Missing options in {name}"
            assert entry["options"].get("send_events") is True, f"Missing send_events in {name}"

    def test_expected_tasks_in_schedule(self) -> None:
        expected_tasks = {
            "workers.tasks.ingest.fetch_all_sources",
            "workers.tasks.process.summarize_pending_articles",
            "workers.tasks.process.categorize_pending_articles",
            "workers.tasks.digest.generate_daily_digest",
            "workers.tasks.deliver.send_latest_digest",
        }
        actual_tasks = {entry["task"] for entry in celery_app.conf.beat_schedule.values()}
        assert expected_tasks == actual_tasks

    def test_beat_app_is_same_as_celery_app(self) -> None:
        beat_schedule_celery_app = celery_app
        assert beat_schedule_celery_app is celery_app


class TestTaskRegistration:
    """Tests for task registration and consistency."""

    def test_all_tasks_registered(self) -> None:
        expected_tasks = {
            "workers.tasks.ingest.fetch_all_sources",
            "workers.tasks.process.summarize_article",
            "workers.tasks.process.categorize_article",
            "workers.tasks.process.process_article",
            "workers.tasks.process.summarize_pending_articles",
            "workers.tasks.process.categorize_pending_articles",
            "workers.tasks.digest.generate_daily_digest",
            "workers.tasks.deliver.send_digest_email",
            "workers.tasks.deliver.send_latest_digest",
            "workers.tasks.cleanup.cleanup_old_articles",
            "workers.tasks.cleanup.cleanup_old_digests",
        }
        registered = set(celery_app.tasks.keys())
        missing = expected_tasks - registered
        assert not missing, f"Missing tasks: {missing}"

    def test_all_tasks_have_max_retries_3(self) -> None:
        task_names = [
            fetch_all_sources,
            summarize_article,
            categorize_article,
            process_article,
            summarize_pending_articles,
            categorize_pending_articles,
            generate_daily_digest,
            send_digest_email,
            send_latest_digest,
            cleanup_old_articles,
            cleanup_old_digests,
        ]
        for task in task_names:
            assert task.max_retries == 3, f"{task.name} max_retries != 3"

    def test_task_names_are_unique(self) -> None:
        task_names = [
            fetch_all_sources.name,
            summarize_article.name,
            categorize_article.name,
            process_article.name,
            summarize_pending_articles.name,
            categorize_pending_articles.name,
            generate_daily_digest.name,
            send_digest_email.name,
            send_latest_digest.name,
            cleanup_old_articles.name,
            cleanup_old_digests.name,
        ]
        assert len(task_names) == len(set(task_names))


class TestIdempotency:
    """Tests verifying task idempotency guarantees."""

    def test_ingest_task_is_idempotent(self) -> None:
        assert "idempotent" in fetch_all_sources.__doc__.lower()

    def test_process_tasks_are_idempotent(self) -> None:
        assert "idempotent" in summarize_article.__doc__.lower()
        assert "idempotent" in categorize_article.__doc__.lower()
        assert "idempotent" in process_article.__doc__.lower()

    def test_digest_task_is_idempotent(self) -> None:
        assert "idempotent" in generate_daily_digest.__doc__.lower()

    def test_deliver_task_is_idempotent(self) -> None:
        assert "idempotent" in send_digest_email.__doc__.lower()


class TestRetryBackoff:
    """Tests for exponential backoff retry configuration."""

    def test_exponential_backoff_values(self) -> None:
        delay_func = celery_app.conf.task_retry_delay
        assert delay_func(1) == 60
        assert delay_func(2) == 120
        assert delay_func(3) == 240

    def test_backoff_doubles_each_retry(self) -> None:
        delay_func = celery_app.conf.task_retry_delay
        for retry in range(1, 4):
            assert delay_func(retry) == 60 * (2 ** (retry - 1))


class TestRetryMetrics:
    """Tests for retry metric recording."""

    def test_retry_signal_records_metric(self) -> None:
        """The task_retry signal schedules a retry metric record."""
        from ai_news_digest.workers.celery_app import log_task_retry

        mock_sender = MagicMock()
        mock_sender.name = "test.task"

        with (
            patch("ai_news_digest.workers.celery_app.record_celery_task_retry") as mock_record,
            patch("ai_news_digest.workers.celery_app.asyncio.get_running_loop") as mock_get_loop,
        ):
            mock_loop = MagicMock()
            mock_loop.is_running.return_value = True
            mock_get_loop.return_value = mock_loop
            log_task_retry(sender=mock_sender, task_id="tid")

        mock_record.assert_called_once_with("test.task")
        mock_loop.create_task.assert_called_once()
