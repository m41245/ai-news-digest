from __future__ import annotations

from html import escape as html_escape
from typing import Any

_DIGEST_CSS = (
    "body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; "
    "max-width: 700px; margin: 0 auto; padding: 20px; } "
    ".digest-header { background: #1e40af; color: white; padding: 20px; "
    "border-radius: 8px 8px 0 0; } "
    ".digest-header h1 { margin: 0; font-size: 22px; } "
    ".digest-header p { margin: 4px 0 0 0; opacity: 0.9; font-size: 14px; } "
    ".section { margin-top: 24px; } "
    ".section-title { font-size: 16px; font-weight: bold; color: #1e40af; "
    "border-bottom: 2px solid #1e40af; padding-bottom: 4px; margin-bottom: 12px; } "
    ".article { padding: 12px 0; border-bottom: 1px solid #e2e8f0; } "
    ".article:last-child { border-bottom: none; } "
    ".article-title { font-size: 15px; font-weight: bold; color: #1e3a8a; "
    "text-decoration: none; } "
    ".article-title:hover { text-decoration: underline; } "
    ".article-meta { font-size: 12px; color: #64748b; margin-top: 4px; } "
    ".article-summary { font-size: 14px; color: #334155; margin-top: 6px; } "
    ".footer { margin-top: 32px; font-size: 12px; color: #64748b; "
    "border-top: 1px solid #e2e8f0; padding-top: 16px; } "
    ".footer a { color: #2563eb; text-decoration: none; } "
    ".capped-note { font-size: 13px; color: #64748b; font-style: italic; "
    "margin-top: 8px; } "
    ".empty-digest { padding: 40px 0; text-align: center; color: #64748b; }"
)


def _get_digest_dates(digest: Any) -> tuple[str, str]:
    safe_title = (
        html_escape(digest.title)
        if hasattr(digest, "title") and digest.title
        else "Digest"
    )
    safe_date = ""
    if hasattr(digest, "created_at") and digest.created_at:
        safe_date = html_escape(digest.created_at.strftime("%B %d, %Y"))
    return safe_title, safe_date


def _render_daily_digest_html(
    digest: Any,
    items: list[dict[str, Any]],
    app_name: str,
    base_url: str,
    unsubscribe_url: str | None,
    limit: int = 50,
) -> str:
    safe_app = html_escape(app_name)
    safe_title, safe_date = _get_digest_dates(digest)
    safe_base = html_escape(base_url)

    sections: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        category = item.get("category", "Other")
        sections.setdefault(category, []).append(item)

    for cat in sections:
        sections[cat].sort(key=lambda x: x.get("importance_score", 0), reverse=True)

    section_html_parts: list[str] = []
    for category, cat_items in sections.items():
        safe_cat = html_escape(category)
        section_html_parts.append(
            f"<div class='section'>"
            f"<div class='section-title'>{safe_cat}</div>"
        )
        for art in cat_items:
            title = html_escape(art.get("title", ""))
            summary = html_escape(art.get("summary", "")[:300])
            source = html_escape(art.get("source_name", ""))
            url = html_escape(art.get("url", ""))
            section_html_parts.append(
                "<div class='article'>"
                f"<a href='{url}' class='article-title'>{title}</a>"
                f"<div class='article-meta'>{source}</div>"
                f"<div class='article-summary'>{summary}</div>"
                "</div>"
            )
        section_html_parts.append("</div>")

    sections_html = "".join(section_html_parts)

    capped_note = ""
    if len(items) > limit:
        capped_note = (
            f"<p class='capped-note'>"
            f"Showing top {limit} of {len(items)} available articles."
            f"</p>"
        )

    header = (
        "<div class='digest-header'>"
        f"<h1>{safe_title}</h1>"
        f"<p>{safe_date} &middot; {safe_app}</p>"
        "</div>"
    )

    content = f"<div class='content'>{sections_html}{capped_note}</div>"

    footer_parts = [
        "<div class='footer'>",
    ]
    if hasattr(digest, "id"):
        footer_parts.append(
            f"<p><a href='{safe_base}/digests/{digest.id}'>"
            f"View full digest</a></p>"
        )
    footer_parts.append(f"<p>Sent to you by {safe_app}</p>")
    if unsubscribe_url:
        footer_parts.append(
            f"<p><a href='{html_escape(unsubscribe_url)}'>"
            f"Unsubscribe from email notifications</a></p>"
        )
    footer_parts.append("</div>")

    html = (
        "<!DOCTYPE html><html><head>"
        "<meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<style>{_DIGEST_CSS}</style>"
        "</head><body>"
        f"{header}{content}{''.join(footer_parts)}"
        "</body></html>"
    )
    return html


def _render_daily_digest_text(
    digest: Any,
    items: list[dict[str, Any]],
    app_name: str,
) -> str:
    safe_title = digest.title if hasattr(digest, "title") else "Daily Digest"
    safe_date = ""
    if hasattr(digest, "created_at") and digest.created_at:
        safe_date = digest.created_at.strftime("%B %d, %Y")
    parts = [safe_title, safe_date, "=" * len(safe_title), ""]

    sections: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        category = item.get("category", "Other")
        sections.setdefault(category, []).append(item)

    for cat in sections:
        sections[cat].sort(key=lambda x: x.get("importance_score", 0), reverse=True)

    for category, cat_items in sections.items():
        parts.extend([f"\n## {category}", "-" * len(category), ""])
        for art in cat_items:
            title = art.get("title", "")
            source = art.get("source_name", "")
            url = art.get("url", "")
            summary = art.get("summary", "")[:200]
            parts.extend([f"- {title} ({source})", f"  {url}", f"  {summary}", ""])

    if app_name:
        parts.extend([f"Sent to you by {app_name}", ""])
    return "\n".join(parts)


