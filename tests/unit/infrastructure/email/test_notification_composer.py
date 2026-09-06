"""
Unit tests for ``NotificationEmailComposer``.
"""

from __future__ import annotations

import pytest

from ai_news_digest.infrastructure.email.notification_composer import (
    NotificationEmailComposer,
)


def test_compose_returns_html_and_text() -> None:
    composer = NotificationEmailComposer()
    html, text = composer.compose_notification_email(
        title="Alert",
        body="Something happened.",
        story_title="Story",
        story_url="https://example.com/story",
        notification_url="https://example.com/notifications",
        unsubscribe_url="https://example.com/unsubscribe",
    )
    assert "<!DOCTYPE html>" in html
    assert "Alert" in html
    assert "Something happened." in html
    assert "Story" in text
    assert "Something happened." in text
    assert "https://example.com/story" in text
    assert "https://example.com/unsubscribe" in text


def test_compose_escapes_html_in_title_and_body() -> None:
    composer = NotificationEmailComposer()
    html, _ = composer.compose_notification_email(
        title="<script>alert('xss')</script>",
        body="<b>bold</b> & <i>italic</i>",
    )
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "<b>bold</b>" not in html
    assert "&lt;b&gt;bold&lt;/b&gt;" in html
    assert "&amp;" in html


def test_compose_without_optional_links() -> None:
    composer = NotificationEmailComposer()
    html, text = composer.compose_notification_email(
        title="Title",
        body="Body",
    )
    assert "Title" in html
    assert "Body" in text
    assert "Read:" not in text
    assert "View all notifications" not in text
    assert "Unsubscribe" not in text


def test_compose_app_name_escaped() -> None:
    composer = NotificationEmailComposer()
    html, _ = composer.compose_notification_email(
        title="Title",
        body="Body",
    )
    assert "Sent to you by" in html


def test_compose_html_structure() -> None:
    composer = NotificationEmailComposer()
    html, _ = composer.compose_notification_email(
        title="Title",
        body="Body",
    )
    assert html.startswith("<!DOCTYPE html>")
    assert "<html>" in html
    assert "</html>" in html
    assert "<style>" in html


__all__ = [
    "test_compose_app_name_escaped",
    "test_compose_escapes_html_in_title_and_body",
    "test_compose_html_structure",
    "test_compose_returns_html_and_text",
    "test_compose_without_optional_links",
]
