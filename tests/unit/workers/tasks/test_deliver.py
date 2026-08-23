"""
Unit tests for ``workers/tasks/deliver.py``.

The email delivery use case is patched so no real rendering or email
delivery occurs during the tests.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
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

    result = await deliver.send_digest_email(digest.id)

    assert result["status"] == "completed"
    usecase.execute.assert_awaited_once_with(digest.id)


async def test_send_digest_email_not_found(monkeypatch):
    """An unknown digest id returns not_found."""
    digest_id = uuid4()

    mock_container = MagicMock()
    mock_container.deliver_digest = MagicMock()
    mock_container.deliver_digest.execute.side_effect = ResourceNotFoundError(
        f"Digest with id '{digest_id}' was not found."
    )
    monkeypatch.setattr(deliver, "get_container", container_generator(mock_container))

    with pytest.raises(ResourceNotFoundError):
        await deliver.send_digest_email(digest_id)


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

    with pytest.raises(RuntimeError, match="SMTP auth failed"):
        await deliver.send_digest_email(digest.id)


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

    result = await deliver.send_latest_digest()
    assert result["status"] == "completed"
    mock_container.digest_repository.list_recent.assert_awaited_once_with(limit=1)
    usecase.execute.assert_awaited_once_with(digest.id)


async def test_send_latest_digest_no_digests(monkeypatch):
    """When no digests exist the task returns no_digests."""
    mock_container = MagicMock()
    mock_container.digest_repository = AsyncMock()
    mock_container.digest_repository.list_recent.return_value = []
    monkeypatch.setattr(deliver, "get_container", container_generator(mock_container))

    result = await deliver.send_latest_digest()
    assert result["status"] == "no_digests"


# ----------------------------------------------------------------------
# Registration
# ----------------------------------------------------------------------


def test_deliver_task_registration() -> None:
    """Both deliver tasks are registered with the expected names."""
    assert deliver.send_digest_email.name == "workers.tasks.deliver.send_digest_email"
    assert deliver.send_latest_digest.name == "workers.tasks.deliver.send_latest_digest"

    assert deliver.send_digest_email.name in celery_app.tasks
    assert deliver.send_digest_email.max_retries == 3
    assert deliver.send_digest_email.default_retry_delay == 300

    assert deliver.send_latest_digest.name in celery_app.tasks
    assert deliver.send_latest_digest.max_retries == 3
    assert deliver.send_latest_digest.default_retry_delay == 300


__all__ = [
    "test_deliver_task_registration",
    "test_send_digest_email_completed",
    "test_send_digest_email_not_found",
    "test_send_digest_email_system_error",
    "test_send_latest_digest_completed",
    "test_send_latest_digest_no_digests",
]
