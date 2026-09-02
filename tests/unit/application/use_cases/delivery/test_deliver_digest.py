"""Unit tests for DeliverDigestUseCase."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from ai_news_digest.application.use_cases.delivery.deliver_digest import (
    DeliverDigestUseCase,
)
from ai_news_digest.core.exceptions import ResourceNotFoundError
from ai_news_digest.domain.enums.delivery_status import DeliveryStatus
from ai_news_digest.domain.enums.digest_format import DigestFormat
from ai_news_digest.domain.models.digest import Digest
from ai_news_digest.domain.ports.digest_repository import DigestRepository
from ai_news_digest.infrastructure.email.composer import EmailComposer
from ai_news_digest.infrastructure.email.errors import (
    EmailAuthenticationError,
    EmailConfigurationError,
    EmailConnectionError,
    EmailError,
    EmailInvalidRecipientError,
    EmailPermanentFailureError,
    EmailRateLimitError,
    EmailTimeoutError,
)


def _make_digest() -> Digest:
    return Digest.create(
        title="Test Digest",
        content="Content.",
        digest_format=DigestFormat.MARKDOWN,
        article_ids=[],
    )


def _build_usecase(
    digest: Digest | None = None,
    recipients: list[str] | None = None,
    existing_deliveries: dict[str, MagicMock] | None = None,
) -> DeliverDigestUseCase:
    digest_repository = AsyncMock(spec=DigestRepository)
    if digest is not None:
        digest_repository.get_by_id.return_value = digest
    else:
        digest_repository.get_by_id.return_value = None

    delivery_repository = AsyncMock()
    email_sender = AsyncMock()
    email_composer = EmailComposer()

    effective_recipients = recipients if recipients is not None else ["a@b.com", "c@d.com"]

    if existing_deliveries is not None:

        def _get_existing(digest_id, recipient):
            return existing_deliveries.get(recipient)

        delivery_repository.get_by_digest_and_recipient.side_effect = _get_existing
    else:
        delivery_repository.get_by_digest_and_recipient.return_value = None

    return DeliverDigestUseCase(
        digest_repository=digest_repository,
        delivery_repository=delivery_repository,
        email_sender=email_sender,
        email_composer=email_composer,
        recipients=effective_recipients,
    )


@pytest.mark.asyncio
async def test_deliver_digest_not_found() -> None:
    use_case = _build_usecase(digest=None)
    with pytest.raises(ResourceNotFoundError):
        await use_case.execute(uuid4())


@pytest.mark.asyncio
async def test_deliver_digest_zero_recipients() -> None:
    use_case = _build_usecase(digest=_make_digest(), recipients=[])
    summary = await use_case.execute(uuid4())
    assert summary.total_recipients == 0
    assert summary.sent_count == 0


@pytest.mark.asyncio
async def test_deliver_digest_success() -> None:
    digest = _make_digest()
    use_case = _build_usecase(digest=digest, recipients=["a@b.com"])
    summary = await use_case.execute(digest.id)
    assert summary.sent_count == 1
    assert summary.failed_count == 0
    assert summary.skipped_count == 0


@pytest.mark.asyncio
async def test_deliver_digest_idempotent_skip_sent() -> None:
    digest = _make_digest()
    existing = MagicMock()
    existing.status = DeliveryStatus.SENT
    existing.recipient = "a@b.com"
    use_case = _build_usecase(
        digest=digest,
        recipients=["a@b.com"],
        existing_deliveries={"a@b.com": existing},
    )
    summary = await use_case.execute(digest.id)
    assert summary.skipped_count == 1
    assert summary.sent_count == 0


@pytest.mark.asyncio
async def test_deliver_digest_invalid_recipient_continues() -> None:
    digest = _make_digest()
    use_case = _build_usecase(digest=digest, recipients=["a@b.com", "c@d.com"])
    use_case._email_sender.send.side_effect = [
        EmailInvalidRecipientError("bad addr"),
        None,
    ]
    summary = await use_case.execute(digest.id)
    assert summary.sent_count == 1
    assert summary.failed_count == 1
    assert not summary.has_system_error


@pytest.mark.asyncio
async def test_deliver_digest_permanent_failure_continues() -> None:
    digest = _make_digest()
    use_case = _build_usecase(digest=digest, recipients=["a@b.com", "c@d.com"])
    use_case._email_sender.send.side_effect = [
        EmailPermanentFailureError("perm reject"),
        None,
    ]
    summary = await use_case.execute(digest.id)
    assert summary.sent_count == 1
    assert summary.failed_count == 1


@pytest.mark.asyncio
async def test_deliver_digest_auth_error_stops_and_reports() -> None:
    digest = _make_digest()
    use_case = _build_usecase(digest=digest, recipients=["a@b.com", "c@d.com"])
    use_case._email_sender.send.side_effect = EmailAuthenticationError("bad creds")

    mock_delivery = MagicMock()
    mock_delivery.status = DeliveryStatus.PENDING
    mock_delivery.recipient = "a@b.com"
    mock_delivery2 = MagicMock()
    mock_delivery2.status = DeliveryStatus.PENDING
    mock_delivery2.recipient = "c@d.com"
    use_case._delivery_repository.get_by_digest_and_recipient.return_value = None
    use_case._delivery_repository.create.side_effect = [mock_delivery, mock_delivery2]

    summary = await use_case.execute(digest.id)
    assert summary.has_system_error
    assert summary.system_error == "bad creds"
    assert summary.failed_count == 2


@pytest.mark.asyncio
async def test_deliver_digest_config_error_stops_and_reports() -> None:
    digest = _make_digest()
    use_case = _build_usecase(digest=digest, recipients=["a@b.com"])
    use_case._email_sender.send.side_effect = EmailConfigurationError("no host")
    summary = await use_case.execute(digest.id)
    assert summary.has_system_error
    assert summary.system_error == "no host"


@pytest.mark.asyncio
async def test_deliver_digest_transient_error_propagates() -> None:
    digest = _make_digest()
    use_case = _build_usecase(digest=digest, recipients=["a@b.com"])
    use_case._email_sender.send.side_effect = EmailConnectionError("conn reset")
    with pytest.raises(EmailError):
        await use_case.execute(digest.id)


@pytest.mark.asyncio
async def test_deliver_digest_timeout_error_propagates() -> None:
    digest = _make_digest()
    use_case = _build_usecase(digest=digest, recipients=["a@b.com"])
    use_case._email_sender.send.side_effect = EmailTimeoutError("timeout")
    with pytest.raises(EmailError):
        await use_case.execute(digest.id)


@pytest.mark.asyncio
async def test_deliver_digest_rate_limit_error_propagates() -> None:
    digest = _make_digest()
    use_case = _build_usecase(digest=digest, recipients=["a@b.com"])
    use_case._email_sender.send.side_effect = EmailRateLimitError("rate limited")
    with pytest.raises(EmailError):
        await use_case.execute(digest.id)


@pytest.mark.asyncio
async def test_deliver_digest_deduplicates_recipients() -> None:
    digest = _make_digest()
    use_case = _build_usecase(digest=digest, recipients=["a@b.com", "a@b.com", "c@d.com"])
    summary = await use_case.execute(digest.id)
    assert summary.total_recipients == 2


@pytest.mark.asyncio
async def test_ensure_deliveries_cleans_up_on_failure() -> None:
    digest = _make_digest()
    use_case = _build_usecase(digest=digest, recipients=["a@b.com", "c@d.com"])

    mock_delivery1 = MagicMock()
    mock_delivery1.id = uuid4()
    mock_delivery2 = MagicMock()
    mock_delivery2.id = uuid4()

    use_case._delivery_repository.get_by_digest_and_recipient.side_effect = [
        None,
        None,
    ]
    use_case._delivery_repository.create.side_effect = [
        mock_delivery1,
        RuntimeError("db failure"),
    ]

    with pytest.raises(RuntimeError, match="db failure"):
        await use_case.execute(digest.id)

    use_case._delivery_repository.delete.assert_awaited_once_with(mock_delivery1.id)


@pytest.mark.asyncio
async def test_auth_error_cleanup_continues_on_update_failure() -> None:
    digest = _make_digest()
    use_case = _build_usecase(digest=digest, recipients=["a@b.com", "c@d.com"])
    use_case._email_sender.send.side_effect = EmailAuthenticationError("bad creds")

    mock_delivery1 = MagicMock()
    mock_delivery1.status = DeliveryStatus.PENDING
    mock_delivery1.recipient = "a@b.com"
    mock_delivery2 = MagicMock()
    mock_delivery2.status = DeliveryStatus.PENDING
    mock_delivery2.recipient = "c@d.com"

    use_case._delivery_repository.get_by_digest_and_recipient.return_value = None
    use_case._delivery_repository.create.side_effect = [mock_delivery1, mock_delivery2]
    use_case._delivery_repository.update.side_effect = [
        None,
        RuntimeError("update failed"),
    ]

    summary = await use_case.execute(digest.id)
    assert summary.has_system_error
    assert summary.failed_count == 2
    assert len(summary.results) == 2
    assert summary.results[0].status == DeliveryStatus.FAILED
    assert summary.results[1].status == DeliveryStatus.FAILED
    assert "update failed" in summary.results[1].failure_reason


@pytest.mark.asyncio
async def test_unexpected_error_marks_pending_as_failed() -> None:
    digest = _make_digest()
    use_case = _build_usecase(digest=digest, recipients=["a@b.com", "c@d.com"])

    mock_delivery1 = MagicMock()
    mock_delivery1.status = DeliveryStatus.PENDING
    mock_delivery1.recipient = "a@b.com"
    mock_delivery2 = MagicMock()
    mock_delivery2.status = DeliveryStatus.PENDING
    mock_delivery2.recipient = "c@d.com"

    use_case._delivery_repository.get_by_digest_and_recipient.return_value = None
    use_case._delivery_repository.create.side_effect = [mock_delivery1, mock_delivery2]
    use_case._email_sender.send.side_effect = [
        None,
        RuntimeError("unexpected failure"),
    ]
    use_case._delivery_repository.update.side_effect = [None, None]

    with pytest.raises(RuntimeError, match="unexpected failure"):
        await use_case.execute(digest.id)

    assert use_case._delivery_repository.update.call_count == 2
    pending_updates = [
        call_obj.args[0]
        for call_obj in use_case._delivery_repository.update.call_args_list
        if call_obj.args[0].status == DeliveryStatus.FAILED
    ]
    assert len(pending_updates) == 1
    assert pending_updates[0].recipient == "c@d.com"


__all__ = [
    "test_auth_error_cleanup_continues_on_update_failure",
    "test_deliver_digest_auth_error_stops_and_reports",
    "test_deliver_digest_config_error_stops_and_reports",
    "test_deliver_digest_deduplicates_recipients",
    "test_deliver_digest_idempotent_skip_sent",
    "test_deliver_digest_invalid_recipient_continues",
    "test_deliver_digest_not_found",
    "test_deliver_digest_permanent_failure_continues",
    "test_deliver_digest_rate_limit_error_propagates",
    "test_deliver_digest_success",
    "test_deliver_digest_timeout_error_propagates",
    "test_deliver_digest_transient_error_propagates",
    "test_deliver_digest_zero_recipients",
    "test_ensure_deliveries_cleans_up_on_failure",
    "test_unexpected_error_marks_pending_as_failed",
]
