"""
Unit tests for notification email template renderers.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from ai_news_digest.domain.enums.notification import NotificationSeverity, NotificationType
from ai_news_digest.domain.models.notification import Notification
from ai_news_digest.infrastructure.email.notification_templates import (
    render_contradiction_detected_email,
    render_correction_published_email,
    render_digest_ready_email,
    render_followed_company_update_email,
    render_followed_topic_update_email,
    render_important_story_email,
    render_story_evolution_email,
    render_system_email,
)


def _make_notification(
    notification_type: NotificationType = NotificationType.SYSTEM,
    title: str = "Title",
    severity: NotificationSeverity = NotificationSeverity.MEDIUM,
    metadata: dict[str, Any] | None = None,
    story_id: Any = None,
    company_id: Any = None,
    topic_id: Any = None,
    digest_id: Any = None,
) -> Notification:
    return Notification(
        id=MagicMock(),
        user_id=MagicMock(),
        notification_type=notification_type,
        title=title,
        body="Body",
        severity=severity,
        metadata=metadata,
        story_id=story_id,
        company_id=company_id,
        topic_id=topic_id,
        digest_id=digest_id,
    )


@pytest.mark.parametrize(
    "render_fn,notification_type",
    [
        (render_important_story_email, NotificationType.IMPORTANT_STORY),
        (render_followed_company_update_email, NotificationType.FOLLOWED_COMPANY_UPDATE),
        (render_followed_topic_update_email, NotificationType.FOLLOWED_TOPIC_UPDATE),
        (render_story_evolution_email, NotificationType.STORY_EVOLUTION),
        (render_contradiction_detected_email, NotificationType.CONTRADICTION_DETECTED),
        (render_correction_published_email, NotificationType.CORRECTION_PUBLISHED),
        (render_digest_ready_email, NotificationType.DIGEST_READY),
        (render_system_email, NotificationType.SYSTEM),
    ],
)
def test_each_template_returns_subject_html_and_text(
    render_fn: Any,
    notification_type: NotificationType,
) -> None:
    notification = _make_notification(notification_type=notification_type)
    result = render_fn(
        notification=notification,
        app_name="TestApp",
        base_url="http://localhost:8000",
        unsubscribe_url="http://localhost:8000/unsubscribe",
    )
    assert len(result) == 3
    subject, html, text = result
    assert isinstance(subject, str)
    assert len(subject) > 0
    assert isinstance(html, str)
    assert len(html) > 0
    assert isinstance(text, str)
    assert len(text) > 0


@pytest.mark.parametrize(
    "render_fn",
    [
        render_important_story_email,
        render_followed_company_update_email,
        render_followed_topic_update_email,
        render_story_evolution_email,
        render_contradiction_detected_email,
        render_correction_published_email,
        render_digest_ready_email,
        render_system_email,
    ],
)
def test_html_is_properly_escaped(render_fn: Any) -> None:
    notification = _make_notification(title="<script>alert('xss')</script>")
    _, html, _ = render_fn(
        notification=notification,
        app_name="TestApp",
        base_url="http://localhost:8000",
    )
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


@pytest.mark.parametrize(
    "render_fn",
    [
        render_important_story_email,
        render_followed_company_update_email,
        render_followed_topic_update_email,
        render_story_evolution_email,
        render_contradiction_detected_email,
        render_correction_published_email,
        render_digest_ready_email,
        render_system_email,
    ],
)
def test_unsubscribe_link_is_included(render_fn: Any) -> None:
    notification = _make_notification()
    _, html, _ = render_fn(
        notification=notification,
        app_name="TestApp",
        base_url="http://localhost:8000",
        unsubscribe_url="http://localhost:8000/unsubscribe",
    )
    assert "unsubscribe" in html.lower()


@pytest.mark.parametrize(
    "render_fn",
    [
        render_important_story_email,
        render_followed_company_update_email,
        render_followed_topic_update_email,
        render_story_evolution_email,
        render_contradiction_detected_email,
        render_correction_published_email,
        render_digest_ready_email,
        render_system_email,
    ],
)
def test_app_name_is_included(render_fn: Any) -> None:
    notification = _make_notification()
    _, html, _ = render_fn(
        notification=notification,
        app_name="MyApp",
        base_url="http://localhost:8000",
    )
    assert "MyApp" in html


def test_story_context_is_included_in_important_story() -> None:
    notification = _make_notification(
        notification_type=NotificationType.IMPORTANT_STORY,
        metadata={"story_title": "Big Story"},
    )
    _, html, text = render_important_story_email(
        notification=notification,
        app_name="TestApp",
        base_url="http://localhost:8000",
    )
    assert "Big Story" in html
    assert "Big Story" in text


def test_company_context_is_included() -> None:
    notification = _make_notification(
        notification_type=NotificationType.FOLLOWED_COMPANY_UPDATE,
        company_id=MagicMock(),
    )
    _, html, _ = render_followed_company_update_email(
        notification=notification,
        app_name="TestApp",
        base_url="http://localhost:8000",
    )
    assert "View Company" in html


def test_topic_context_is_included() -> None:
    notification = _make_notification(
        notification_type=NotificationType.FOLLOWED_TOPIC_UPDATE,
        topic_id=MagicMock(),
    )
    _, html, _ = render_followed_topic_update_email(
        notification=notification,
        app_name="TestApp",
        base_url="http://localhost:8000",
    )
    assert "View Topic" in html


def test_plain_text_fallback_is_present() -> None:
    notification = _make_notification()
    _, _, text = render_system_email(
        notification=notification,
        app_name="TestApp",
        base_url="http://localhost:8000",
    )
    assert "Title" in text
    assert "Body" in text


def test_html_starts_with_doctype() -> None:
    notification = _make_notification()
    _, html, _ = render_system_email(
        notification=notification,
        app_name="TestApp",
        base_url="http://localhost:8000",
    )
    assert html.startswith("<!DOCTYPE html>")


def test_digest_ready_includes_digest_link() -> None:
    notification = _make_notification(
        notification_type=NotificationType.DIGEST_READY,
        digest_id=MagicMock(),
    )
    _, html, _ = render_digest_ready_email(
        notification=notification,
        app_name="TestApp",
        base_url="http://localhost:8000",
    )
    assert "View Your Digest" in html


__all__ = [
    "test_app_name_is_included",
    "test_company_context_is_included",
    "test_digest_ready_includes_digest_link",
    "test_each_template_returns_subject_html_and_text",
    "test_html_is_properly_escaped",
    "test_html_starts_with_doctype",
    "test_plain_text_fallback_is_present",
    "test_story_context_is_included_in_important_story",
    "test_topic_context_is_included",
    "test_unsubscribe_link_is_included",
]
