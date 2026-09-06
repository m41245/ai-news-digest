"""
Unit tests for ``ConsoleEmailSender``.
"""

from __future__ import annotations

import logging
from unittest.mock import patch

import pytest

from ai_news_digest.infrastructure.email.development_sender import ConsoleEmailSender


@pytest.fixture
def sender() -> ConsoleEmailSender:
    return ConsoleEmailSender(from_address="noreply@example.com")


@pytest.mark.asyncio
async def test_send_logs_to_console(sender: ConsoleEmailSender, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO):
        await sender.send(
            recipient="user@example.com",
            subject="Hello",
            html="<p>Hi</p>",
            text="Hi",
        )
    assert "user@example.com" in caplog.text
    assert "Hello" in caplog.text


@pytest.mark.asyncio
async def test_send_logs_html_debug(sender: ConsoleEmailSender, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.DEBUG):
        await sender.send(
            recipient="user@example.com",
            subject="Hello",
            html="<p>debug html</p>",
        )
    assert "debug html" in caplog.text


@pytest.mark.asyncio
async def test_send_email_logs_all_recipients(sender: ConsoleEmailSender, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO):
        await sender.send_email(
            to=["a@example.com", "b@example.com"],
            subject="Batch",
            html_body="<p>html</p>",
            text_body="text",
        )
    assert "a@example.com" in caplog.text
    assert "b@example.com" in caplog.text
    assert "Batch" in caplog.text
    assert "Count: 2" in caplog.text


def test_initialization_stores_from_address() -> None:
    sender = ConsoleEmailSender(from_address="custom@example.com")
    assert sender._from_address == "custom@example.com"


__all__ = [
    "test_initialization_stores_from_address",
    "test_send_logs_html_debug",
    "test_send_logs_to_console",
    "test_send_email_logs_all_recipients",
]
