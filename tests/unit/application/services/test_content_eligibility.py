"""Regression tests for the canonical content-eligibility policy.

These tests exercise ``content_eligibility.assess_content_eligibility`` in
isolation so the eligibility rules are independently verifiable without a
database, broker, or external services.
"""

from __future__ import annotations

from unittest.mock import patch

from ai_news_digest.application.services.content_eligibility import (
    MIN_CONTENT_CHARS,
    ContentEligibility,
    assess_content_eligibility,
    is_eligible_for_summarize,
)

# ----------------------------------------------------------------------
# None / empty / whitespace-only content
# ----------------------------------------------------------------------


def test_assess_content_none_no_summary() -> None:
    result = assess_content_eligibility(content=None, summary=None)
    assert result.eligible is False
    assert result.reason == "awaiting_extraction"
    assert result.usable_text is None


def test_assess_content_none_with_valid_summary() -> None:
    result = assess_content_eligibility(content=None, summary="A valid existing summary.")
    assert result.eligible is True
    assert result.reason == "existing_summary_valid"
    assert result.usable_text == "A valid existing summary."


def test_assess_content_empty_no_summary() -> None:
    result = assess_content_eligibility(content="", summary=None)
    assert result.eligible is False
    assert result.reason == "empty_content"
    assert result.usable_text is None


def test_assess_content_whitespace_only_no_summary() -> None:
    result = assess_content_eligibility(content="   \n  \t  ", summary=None)
    assert result.eligible is False
    assert result.reason == "empty_content"
    assert result.usable_text is None


def test_assess_content_whitespace_only_with_valid_summary() -> None:
    result = assess_content_eligibility(content="   \n  ", summary="Existing summary text.")
    assert result.eligible is True
    assert result.reason == "existing_summary_valid"


def test_assess_content_empty_summary_with_valid_content() -> None:
    result = assess_content_eligibility(
        content="Real article content here about AI developments.", summary=""
    )
    assert result.eligible is True
    assert result.reason == "eligible"


# ----------------------------------------------------------------------
# HTML-only, script/style, navigation, boilerplate content
# ----------------------------------------------------------------------


def test_assess_content_html_script_only() -> None:
    result = assess_content_eligibility(content="<script>alert('xss')</script>", summary=None)
    assert result.eligible is False
    assert result.reason == "html_only_or_boilerplate"
    assert result.usable_text is None


def test_assess_content_html_style_only() -> None:
    result = assess_content_eligibility(
        content="<style>body { display: none; }</style>", summary=None
    )
    assert result.eligible is False
    assert result.reason == "html_only_or_boilerplate"


def test_assess_content_navigation_boilerplate_only() -> None:
    result = assess_content_eligibility(
        content="<nav>Home About Contact</nav><footer>2026 Acme Corp</footer>",
        summary=None,
    )
    assert result.eligible is False
    assert result.reason == "html_only_or_boilerplate"


def test_assess_content_html_preserves_article_text() -> None:
    result = assess_content_eligibility(
        content="<html><body><article><p>Breaking news about AI developments today.</p></article></body></html>",
        summary=None,
    )
    assert result.eligible is True
    assert result.reason == "eligible"
    assert result.usable_text is not None
    assert "Breaking news" in result.usable_text


def test_assess_content_malformed_html() -> None:
    result = assess_content_eligibility(
        content="<broken><unclosed><div>no proper structure", summary=None
    )
    assert result.eligible is False
    assert result.reason == "html_only_or_boilerplate"


def test_assess_content_parser_exception_falls_back_to_empty() -> None:
    """Trafilatura exceptions are caught; unusable markup is never accepted."""
    with patch(
        "ai_news_digest.application.services.content_eligibility.trafilatura.extract",
        side_effect=RuntimeError("extraction failed"),
    ):
        result = assess_content_eligibility(
            content="<html><body><p>Some article text.</p></body></html>",
            summary=None,
        )
    assert result.eligible is False
    assert result.reason == "html_only_or_boilerplate"
    assert result.usable_text is None


def test_assess_content_parser_exception_with_valid_summary() -> None:
    """Parser exception with a valid summary still falls back to the summary."""
    with patch(
        "ai_news_digest.application.services.content_eligibility.trafilatura.extract",
        side_effect=RuntimeError("extraction failed"),
    ):
        result = assess_content_eligibility(
            content="<html><body><p>Some article text.</p></body></html>",
            summary="A valid pre-existing summary.",
        )
    assert result.eligible is True
    assert result.reason == "existing_summary_valid"
    assert result.usable_text == "A valid pre-existing summary."


# ----------------------------------------------------------------------
# Title-only records
# ----------------------------------------------------------------------


def test_assess_content_title_only() -> None:
    result = assess_content_eligibility(
        content="Breaking News: AI Act Signed",
        summary=None,
        title="Breaking News: AI Act Signed",
    )
    assert result.eligible is False
    assert result.reason == "title_only"


