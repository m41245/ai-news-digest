from __future__ import annotations

from html import escape as html_escape

from ai_news_digest.core.config import get_settings
from ai_news_digest.core.logging import get_logger

logger = get_logger(__name__)


class NotificationEmailComposer:
    """Builds email content for notifications."""

    def compose_notification_email(
        self,
        title: str,
        body: str,
        story_title: str | None = None,
        story_url: str | None = None,
        notification_url: str | None = None,
        unsubscribe_url: str | None = None,
    ) -> tuple[str, str]:
        """
        Return (html_body, text_body) for a notification email.
        """
        safe_title = html_escape(title)
        safe_body = html_escape(body)
        safe_story_title = html_escape(story_title) if story_title else None

        css = (
            "body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; "
            "max-width: 600px; margin: 0 auto; padding: 20px; } "
            ".header { background: #2563eb; color: white; padding: 16px; "
            "border-radius: 8px 8px 0 0; } "
            ".content { padding: 24px; background: #f8fafc; border: 1px solid #e2e8f0; "
            "border-top: none; border-radius: 0 0 8px 8px; } "
            ".story-link { display: inline-block; margin-top: 16px; color: #2563eb; "
            "text-decoration: none; font-weight: 500; } "
            ".footer { margin-top: 24px; font-size: 12px; color: #64748b; } "
            ".footer a { color: #64748b; }"
        )

        html_parts = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            "<meta charset='utf-8'>",
            "<meta name='viewport' content='width=device-width, initial-scale=1'>",
            f"<style>{css}</style>",
            "</head>",
            "<body>",
            "<div class='header'>",
            f"<h1 style='margin:0;font-size:18px;'>{safe_title}</h1>",
            "</div>",
            "<div class='content'>",
            f"<p>{safe_body}</p>",
        ]

        if safe_story_title and story_url:
            link = (
                f"<a href='{html_escape(story_url)}' class='story-link'>"
                f"Read: {safe_story_title}</a>"
            )
            html_parts.append(link)

        if notification_url:
            link = (
                f"<p style='margin-top:16px;'>"
                f"<a href='{html_escape(notification_url)}'>"
                "View all notifications</a></p>"
            )
            html_parts.append(link)

        html_parts.extend(
            [
                "</div>",
                "<div class='footer'>",
                f"<p>Sent to you by {html_escape(get_settings().app_name)}</p>",
            ]
        )

        if unsubscribe_url:
            link = (
                f"<p><a href='{html_escape(unsubscribe_url)}'>"
                "Unsubscribe from email notifications</a></p>"
            )
            html_parts.append(link)

        html_parts.extend(
            [
                "</div>",
                "</body>",
                "</html>",
            ]
        )

        html_body = "\n".join(html_parts)

        text_parts = [
            title,
            "=" * len(title),
            "",
            body,
            "",
        ]
        if story_title and story_url:
            text_parts.extend([f"Read: {story_title}", story_url, ""])
        if notification_url:
            text_parts.extend(["View all notifications:", notification_url, ""])
        text_parts.extend(
            [
                f"Sent to you by {get_settings().app_name}",
            ]
        )
        if unsubscribe_url:
            text_parts.extend(["", "Unsubscribe:", unsubscribe_url])

        text_body = "\n".join(text_parts)
        return html_body, text_body


__all__ = ["NotificationEmailComposer"]
