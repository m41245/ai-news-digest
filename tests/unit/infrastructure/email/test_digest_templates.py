"""
Unit tests for digest email template renderers.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from ai_news_digest.infrastructure.email.digest_templates import (
    render_daily_digest_email,
    render_weekly_digest_email,
)


def _make_digest(title: str = "Daily Digest", created_at: Any = None) -> MagicMock:
    digest = MagicMock()
    digest.title = title
    digest.created_at = created_at
    digest.id = MagicMock()
    return digest


def _make_item(
    title: str = "Article",
    category: str = "Tech",
    importance_score: float = 0.9,
    summary: str = "Summary",
    source_name: str = "Source",
    url: str = "http://example.com/article",
) -> dict[str, Any]:
    return {
        "title": title,
        "category": category,
        "importance_score": importance_score,
        "summary": summary,
        "source_name": source_name,
        "url": url,
    }


def test_daily_digest_template_renders_correctly() -> None:
    digest = _make_digest(created_at=MagicMock(strftime=lambda fmt: "January 01, 2026"))
    items = [_make_item()]
    subject, html, text = render_daily_digest_email(
        digest=digest,
        items=items,
        app_name="TestApp",
        base_url="http://localhost:8000",
        unsubscribe_url="http://localhost:8000/unsubscribe",
    )
    assert len(subject) > 0
    assert "<!DOCTYPE html>" in html
    assert "TestApp" in html
    assert "Article" in html
    assert len(text) > 0


def test_weekly_digest_template_renders_correctly() -> None:
    digest = _make_digest(
        title="Weekly Digest", created_at=MagicMock(strftime=lambda fmt: "January 01, 2026")
    )
    items = [_make_item()]
    subject, html, text = render_weekly_digest_email(
        digest=digest,
        items=items,
        app_name="TestApp",
        base_url="http://localhost:8000",
        unsubscribe_url="http://localhost:8000/unsubscribe",
    )
    assert len(subject) > 0
    assert "<!DOCTYPE html>" in html
    assert "Weekly Digest" in html
    assert "Article" in html
    assert len(text) > 0


def test_items_are_grouped_by_category() -> None:
    digest = _make_digest()
    items = [
        _make_item(category="Tech"),
        _make_item(category="Business"),
        _make_item(category="Tech"),
    ]
    _, html, _ = render_daily_digest_email(
        digest=digest,
        items=items,
        app_name="TestApp",
        base_url="http://localhost:8000",
    )
    assert "Tech" in html
    assert "Business" in html
    assert html.count("<div class='section-title'>") == 2


def test_most_important_items_first() -> None:
    digest = _make_digest()
    items = [
        _make_item(title="Low", importance_score=0.3),
        _make_item(title="High", importance_score=0.9),
        _make_item(title="Medium", importance_score=0.6),
    ]
    _, html, _ = render_daily_digest_email(
        digest=digest,
        items=items,
        app_name="TestApp",
        base_url="http://localhost:8000",
    )
    high_pos = html.find("High")
    medium_pos = html.find("Medium")
    low_pos = html.find("Low")
    assert high_pos < medium_pos < low_pos


def test_count_of_additional_items_shown_when_capped() -> None:
    digest = _make_digest()
    items = [_make_item(title=f"Item {i}") for i in range(100)]
    _, html, _ = render_daily_digest_email(
        digest=digest,
        items=items,
        app_name="TestApp",
        base_url="http://localhost:8000",
    )
    assert "capped-note" in html
    assert "Showing top" in html


def test_safe_escaping_of_content() -> None:
    digest = _make_digest()
    items = [_make_item(title="<script>alert('xss')</script>")]
    _, html, _ = render_daily_digest_email(
        digest=digest,
        items=items,
        app_name="TestApp",
        base_url="http://localhost:8000",
    )
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_unsubscribe_link_included() -> None:
    digest = _make_digest()
    items = [_make_item()]
    _, html, _ = render_daily_digest_email(
        digest=digest,
        items=items,
        app_name="TestApp",
        base_url="http://localhost:8000",
        unsubscribe_url="http://localhost:8000/unsubscribe",
    )
    assert "unsubscribe" in html.lower()


def test_app_name_included() -> None:
    digest = _make_digest()
    items = [_make_item()]
    _, html, _ = render_daily_digest_email(
        digest=digest,
        items=items,
        app_name="MyApp",
        base_url="http://localhost:8000",
    )
    assert "MyApp" in html


def test_weekly_digest_items_grouped_by_category() -> None:
    digest = _make_digest(title="Weekly Digest")
    items = [
        _make_item(category="Tech"),
        _make_item(category="Business"),
    ]
    _, html, _ = render_weekly_digest_email(
        digest=digest,
        items=items,
        app_name="TestApp",
        base_url="http://localhost:8000",
    )
    assert "Tech" in html
    assert "Business" in html


def test_weekly_digest_most_important_first() -> None:
    digest = _make_digest(title="Weekly Digest")
    items = [
        _make_item(title="Low", importance_score=0.3),
        _make_item(title="High", importance_score=0.9),
    ]
    _, html, _ = render_weekly_digest_email(
        digest=digest,
        items=items,
        app_name="TestApp",
        base_url="http://localhost:8000",
    )
    high_pos = html.find("High")
    low_pos = html.find("Low")
    assert high_pos < low_pos


def test_weekly_digest_safe_escaping() -> None:
    digest = _make_digest(title="Weekly Digest")
    items = [_make_item(title="<img src=x onerror=alert(1)>")]
    _, html, _ = render_weekly_digest_email(
        digest=digest,
        items=items,
        app_name="TestApp",
        base_url="http://localhost:8000",
    )
    assert "<img" not in html
    assert "&lt;img" in html


__all__ = [
    "test_app_name_included",
    "test_count_of_additional_items_shown_when_capped",
    "test_daily_digest_template_renders_correctly",
    "test_items_are_grouped_by_category",
    "test_most_important_items_first",
    "test_safe_escaping_of_content",
    "test_unsubscribe_link_included",
    "test_weekly_digest_items_grouped_by_category",
    "test_weekly_digest_most_important_first",
    "test_weekly_digest_safe_escaping",
    "test_weekly_digest_template_renders_correctly",
]
