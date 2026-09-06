from __future__ import annotations

from html import escape as html_escape
from typing import Any

from ai_news_digest.core.logging import get_logger

logger = get_logger(__name__)


_BASE_CSS = (
    "body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; "
    "max-width: 600px; margin: 0 auto; padding: 20px; } "
    ".header { background: #2563eb; color: white; padding: 16px; "
    "border-radius: 8px 8px 0 0; } "
    ".content { padding: 24px; background: #f8fafc; border: 1px solid #e2e8f0; "
    "border-top: none; border-radius: 0 0 8px 8px; } "
    ".story-link { display: inline-block; margin-top: 16px; color: #2563eb; "
    "text-decoration: none; font-weight: 500; } "
    ".footer { margin-top: 24px; font-size: 12px; color: #64748b; } "
    ".footer a { color: #64748b; } "
    ".badge { display: inline-block; padding: 2px 8px; border-radius: 4px; "
    "font-size: 11px; font-weight: bold; text-transform: uppercase; } "
    ".badge-critical { background: #dc2626; color: white; } "
    ".badge-high { background: #ea580c; color: white; } "
    ".badge-medium { background: #f59e0b; color: white; } "
    ".badge-low { background: #16a34a; color: white; } "
    ".badge-info { background: #2563eb; color: white; }"
)


def _html_page(content: str, app_name: str, base_url: str, unsubscribe_url: str | None) -> str:
    safe_app = html_escape(app_name)
    safe_base = html_escape(base_url)
    footer_parts = [
        "<div class='footer'>",
        f"<p>Sent to you by {safe_app}</p>",
        f"<p><a href='{safe_base}'>Open {safe_app}</a></p>",
    ]
    if unsubscribe_url:
        footer_parts.append(
            f"<p><a href='{html_escape(unsubscribe_url)}'>"
            "Unsubscribe from email notifications</a></p>"
        )
    footer_parts.append("</div>")
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<style>{_BASE_CSS}</style></head><body>{content}{''.join(footer_parts)}</body></html>"
    )


def _text_page(title: str, body: str, story_title: str | None, story_url: str | None,
               extra_links: list[tuple[str, str]] | None = None, app_name: str = "") -> str:
    parts = [title, "=" * len(title), "", body, ""]
    if story_title and story_url:
        parts.extend([f"Read: {story_title}", story_url, ""])
    if extra_links:
        for label, url in extra_links:
            parts.extend([f"{label}:", url, ""])
    if app_name:
        parts.extend([f"Sent to you by {app_name}", ""])
    return "\n".join(parts)


def _notification_context(
    notification: Any,
    app_name: str,
    base_url: str,
    unsubscribe_url: str | None,
) -> dict[str, Any]:
    return {
        "notification": notification,
        "app_name": app_name,
        "base_url": base_url,
        "unsubscribe_url": unsubscribe_url,
    }


def _severity_badge_class(severity: str) -> str:
    mapping = {
        "critical": "badge-critical",
        "high": "badge-high",
        "medium": "badge-medium",
        "low": "badge-low",
        "info": "badge-info",
    }
    return mapping.get(severity.lower(), "badge-info")


def _build_context_links(notification: Any, base_url: str) -> str:
    parts = []
    if getattr(notification, "story_id", None):
        story_url = f"{html_escape(base_url)}/stories/{notification.story_id}"
        parts.append(f"<a href='{story_url}' class='story-link'>View Story</a>")
    if getattr(notification, "article_id", None):
        article_url = f"{html_escape(base_url)}/articles/{notification.article_id}"
        parts.append(f"<a href='{article_url}' class='story-link'>View Article</a>")
    if getattr(notification, "company_id", None):
        company_url = f"{html_escape(base_url)}/companies/{notification.company_id}"
        parts.append(f"<a href='{company_url}' class='story-link'>View Company</a>")
    if getattr(notification, "topic_id", None):
        topic_url = f"{html_escape(base_url)}/topics/{notification.topic_id}"
        parts.append(f"<a href='{topic_url}' class='story-link'>View Topic</a>")
    if getattr(notification, "digest_id", None):
        digest_url = f"{html_escape(base_url)}/digests/{notification.digest_id}"
        parts.append(f"<a href='{digest_url}' class='story-link'>View Digest</a>")
    return "".join(parts)


def _build_text_links(notification: Any, base_url: str) -> list[tuple[str, str]]:
    links: list[tuple[str, str]] = []
    if getattr(notification, "story_id", None):
        links.append(("View Story", f"{base_url}/stories/{notification.story_id}"))
    if getattr(notification, "article_id", None):
        links.append(("View Article", f"{base_url}/articles/{notification.article_id}"))
    if getattr(notification, "company_id", None):
        links.append(("View Company", f"{base_url}/companies/{notification.company_id}"))
    if getattr(notification, "topic_id", None):
        links.append(("View Topic", f"{base_url}/topics/{notification.topic_id}"))
    if getattr(notification, "digest_id", None):
        links.append(("View Digest", f"{base_url}/digests/{notification.digest_id}"))
    return links


