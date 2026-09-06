"""
Unit tests for ``create_email_sender`` provider factory.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from ai_news_digest.core.config import Settings
from ai_news_digest.infrastructure.email.development_sender import ConsoleEmailSender
from ai_news_digest.infrastructure.email.provider_factory import create_email_sender
from ai_news_digest.infrastructure.email.smtp_sender import SMTPSender
from ai_news_digest.infrastructure.email.test_sender import TestEmailSender


def _make_settings(
    email_enabled: bool = True,
    email_development_mode: bool = False,
    email_provider: str = "console",
) -> Settings:
    return Settings(
        email_enabled=email_enabled,
        email_development_mode=email_development_mode,
        email_provider=email_provider,
        email_from_address="test@example.com",
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_user="user",
        smtp_password="pass",
    )


def test_returns_console_sender_when_email_disabled() -> None:
    settings = _make_settings(email_enabled=False)
    sender = create_email_sender(settings_obj=settings)
    assert isinstance(sender, ConsoleEmailSender)


def test_returns_console_sender_when_development_mode() -> None:
    settings = _make_settings(email_enabled=True, email_development_mode=True)
    sender = create_email_sender(settings_obj=settings)
    assert isinstance(sender, ConsoleEmailSender)


def test_returns_smtp_sender_when_smtp_provider() -> None:
    settings = _make_settings(email_enabled=True, email_development_mode=False, email_provider="smtp")
    sender = create_email_sender(settings_obj=settings)
    assert isinstance(sender, SMTPSender)


def test_returns_test_sender_when_test_provider() -> None:
    settings = _make_settings(email_enabled=True, email_development_mode=False, email_provider="test")
    sender = create_email_sender(settings_obj=settings)
    assert isinstance(sender, TestEmailSender)


def test_returns_console_sender_for_unknown_provider() -> None:
    custom_settings = MagicMock()
    custom_settings.email_enabled = True
    custom_settings.email_development_mode = False
    custom_settings.email_provider = "unknown"
    custom_settings.email_from_address = "test@example.com"
    custom_settings.smtp_host = None
    custom_settings.smtp_port = None
    custom_settings.smtp_user = None
    custom_settings.smtp_password = None
    sender = create_email_sender(settings_obj=custom_settings)
    assert isinstance(sender, ConsoleEmailSender)


def test_accepts_explicit_settings_object() -> None:
    custom_settings = _make_settings(email_enabled=False)
    sender = create_email_sender(settings_obj=custom_settings)
    assert isinstance(sender, ConsoleEmailSender)


def test_development_mode_overrides_smtp_provider() -> None:
    settings = _make_settings(
        email_enabled=True,
        email_development_mode=True,
        email_provider="smtp",
    )
    sender = create_email_sender(settings_obj=settings)
    assert isinstance(sender, ConsoleEmailSender)


__all__ = [
    "test_accepts_explicit_settings_object",
    "test_returns_console_sender_for_unknown_provider",
    "test_returns_console_sender_when_development_mode",
    "test_returns_console_sender_when_email_disabled",
    "test_returns_smtp_sender_when_smtp_provider",
    "test_returns_test_sender_when_test_provider",
    "test_development_mode_overrides_smtp_provider",
]