def test_assess_content_title_only_with_valid_summary() -> None:
    result = assess_content_eligibility(
        content="Breaking News: AI Act Signed",
        summary="The EU AI Act has been signed into law.",
        title="Breaking News: AI Act Signed",
    )
    assert result.eligible is True
    assert result.reason == "existing_summary_valid"


def test_assess_content_title_vs_body_not_title_only() -> None:
    result = assess_content_eligibility(
        content="Breaking News: AI Act Signed. The European Parliament approved "
        "the legislation after years of debate and negotiation.",
        summary=None,
        title="Breaking News: AI Act Signed",
    )
    assert result.eligible is True
    assert result.reason == "eligible"


# ----------------------------------------------------------------------
# Short meaningful vs valid longer content
# ----------------------------------------------------------------------


def test_assess_content_short_meaningful_above_threshold() -> None:
    """Short but meaningful content clears the minimum threshold."""
    content = "AI startup raises $5M in seed funding."
    assert len(content) >= MIN_CONTENT_CHARS
    result = assess_content_eligibility(content=content, summary=None)
    assert result.eligible is True
    assert result.reason == "eligible"


def test_assess_content_short_below_threshold() -> None:
    """Content below the minimum threshold is ineligible without a summary."""
    result = assess_content_eligibility(content="AI news.", summary=None)
    assert result.eligible is False
    assert result.reason == "insufficient_content"


def test_assess_content_short_below_threshold_with_summary() -> None:
    """Short content with a valid existing summary remains eligible."""
    result = assess_content_eligibility(
        content="AI news.", summary="An AI startup raised seed funding."
    )
    assert result.eligible is True
    assert result.reason == "existing_summary_valid"


def test_assess_content_valid_longer_article() -> None:
    content = (
        "Artificial intelligence companies announced new models today. "
        "The releases include improvements in reasoning, coding, and "
        "multimodal capabilities. Developers can access the models via API."
    )
    result = assess_content_eligibility(content=content, summary=None)
    assert result.eligible is True
    assert result.reason == "eligible"


# ----------------------------------------------------------------------
# Punctuation and Unicode
# ----------------------------------------------------------------------


def test_assess_content_unicode_punctuation() -> None:
    result = assess_content_eligibility(
        content="Café résumé naïve — AI & ML: 2026 update.", summary=None
    )
    assert result.eligible is True
    assert result.reason == "eligible"


# ----------------------------------------------------------------------
# Existing summary behavior
# ----------------------------------------------------------------------


def test_assess_content_existing_summary_preserved() -> None:
    result = assess_content_eligibility(
        content=None, summary="This is a valid pre-existing summary."
    )
    assert result.eligible is True
    assert result.reason == "existing_summary_valid"
    assert result.usable_text == "This is a valid pre-existing summary."


def test_assess_content_empty_existing_summary() -> None:
    result = assess_content_eligibility(
        content="Real article content here about AI developments.",
        summary="",
    )
    assert result.eligible is True
    assert result.reason == "eligible"


def test_assess_content_whitespace_existing_summary_with_usable_content() -> None:
    result = assess_content_eligibility(
        content="Real article content here about AI developments.",
        summary="   \n  ",
    )
    assert result.eligible is True
    assert result.reason == "eligible"


def test_assess_content_usable_content_with_valid_summary_preserved() -> None:
    """Usable content plus a valid existing summary preserves the summary."""
    result = assess_content_eligibility(
        content="Real article content here about AI developments.",
        summary="A valid pre-existing summary.",
    )
    assert result.eligible is True
    assert result.reason == "existing_summary_valid"
    assert result.usable_text == "A valid pre-existing summary."


# ----------------------------------------------------------------------
# Extraction retry scenario
# ----------------------------------------------------------------------


def test_assess_content_awaiting_extraction_can_be_retried() -> None:
    """An article with None content and no summary awaits extraction."""
    result = assess_content_eligibility(content=None, summary=None)
    assert result.eligible is False
    assert result.reason == "awaiting_extraction"


def test_assess_content_after_extraction_becomes_eligible() -> None:
    """Once extraction provides content, the article becomes eligible."""
    before = assess_content_eligibility(content=None, summary=None)
    assert before.eligible is False
    assert before.reason == "awaiting_extraction"

    after = assess_content_eligibility(content="Extracted article content about AI.", summary=None)
    assert after.eligible is True
    assert after.reason == "eligible"


# ----------------------------------------------------------------------
# is_eligible_for_summarize convenience
# ----------------------------------------------------------------------


def test_is_eligible_for_summarize_true() -> None:
    assert is_eligible_for_summarize(content="Valid article content about AI.") is True


def test_is_eligible_for_summarize_false() -> None:
    assert is_eligible_for_summarize(content=None) is False


def test_min_content_chars_positive() -> None:
    assert MIN_CONTENT_CHARS > 0


def test_assess_content_returns_dataclass() -> None:
    result = assess_content_eligibility(content="Valid content here.")
    assert isinstance(result, ContentEligibility)
    assert isinstance(result.eligible, bool)
    assert isinstance(result.reason, str)
