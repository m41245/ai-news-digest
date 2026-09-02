"""
Unit tests for ``workers/tasks/deliver.py``.

The email delivery use case is patched so no real rendering or email
delivery occurs during the tests.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from ai_news_digest.core.exceptions import ResourceNotFoundError
from ai_news_digest.workers.celery_app import celery_app
from ai_news_digest.workers.tasks import deliver
from tests.unit.workers.tasks.conftest import (
    container_generator,
    make_digest,
)


def _patch_deliver_usecase(monkeypatch, summary=None):
    """Patch the deliver_digest use case in the container."""
    if summary is None:
        from ai_news_digest.application.use_cases.delivery.deliver_digest import DeliverySummary

        summary = DeliverySummary(
            digest_id=uuid4(),
            total_recipients=1,
            sent_count=1,
            failed_count=0,
            skipped_count=0,
            results=[],
        )

    usecase = MagicMock()
    usecase.execute = AsyncMock(return_value=summary)

    mock_container = MagicMock()
    mock_container.deliver_digest = usecase

    monkeypatch.setattr(deliver, "get_container", container_generator(mock_container))
    return usecase


# ----------------------------------------------------------------------
# send_digest_email
# ----------------------------------------------------------------------


async def test_send_digest_email_completed(monkeypatch):
    """A known digest is delivered via the use case."""
    digest = make_digest()
    usecase = _patch_deliver_usecase(
        monkeypatch,
        summary=MagicMock(
            digest_id=digest.id,
            sent_count=1,
            failed_count=0,
            skipped_count=0,
            has_system_error=False,
        ),
    )

    with (
        patch.object(deliver, "record_celery_task_success") as mock_success,
        patch.object(deliver, "record_celery_task_failure") as mock_failure,
        patch.object(deliver, "record_celery_task_duration") as mock_duration,
        patch.object(deliver, "record_email_delivery_success") as mock_email_success,
        patch.object(deliver, "record_email_delivery_failure") as mock_email_failure,
    ):
        result = await deliver.send_digest_email(digest.id)

    assert result["status"] == "completed"
    usecase.execute.assert_awaited_once_with(digest.id)
    mock_success.assert_awaited_once_with(deliver._TASK_NAME_SEND_EMAIL)
    mock_failure.assert_not_awaited()
    mock_email_success.assert_called_once_with(1)
    mock_email_failure.assert_not_called()
    mock_duration.assert_awaited_once()


async def test_send_digest_email_not_found(monkeypatch):
    """An unknown digest id returns not_found."""
    digest_id = uuid4()

    mock_container = MagicMock()
    mock_container.deliver_digest = MagicMock()
    mock_container.deliver_digest.execute.side_effect = ResourceNotFoundError(
        f"Digest with id '{digest_id}' was not found."
    )
    monkeypatch.setattr(deliver, "get_container", container_generator(mock_container))

    with (
        patch.object(deliver, "record_celery_task_success") as mock_success,
        patch.object(deliver, "record_celery_task_failure") as mock_failure,
        patch.object(deliver, "record_celery_task_duration") as mock_duration,
        patch.object(deliver, "record_email_delivery_success") as mock_email_success,
        patch.object(deliver, "record_email_delivery_failure") as mock_email_failure,
        pytest.raises(ResourceNotFoundError),
    ):
        await deliver.send_digest_email(digest_id)

    mock_success.assert_not_awaited()
    mock_failure.assert_awaited_once_with(deliver._TASK_NAME_SEND_EMAIL)
    mock_email_success.assert_not_called()
    mock_email_failure.assert_called_once_with(1)
    mock_duration.assert_awaited_once()


async def test_send_digest_email_system_error(monkeypatch):
    """A system error is re-raised by the task wrapper."""
    digest = make_digest()

    from ai_news_digest.application.use_cases.delivery.deliver_digest import DeliverySummary

    summary = DeliverySummary(
        digest_id=digest.id,
        total_recipients=1,
        sent_count=0,
        failed_count=1,
        skipped_count=0,
        results=[],
        has_system_error=True,
        system_error="SMTP auth failed",
    )
    _patch_deliver_usecase(monkeypatch, summary=summary)

    with (
        patch.object(deliver, "record_celery_task_success") as mock_success,
        patch.object(deliver, "record_celery_task_failure") as mock_failure,
        patch.object(deliver, "record_celery_task_duration") as mock_duration,
        patch.object(deliver, "record_email_delivery_success") as mock_email_success,
        patch.object(deliver, "record_email_delivery_failure") as mock_email_failure,
        pytest.raises(RuntimeError, match="SMTP auth failed"),
    ):
        await deliver.send_digest_email(digest.id)

    mock_success.assert_not_awaited()
    mock_failure.assert_awaited_once_with(deliver._TASK_NAME_SEND_EMAIL)
    mock_email_success.assert_not_called()
    mock_email_failure.assert_called_once_with(1)
    mock_duration.assert_awaited_once()


# ----------------------------------------------------------------------
# send_latest_digest
# ----------------------------------------------------------------------


async def test_send_latest_digest_completed(monkeypatch):
    """The most recent digest is delivered when one exists."""
    digest = make_digest()
    mock_container = MagicMock()
    mock_container.digest_repository = AsyncMock()
    mock_container.digest_repository.list_recent.return_value = [digest]

    from ai_news_digest.application.use_cases.delivery.deliver_digest import DeliverySummary

    summary = DeliverySummary(
        digest_id=digest.id,
        total_recipients=1,
        sent_count=1,
        failed_count=0,
        skipped_count=0,
        results=[],
    )
    usecase = MagicMock()
    usecase.execute = AsyncMock(return_value=summary)
    mock_container.deliver_digest = usecase

    monkeypatch.setattr(deliver, "get_container", container_generator(mock_container))

    with (
        patch.object(deliver, "record_celery_task_success") as mock_success,
        patch.object(deliver, "record_celery_task_failure") as mock_failure,
        patch.object(deliver, "record_celery_task_duration") as mock_duration,
        patch.object(deliver, "record_email_delivery_success") as mock_email_success,
        patch.object(deliver, "record_email_delivery_failure") as mock_email_failure,
    ):
        result = await deliver.send_latest_digest()

    assert result["status"] == "completed"
    mock_container.digest_repository.list_recent.assert_awaited_once_with(limit=1)
    usecase.execute.assert_awaited_once_with(digest.id)
    mock_success.assert_awaited_once_with(deliver._TASK_NAME_SEND_LATEST)
    mock_failure.assert_not_awaited()
    mock_email_success.assert_called_once_with(1)
    mock_email_failure.assert_not_called()
    mock_duration.assert_awaited_once()


async def test_send_latest_digest_no_digests(monkeypatch):
    """When no digests exist the task returns no_digests."""
    mock_container = MagicMock()
    mock_container.digest_repository = AsyncMock()
    mock_container.digest_repository.list_recent.return_value = []
    monkeypatch.setattr(deliver, "get_container", container_generator(mock_container))

    with (
        patch.object(deliver, "record_celery_task_success") as mock_success,
        patch.object(deliver, "record_celery_task_failure") as mock_failure,
        patch.object(deliver, "record_celery_task_duration") as mock_duration,
        patch.object(deliver, "record_email_delivery_success") as mock_email_success,
        patch.object(deliver, "record_email_delivery_failure") as mock_email_failure,
    ):
        result = await deliver.send_latest_digest()

    assert result["status"] == "no_digests"
    mock_success.assert_awaited_once_with(deliver._TASK_NAME_SEND_LATEST)
    mock_failure.assert_not_awaited()
    mock_email_success.assert_not_called()
    mock_email_failure.assert_not_called()
    mock_duration.assert_awaited_once()


# ----------------------------------------------------------------------
# Regression tests for dead "skipped" branch removal (M-4)
# ----------------------------------------------------------------------


async def test_send_digest_email_not_found_treated_as_failure(monkeypatch):
    """A 'not_found' status must record a failure, not be silently skipped."""
    digest_id = uuid4()

    mock_container = MagicMock()
    mock_container.deliver_digest = MagicMock()
    mock_container.deliver_digest.execute.side_effect = ResourceNotFoundError(
        f"Digest with id '{digest_id}' was not found."
    )
    monkeypatch.setattr(deliver, "get_container", container_generator(mock_container))

    with (
        patch.object(deliver, "record_celery_task_success"),
        patch.object(deliver, "record_celery_task_failure"),
        patch.object(deliver, "record_celery_task_duration"),
        patch.object(deliver, "record_email_delivery_success") as mock_email_success,
        patch.object(deliver, "record_email_delivery_failure") as mock_email_failure,
        pytest.raises(ResourceNotFoundError),
    ):
        await deliver.send_digest_email(digest_id)

    mock_email_failure.assert_called_once_with(1)
    mock_email_success.assert_not_called()


async def test_send_latest_digest_not_found_treated_as_failure(monkeypatch):
    """A ResourceNotFoundError during latest-digest delivery records failure and re-raises."""
    latest_digest = make_digest()
    mock_container = MagicMock()
    mock_container.digest_repository = AsyncMock()
    mock_container.digest_repository.list_recent.return_value = [latest_digest]

    mock_container.deliver_digest = MagicMock()
    mock_container.deliver_digest.execute.side_effect = ResourceNotFoundError("not found")
    monkeypatch.setattr(deliver, "get_container", container_generator(mock_container))

    with (
        patch.object(deliver, "record_celery_task_success"),
        patch.object(deliver, "record_celery_task_failure"),
        patch.object(deliver, "record_celery_task_duration"),
        patch.object(deliver, "record_email_delivery_success") as mock_email_success,
        patch.object(deliver, "record_email_delivery_failure") as mock_email_failure,
        pytest.raises(ResourceNotFoundError),
    ):
        await deliver.send_latest_digest()

    mock_email_failure.assert_called_once_with(1)
    mock_email_success.assert_not_called()


# ----------------------------------------------------------------------
# Registration
# ----------------------------------------------------------------------


def test_deliver_task_registration() -> None:
    """Both deliver tasks are registered with the expected names."""
    assert deliver.send_digest_email.name == "workers.tasks.deliver.send_digest_email"
    assert deliver.send_latest_digest.name == "workers.tasks.deliver.send_latest_digest"

    assert deliver.send_digest_email.name in celery_app.tasks
    assert deliver.send_digest_email.max_retries == 3
    assert deliver.send_digest_email.default_retry_delay == 60

    assert deliver.send_latest_digest.name in celery_app.tasks
    assert deliver.send_latest_digest.max_retries == 3
    assert deliver.send_latest_digest.default_retry_delay == 60


__all__ = [
    "test_deliver_task_registration",
    "test_send_digest_email_completed",
    "test_send_digest_email_not_found",
    "test_send_digest_email_not_found_treated_as_failure",
    "test_send_digest_email_system_error",
    "test_send_latest_digest_completed",
    "test_send_latest_digest_no_digests",
    "test_send_latest_digest_not_found_treated_as_failure",
]
