"""
Unit tests for ``TestEmailSender``.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from ai_news_digest.infrastructure.email.test_sender import SentEmailRecord, TestEmailSender


@pytest.fixture
def sender() -> TestEmailSender:
    return TestEmailSender()


@pytest.mark.asyncio
async def test_records_sent_emails(sender: TestEmailSender) -> None:
    await sender.send(
        recipient="user@example.com",
        subject="Hello",
        html="<p>Hi</p>",
        text="Hi",
    )
    assert len(sender.sent_emails) == 1
    record = sender.sent_emails[0]
    assert record.to == ["user@example.com"]
    assert record.subject == "Hello"
    assert record.html_body == "<p>Hi</p>"


@pytest.mark.asyncio
async def test_send_email_records_multiple_recipients(sender: TestEmailSender) -> None:
    await sender.send_email(
        to=["a@example.com", "b@example.com"],
        subject="Batch",
        html_body="<p>html</p>",
        text_body="text",
    )
    assert len(sender.sent_emails) == 1
    record = sender.sent_emails[0]
    assert record.to == ["a@example.com", "b@example.com"]
    assert record.subject == "Batch"


def test_provides_access_to_sent_emails_for_assertions(sender: TestEmailSender) -> None:
    import asyncio

    asyncio.run(sender.send(recipient="user@example.com", subject="S", html="<p/>"))
    emails = sender.sent_emails
    assert isinstance(emails, list)
    assert len(emails) == 1


@pytest.mark.asyncio
async def test_clear_removes_sent_emails(sender: TestEmailSender) -> None:
    await sender.send(recipient="user@example.com", subject="S", html="<p/>")
    await sender.send(recipient="other@example.com", subject="S2", html="<p/>")
    assert len(sender.sent_emails) == 2
    sender.clear()
    assert len(sender.sent_emails) == 0


@pytest.mark.asyncio
async def test_records_sent_at_timestamp(sender: TestEmailSender) -> None:
    before = datetime.now(UTC)
    await sender.send(recipient="user@example.com", subject="S", html="<p/>")
    after = datetime.now(UTC)
    record = sender.sent_emails[0]
    assert before <= record.sent_at <= after


@pytest.mark.asyncio
async def test_sent_email_record_attributes(sender: TestEmailSender) -> None:
    await sender.send_email(
        to=["user@example.com"],
        subject="Subject",
        html_body="<html></html>",
        text_body="plain",
    )
    record = sender.sent_emails[0]
    assert isinstance(record, SentEmailRecord)
    assert record.to == ["user@example.com"]
    assert record.subject == "Subject"
    assert record.html_body == "<html></html>"
    assert record.text_body == "plain"


def test_sent_emails_returns_copy_not_reference(sender: TestEmailSender) -> None:
    import asyncio

    asyncio.run(sender.send(recipient="user@example.com", subject="S", html="<p/>"))
    emails1 = sender.sent_emails
    emails2 = sender.sent_emails
    assert emails1 is not emails2
    assert emails1 == emails2


__all__ = [
    "test_clear_removes_sent_emails",
    "test_provides_access_to_sent_emails_for_assertions",
    "test_records_sent_at_timestamp",
    "test_records_sent_emails",
    "test_send_email_records_multiple_recipients",
    "test_sent_email_record_attributes",
    "test_sent_emails_returns_copy_not_reference",
]