def render_daily_digest_email(
    digest: Any,
    items: list[dict[str, Any]],
    app_name: str,
    base_url: str,
    unsubscribe_url: str | None = None,
    limit: int = 50,
) -> tuple[str, str, str]:
    safe_title = digest.title if hasattr(digest, "title") else "Daily Digest"
    safe_date = ""
    if hasattr(digest, "created_at") and digest.created_at:
        safe_date = digest.created_at.strftime("%B %d, %Y")
    subject = f"{safe_title} - {safe_date}"
    html_body = _render_daily_digest_html(digest, items, app_name, base_url, unsubscribe_url, limit)
    text_body = _render_daily_digest_text(digest, items, app_name)
    return subject, html_body, text_body


def _render_weekly_digest_html(
    digest: Any,
    items: list[dict[str, Any]],
    app_name: str,
    base_url: str,
    unsubscribe_url: str | None,
    limit: int = 50,
) -> str:
    safe_app = html_escape(app_name)
    safe_title = (
        html_escape(digest.title)
        if hasattr(digest, "title") and digest.title
        else "Weekly Digest"
    )
    safe_base = html_escape(base_url)

    sections: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        category = item.get("category", "Other")
        sections.setdefault(category, []).append(item)

    for cat in sections:
        sections[cat].sort(key=lambda x: x.get("importance_score", 0), reverse=True)

    section_html_parts: list[str] = []
    for category, cat_items in sections.items():
        safe_cat = html_escape(category)
        section_html_parts.append(
            f"<div class='section'>"
            f"<div class='section-title'>{safe_cat}</div>"
        )
        for art in cat_items:
            title = html_escape(art.get("title", ""))
            summary = html_escape(art.get("summary", "")[:300])
            source = html_escape(art.get("source_name", ""))
            url = html_escape(art.get("url", ""))
            section_html_parts.append(
                "<div class='article'>"
                f"<a href='{url}' class='article-title'>{title}</a>"
                f"<div class='article-meta'>{source}</div>"
                f"<div class='article-summary'>{summary}</div>"
                "</div>"
            )
        section_html_parts.append("</div>")

    sections_html = "".join(section_html_parts)

    capped_note = ""
    if len(items) > limit:
        capped_note = (
            f"<p class='capped-note'>"
            f"Showing top {limit} of {len(items)} available articles."
            f"</p>"
        )

    header = (
        "<div class='digest-header'>"
        f"<h1>{safe_title}</h1>"
        f"<p>Your weekly summary &middot; {safe_app}</p>"
        "</div>"
    )

    content = f"<div class='content'>{sections_html}{capped_note}</div>"

    footer_parts = [
        "<div class='footer'>",
    ]
    if hasattr(digest, "id"):
        footer_parts.append(
            f"<p><a href='{safe_base}/digests/{digest.id}'>"
            f"View full digest</a></p>"
        )
    footer_parts.append(f"<p>Sent to you by {safe_app}</p>")
    if unsubscribe_url:
        footer_parts.append(
            f"<p><a href='{html_escape(unsubscribe_url)}'>"
            f"Unsubscribe from email notifications</a></p>"
        )
    footer_parts.append("</div>")

    html = (
        "<!DOCTYPE html><html><head>"
        "<meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<style>{_DIGEST_CSS}</style>"
        "</head><body>"
        f"{header}{content}{''.join(footer_parts)}"
        "</body></html>"
    )
    return html


def _render_weekly_digest_text(
    digest: Any,
    items: list[dict[str, Any]],
    app_name: str,
) -> str:
    safe_title = digest.title if hasattr(digest, "title") else "Weekly Digest"
    parts = [safe_title, "=" * len(safe_title), ""]

    sections: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        category = item.get("category", "Other")
        sections.setdefault(category, []).append(item)

    for cat in sections:
        sections[cat].sort(key=lambda x: x.get("importance_score", 0), reverse=True)

    for category, cat_items in sections.items():
        parts.extend([f"\n## {category}", "-" * len(category), ""])
        for art in cat_items:
            title = art.get("title", "")
            source = art.get("source_name", "")
            url = art.get("url", "")
            summary = art.get("summary", "")[:200]
            parts.extend([f"- {title} ({source})", f"  {url}", f"  {summary}", ""])

    if app_name:
        parts.extend([f"Sent to you by {app_name}", ""])
    return "\n".join(parts)


def render_weekly_digest_email(
    digest: Any,
    items: list[dict[str, Any]],
    app_name: str,
    base_url: str,
    unsubscribe_url: str | None = None,
    limit: int = 50,
) -> tuple[str, str, str]:
    safe_title = digest.title if hasattr(digest, "title") else "Weekly Digest"
    subject = f"{safe_title} - Your Weekly Summary"
    html_body = _render_weekly_digest_html(digest, items, app_name, base_url, unsubscribe_url)
    text_body = _render_weekly_digest_text(digest, items, app_name)
    return subject, html_body, text_body


__all__ = [
    "render_daily_digest_email",
    "render_weekly_digest_email",
]