def _render_common(notification: Any, app_name: str, base_url: str, unsubscribe_url: str | None,
                   severity_label: str, body_text: str, context_links: str | None = None,
                   extra_html: str = "") -> tuple[str, str, str]:
    safe_title = html_escape(notification.title)
    badge_class = _severity_badge_class(notification.severity.value)
    safe_severity = html_escape(notification.severity.value)
    safe_body = html_escape(body_text)

    header = (
        "<div class='header'>"
        f"<span class='badge {badge_class}'>{safe_severity}</span> "
        f"<h1 style='margin:8px 0 0 0;font-size:18px;'>{safe_title}</h1>"
        "</div>"
    )

    body_content = (
        "<div class='content'>"
        f"<p>{safe_body}</p>"
    )
    if context_links:
        body_content += context_links
    if extra_html:
        body_content += extra_html
    body_content += "</div>"

    html_body = _html_page(header + body_content, app_name, base_url, unsubscribe_url)

    text_links = _build_text_links(notification, base_url)
    text_body = _text_page(
        f"[{notification.severity.value.upper()}] {notification.title}",
        body_text,
        getattr(notification, "story_title", None),
        None,
        text_links,
        app_name,
    )

    subject = f"[{severity_label}] {notification.title}"
    return subject, html_body, text_body


def render_important_story_email(
    notification: Any,
    app_name: str,
    base_url: str,
    unsubscribe_url: str | None = None,
) -> tuple[str, str, str]:
    story_title = ""
    if notification.metadata:
        story_title = notification.metadata.get("story_title", "") or ""
    context = _build_context_links(notification, base_url)
    body = (
        "An important story has been detected that matches your preferences."
        + (f" Story: {story_title}" if story_title else "")
    )
    return _render_common(notification, app_name, base_url, unsubscribe_url,
                          "IMPORTANT STORY", body, context)


def render_followed_company_update_email(
    notification: Any,
    app_name: str,
    base_url: str,
    unsubscribe_url: str | None = None,
) -> tuple[str, str, str]:
    context = _build_context_links(notification, base_url)
    body = "There are new updates about a company you follow."
    return _render_common(notification, app_name, base_url, unsubscribe_url,
                          "COMPANY UPDATE", body, context)


def render_followed_topic_update_email(
    notification: Any,
    app_name: str,
    base_url: str,
    unsubscribe_url: str | None = None,
) -> tuple[str, str, str]:
    context = _build_context_links(notification, base_url)
    body = "There are new updates about a topic you follow."
    return _render_common(notification, app_name, base_url, unsubscribe_url,
                          "TOPIC UPDATE", body, context)


def render_story_evolution_email(
    notification: Any,
    app_name: str,
    base_url: str,
    unsubscribe_url: str | None = None,
) -> tuple[str, str, str]:
    context = _build_context_links(notification, base_url)
    body = "A story you're following has evolved with new developments."
    return _render_common(notification, app_name, base_url, unsubscribe_url,
                          "STORY EVOLUTION", body, context)


def render_contradiction_detected_email(
    notification: Any,
    app_name: str,
    base_url: str,
    unsubscribe_url: str | None = None,
) -> tuple[str, str, str]:
    context = _build_context_links(notification, base_url)
    body = "A contradiction has been detected in sources covering this story."
    return _render_common(notification, app_name, base_url, unsubscribe_url,
                          "CONTRADICTION DETECTED", body, context)


def render_correction_published_email(
    notification: Any,
    app_name: str,
    base_url: str,
    unsubscribe_url: str | None = None,
) -> tuple[str, str, str]:
    context = _build_context_links(notification, base_url)
    body = "A correction has been published for a story you're following."
    return _render_common(notification, app_name, base_url, unsubscribe_url,
                          "CORRECTION PUBLISHED", body, context)


def render_digest_ready_email(
    notification: Any,
    app_name: str,
    base_url: str,
    unsubscribe_url: str | None = None,
) -> tuple[str, str, str]:
    context = _build_context_links(notification, base_url)
    body = "Your digest is ready. Click below to view the latest curated news."
    extra = ""
    if notification.digest_id:
        digest_link = (
            f"{html_escape(base_url)}/digests/{notification.digest_id}"
        )
        extra = (
            f"<p><a href='{digest_link}' class='story-link'>"
            f"View Your Digest</a></p>"
        )
    return _render_common(notification, app_name, base_url, unsubscribe_url,
                          "DIGEST READY", body, context, extra_html=extra)


def render_system_email(
    notification: Any,
    app_name: str,
    base_url: str,
    unsubscribe_url: str | None = None,
) -> tuple[str, str, str]:
    context = _build_context_links(notification, base_url)
    body = notification.body or "A system notification regarding your account."
    return _render_common(notification, app_name, base_url, unsubscribe_url,
                          "SYSTEM", body, context)


__all__ = [
    "render_contradiction_detected_email",
    "render_correction_published_email",
    "render_digest_ready_email",
    "render_followed_company_update_email",
    "render_followed_topic_update_email",
    "render_important_story_email",
    "render_story_evolution_email",
    "render_system_email",
]
