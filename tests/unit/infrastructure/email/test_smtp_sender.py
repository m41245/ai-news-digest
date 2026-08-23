"""
Unit tests for SMTPSender.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from ai_news_digest.infrastructure.email.smtp_sender import SMTPSender


@pytest.fixture
def smtp_sender() -> SMTPSender:
    """Create an SMTPSender instance with test configuration."""
    return SMTPSender(
        host="smtp.example.com",
        port=587,
        username="testuser",
        password="testpass",
        from_address="test@example.com",
    )


@pytest.fixture
def smtp_sender_with_defaults() -> SMTPSender:
    """Create an SMTPSender instance using default settings."""
    return SMTPSender()


def test_smtp_sender_initialization_with_params() -> None:
    """Test SMTPSender initialization with explicit parameters."""
    sender = SMTPSender(
        host="smtp.example.com",
        port=2525,
        username="user",
        password="pass",
        from_address="sender@example.com",
    )

    assert sender._host == "smtp.example.com"
    assert sender._port == 2525
    assert sender._username == "user"
    assert sender._password == "pass"
    assert sender._from_address == "sender@example.com"


def test_smtp_sender_initialization_with_none_params() -> None:
    """Test SMTPSender initialization with None parameters uses defaults."""
    sender = SMTPSender(
        host=None,
        port=None,
        username=None,
        password=None,
        from_address=None,
    )

    # Should use settings defaults
    assert sender._host is not None
    assert sender._port is not None
    assert sender._from_address is not None


def test_smtp_sender_initialization_partial_params() -> None:
    """Test SMTPSender initialization with partial parameters."""
    sender = SMTPSender(
        host="smtp.example.com",
        port=None,
        username=None,
        password=None,
        from_address=None,
    )

    assert sender._host == "smtp.example.com"
    assert sender._port is not None  # Uses default
    assert sender._from_address is not None  # Uses default


@pytest.mark.asyncio
async def test_smtp_sender_send_with_text_and_html(smtp_sender: SMTPSender) -> None:
    """Test sending email with both text and HTML content."""
    with patch(
        "ai_news_digest.infrastructure.email.smtp_sender.aiosmtplib.send", new_callable=AsyncMock
    ) as mock_send:
        await smtp_sender.send(
            recipient="recipient@example.com",
            subject="Test Subject",
            html="<p>HTML content</p>",
            text="Text content",
        )

        mock_send.assert_called_once()
        call_args = mock_send.call_args

        message = call_args[0][0]
        assert message["From"] == "test@example.com"
        assert message["To"] == "recipient@example.com"
        assert message["Subject"] == "Test Subject"
        assert call_args[1]["hostname"] == "smtp.example.com"
        assert call_args[1]["port"] == 587
        assert call_args[1]["username"] == "testuser"
        assert call_args[1]["password"] == "testpass"
        assert call_args[1]["use_tls"] is True


@pytest.mark.asyncio
async def test_smtp_sender_send_html_only(smtp_sender: SMTPSender) -> None:
    """Test sending email with only HTML content."""
    with patch(
        "ai_news_digest.infrastructure.email.smtp_sender.aiosmtplib.send", new_callable=AsyncMock
    ) as mock_send:
        await smtp_sender.send(
            recipient="recipient@example.com",
            subject="Test Subject",
            html="<p>HTML content</p>",
            text=None,
        )

        mock_send.assert_called_once()
        call_args = mock_send.call_args
        message = call_args[0][0]

        assert message["From"] == "test@example.com"
        assert message["To"] == "recipient@example.com"
        assert message["Subject"] == "Test Subject"


@pytest.mark.asyncio
async def test_smtp_sender_send_with_defaults(smtp_sender_with_defaults: SMTPSender) -> None:
    """Test sending email with default configuration."""
    with patch(
        "ai_news_digest.infrastructure.email.smtp_sender.aiosmtplib.send", new_callable=AsyncMock
    ) as mock_send:
        await smtp_sender_with_defaults.send(
            recipient="recipient@example.com",
            subject="Test Subject",
            html="<p>HTML content</p>",
        )

        mock_send.assert_called_once()
        call_args = mock_send.call_args

        assert call_args[1]["hostname"] is not None
        assert call_args[1]["port"] is not None
        assert call_args[1]["use_tls"] is True


@pytest.mark.asyncio
async def test_smtp_sender_send_uses_tls(smtp_sender: SMTPSender) -> None:
    """Test that SMTP sender uses TLS."""
    with patch(
        "ai_news_digest.infrastructure.email.smtp_sender.aiosmtplib.send", new_callable=AsyncMock
    ) as mock_send:
        await smtp_sender.send(
            recipient="recipient@example.com",
            subject="Test Subject",
            html="<p>HTML content</p>",
        )

        call_args = mock_send.call_args
        assert call_args[1]["use_tls"] is True


@pytest.mark.asyncio
async def test_smtp_sender_send_message_structure(smtp_sender: SMTPSender) -> None:
    """Test that email message is structured correctly."""
    with patch(
        "ai_news_digest.infrastructure.email.smtp_sender.aiosmtplib.send", new_callable=AsyncMock
    ) as mock_send:
        await smtp_sender.send(
            recipient="recipient@example.com",
            subject="Test Subject",
            html="<p>HTML content</p>",
            text="Text content",
        )

        call_args = mock_send.call_args
        message = call_args[0][0]

        assert message["From"] == "test@example.com"
        assert message["To"] == "recipient@example.com"
        assert message["Subject"] == "Test Subject"


@pytest.mark.asyncio
async def test_smtp_sender_send_email_multiple_recipients(smtp_sender: SMTPSender) -> None:
    """Test sending email to multiple recipients."""
    with patch(
        "ai_news_digest.infrastructure.email.smtp_sender.aiosmtplib.send", new_callable=AsyncMock
    ) as mock_send:
        await smtp_sender.send_email(
            to=["recipient1@example.com", "recipient2@example.com"],
            subject="Test Subject",
            html_body="<p>HTML content</p>",
            text_body="Text content",
        )

        mock_send.assert_called_once()
        call_args = mock_send.call_args

        message = call_args[0][0]
        assert message["From"] == "test@example.com"
        assert "recipient1@example.com" in message["To"]
        assert "recipient2@example.com" in message["To"]
        assert message["Subject"] == "Test Subject"


@pytest.mark.asyncio
async def test_smtp_sender_send_email_single_recipient(smtp_sender: SMTPSender) -> None:
    """Test send_email with single recipient."""
    with patch(
        "ai_news_digest.infrastructure.email.smtp_sender.aiosmtplib.send", new_callable=AsyncMock
    ) as mock_send:
        await smtp_sender.send_email(
            to=["recipient@example.com"],
            subject="Test Subject",
            html_body="<p>HTML content</p>",
        )

        mock_send.assert_called_once()
        call_args = mock_send.call_args
        message = call_args[0][0]
        assert message["To"] == "recipient@example.com"


def test_smtp_sender_all_export() -> None:
    """Test that SMTPSender is exported in __all__."""
    from ai_news_digest.infrastructure.email.smtp_sender import __all__

    assert "SMTPSender" in __all__
