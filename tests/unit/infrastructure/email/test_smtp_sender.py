"""
Unit tests for SMTPSender.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import aiosmtplib
import pytest

from ai_news_digest.infrastructure.email.errors import (
    EmailAuthenticationError,
    EmailConnectionError,
    EmailError,
    EmailInvalidRecipientError,
    EmailPermanentFailureError,
    EmailTimeoutError,
)
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


@pytest.fixture
def smtp_sender_tls() -> SMTPSender:
    """SMTPSender configured to use implicit TLS (port 465)."""
    return SMTPSender(
        host="smtp.example.com",
        port=465,
        username="testuser",
        password="testpass",
        from_address="test@example.com",
    )


def _mock_aiosmtplib_send(**kwargs: object) -> patch:
    """Return a patch context manager for aiosmtplib.send."""
    return patch(
        "ai_news_digest.infrastructure.email.smtp_sender.aiosmtplib.send",
        new_callable=AsyncMock,
        **kwargs,
    )


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
    assert sender._port is not None
    assert sender._from_address is not None


@pytest.mark.asyncio
async def test_smtp_sender_send_with_text_and_html(
    smtp_sender: SMTPSender,
) -> None:
    """Test sending email with both text and HTML content."""
    with _mock_aiosmtplib_send() as mock_send:
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
        assert call_args[1]["use_tls"] is False
        assert call_args[1]["start_tls"] is True


@pytest.mark.asyncio
async def test_smtp_sender_send_html_only(
    smtp_sender: SMTPSender,
) -> None:
    """Test sending email with only HTML content."""
    with _mock_aiosmtplib_send() as mock_send:
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
async def test_smtp_sender_send_with_defaults(
    smtp_sender_with_defaults: SMTPSender,
) -> None:
    """Test sending email with default configuration."""
    with _mock_aiosmtplib_send() as mock_send:
        await smtp_sender_with_defaults.send(
            recipient="recipient@example.com",
            subject="Test Subject",
            html="<p>HTML content</p>",
        )

        mock_send.assert_called_once()
        call_args = mock_send.call_args

        assert call_args[1]["hostname"] is not None
        assert call_args[1]["port"] is not None
        assert call_args[1]["use_tls"] is False
        assert call_args[1]["start_tls"] is True


@pytest.mark.asyncio
async def test_smtp_sender_send_uses_tls(
    smtp_sender: SMTPSender,
) -> None:
    """Test that SMTP sender uses TLS."""
    with _mock_aiosmtplib_send() as mock_send:
        await smtp_sender.send(
            recipient="recipient@example.com",
            subject="Test Subject",
            html="<p>HTML content</p>",
        )

        call_args = mock_send.call_args
        assert call_args[1]["use_tls"] is False
        assert call_args[1]["start_tls"] is True


@pytest.mark.asyncio
async def test_smtp_sender_send_message_structure(
    smtp_sender: SMTPSender,
) -> None:
    """Test that email message is structured correctly."""
    with _mock_aiosmtplib_send() as mock_send:
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
async def test_smtp_sender_send_email_multiple_recipients(
    smtp_sender: SMTPSender,
) -> None:
    """Test sending email to multiple recipients."""
    with _mock_aiosmtplib_send() as mock_send:
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
        assert message["Bcc"] == "recipient1@example.com, recipient2@example.com"
        assert message["Subject"] == "Test Subject"


@pytest.mark.asyncio
async def test_smtp_sender_send_email_single_recipient(
    smtp_sender: SMTPSender,
) -> None:
    """Test send_email with single recipient."""
    with _mock_aiosmtplib_send() as mock_send:
        await smtp_sender.send_email(
            to=["recipient@example.com"],
            subject="Test Subject",
            html_body="<p>HTML content</p>",
        )

        mock_send.assert_called_once()
        call_args = mock_send.call_args
        message = call_args[0][0]
        assert message["Bcc"] == "recipient@example.com"
        assert message["Subject"] == "Test Subject"


@pytest.mark.asyncio
async def test_send_tls_on_port_465(
    smtp_sender_tls: SMTPSender,
) -> None:
    """Port 465 uses implicit TLS (use_tls=True, start_tls=False)."""
    with _mock_aiosmtplib_send() as mock_send:
        await smtp_sender_tls.send(
            recipient="r@example.com",
            subject="S",
            html="<p>hi</p>",
        )

        call_kwargs = mock_send.call_args[1]
        assert call_kwargs["use_tls"] is True
        assert call_kwargs["start_tls"] is False


@pytest.mark.asyncio
async def test_send_email_uses_bcc_not_to(
    smtp_sender: SMTPSender,
) -> None:
    """send_email places recipients in Bcc, not the To header."""
    with _mock_aiosmtplib_send() as mock_send:
        await smtp_sender.send_email(
            to=["a@example.com", "b@example.com"],
            subject="S",
            html_body="<p>hi</p>",
        )

        message = mock_send.call_args[0][0]
        assert "To" not in message
        assert message["Bcc"] == "a@example.com, b@example.com"


@pytest.mark.asyncio
async def test_send_raises_email_authentication_error(
    smtp_sender: SMTPSender,
) -> None:
    """SMTPAuthenticationError is mapped to EmailAuthenticationError."""
    with (
        _mock_aiosmtplib_send(
            side_effect=aiosmtplib.SMTPAuthenticationError(535, "Auth failed"),
        ),
        pytest.raises(EmailAuthenticationError, match="auth"),
    ):
        await smtp_sender.send(
            recipient="r@example.com",
            subject="S",
            html="<p>hi</p>",
        )


@pytest.mark.asyncio
async def test_send_raises_email_connection_error(
    smtp_sender: SMTPSender,
) -> None:
    """SMTPConnectError is mapped to EmailConnectionError."""
    with (
        _mock_aiosmtplib_send(
            side_effect=aiosmtplib.SMTPConnectError("Cannot connect"),
        ),
        pytest.raises(EmailConnectionError, match="connection"),
    ):
        await smtp_sender.send(
            recipient="r@example.com",
            subject="S",
            html="<p>hi</p>",
        )


@pytest.mark.asyncio
async def test_send_raises_email_timeout_error(
    smtp_sender: SMTPSender,
) -> None:
    """SMTPTimeoutError is mapped to EmailTimeoutError."""
    with (
        _mock_aiosmtplib_send(
            side_effect=aiosmtplib.SMTPTimeoutError("Timed out"),
        ),
        pytest.raises(EmailTimeoutError, match="timeout"),
    ):
        await smtp_sender.send(
            recipient="r@example.com",
            subject="S",
            html="<p>hi</p>",
        )


@pytest.mark.asyncio
async def test_send_raises_email_connection_error_on_disconnect(
    smtp_sender: SMTPSender,
) -> None:
    """SMTPServerDisconnected is mapped to EmailConnectionError."""
    with (
        _mock_aiosmtplib_send(
            side_effect=aiosmtplib.SMTPServerDisconnected("Bye"),
        ),
        pytest.raises(EmailConnectionError, match="disconnected"),
    ):
        await smtp_sender.send(
            recipient="r@example.com",
            subject="S",
            html="<p>hi</p>",
        )


@pytest.mark.asyncio
async def test_send_email_raises_email_invalid_recipient_error(
    smtp_sender: SMTPSender,
) -> None:
    """SMTPRecipientsRefused is mapped to EmailInvalidRecipientError."""
    refused = aiosmtplib.SMTPRecipientRefused("bad@example.com", 550, "No such user")
    with (
        _mock_aiosmtplib_send(
            side_effect=aiosmtplib.SMTPRecipientsRefused([refused]),
        ),
        pytest.raises(EmailInvalidRecipientError, match="refused"),
    ):
        await smtp_sender.send_email(
            to=["bad@example.com"],
            subject="S",
            html_body="<p>hi</p>",
        )


@pytest.mark.asyncio
async def test_send_raises_email_permanent_failure_error(
    smtp_sender: SMTPSender,
) -> None:
    """SMTPSenderRefused is mapped to EmailPermanentFailureError."""
    with (
        _mock_aiosmtplib_send(
            side_effect=aiosmtplib.SMTPSenderRefused(554, "Sender refused", "test@example.com"),
        ),
        pytest.raises(EmailPermanentFailureError, match="refused"),
    ):
        await smtp_sender.send(
            recipient="r@example.com",
            subject="S",
            html="<p>hi</p>",
        )


@pytest.mark.asyncio
async def test_send_raises_email_error_on_unexpected_exception(
    smtp_sender: SMTPSender,
) -> None:
    """An unexpected exception is wrapped in EmailError."""
    with (
        _mock_aiosmtplib_send(
            side_effect=OSError("network unreachable"),
        ),
        pytest.raises(EmailError, match="Failed to send"),
    ):
        await smtp_sender.send(
            recipient="r@example.com",
            subject="S",
            html="<p>hi</p>",
        )


def test_smtp_sender_all_export() -> None:
    """Test that SMTPSender is exported in __all__."""
    from ai_news_digest.infrastructure.email.smtp_sender import __all__

    assert "SMTPSender" in __all__


__all__ = [
    "test_send_email_raises_email_invalid_recipient_error",
    "test_send_email_uses_bcc_not_to",
    "test_send_raises_email_authentication_error",
    "test_send_raises_email_connection_error",
    "test_send_raises_email_connection_error_on_disconnect",
    "test_send_raises_email_error_on_unexpected_exception",
    "test_send_raises_email_permanent_failure_error",
    "test_send_raises_email_timeout_error",
    "test_send_tls_on_port_465",
    "test_smtp_sender_all_export",
    "test_smtp_sender_initialization_partial_params",
    "test_smtp_sender_initialization_with_none_params",
    "test_smtp_sender_initialization_with_params",
    "test_smtp_sender_send_email_multiple_recipients",
    "test_smtp_sender_send_email_single_recipient",
    "test_smtp_sender_send_html_only",
    "test_smtp_sender_send_message_structure",
    "test_smtp_sender_send_uses_tls",
    "test_smtp_sender_send_with_defaults",
    "test_smtp_sender_send_with_text_and_html",
]
