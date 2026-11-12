"""Canonical content-eligibility policy for the deterministic pipeline.

This module is the single source of truth for deciding whether an article's
content is usable as summarization input.  Both the Celery processing path
(``workers/tasks/process.py``) and the deterministic batch runner
(``scripts/scheduled/run_deterministic_batch.py``) must use this policy so
that eligibility is consistent across execution paths.

The validator distinguishes the following categories:

* ``None`` content with no usable summary          -> awaiting_extraction
* empty / whitespace-only content                   -> empty_content
* HTML-only content (scripts, styles, nav, boilerplate) -> html_only_or_boilerplate
* content that is only the title                    -> title_only
* short but meaningful content below the threshold  -> insufficient_content
* valid extracted article content                   -> eligible
* unusable content paired with a valid existing summary -> existing_summary_valid

HTML is normalized with trafilatura (an existing project dependency), which
removes scripts, styles, navigation, and boilerplate while preserving the main
article text.  Traffilatura returns ``None`` or an empty string for markup
that contains no extractable article body, so HTML-only content is never
accepted as meaningful content.

Minimum-content rationale
-------------------------

The minimum-content threshold (``MIN_CONTENT_CHARS``) is deliberately small
(30 characters).  Legitimate short news briefs can be well under 100
characters, and the policy must not reject them.  Trafilatura already strips
boilerplate, so any text that survives extraction and exceeds the threshold
is treated as defensible article content.  The threshold is a sanity check
against near-empty extraction artifacts, not a quality gate.
"""

from __future__ import annotations

from dataclasses import dataclass

import trafilatura

__all__ = [
    "MIN_CONTENT_CHARS",
    "ContentEligibility",
    "assess_content_eligibility",
    "is_eligible_for_summarize",
    "normalize_text",
]

#: Defensible minimum number of characters after HTML/boilerplate removal.
#: Short news briefs are legitimate, so this stays small.
MIN_CONTENT_CHARS: int = 30


def normalize_text(text: str) -> str:
    """Collapse internal whitespace in *text*."""
    return " ".join(text.split())


@dataclass(frozen=True)
class ContentEligibility:
    """Outcome of assessing whether article content is usable."""

    eligible: bool
    """Whether the content is usable as summarization input."""

    reason: str
    """Stable reason string describing the outcome.

    One of: ``awaiting_extraction``, ``empty_content``,
    ``html_only_or_boilerplate``, ``title_only``, ``insufficient_content``,
    ``existing_summary_valid``, ``eligible``.
    """

    usable_text: str | None
    """Extracted/normalized text when eligible, otherwise ``None``."""


def _looks_like_html(text: str) -> bool:
    """Return ``True`` when *text* appears to contain HTML markup."""
    return "<" in text and ">" in text


def _extract_text_from_html(html: str) -> str:
    """Return the main article text from *html*, stripping markup.

    Trafilatura is used for HTML documents (it removes scripts, styles,
    navigation, and boilerplate).  Plain-text content (no HTML tags) is
    returned as-is because trafilatora is designed for full HTML pages and
    returns ``None`` for non-HTML input.

    Returns an empty string for empty, malformed, or markup-only input.
    This function is synchronous; callers running in an async context should
    dispatch via ``asyncio.to_thread`` if they wish to avoid blocking the
    event loop.
    """
    if not html:
        return ""

    # Plain text: return as-is.  Trafilatura does not handle non-HTML input.
    if not _looks_like_html(html):
        return html

    try:
        extracted = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=True,
        )
    except Exception:
        return ""

    if extracted is None:
        return ""

    return str(extracted)


def assess_content_eligibility(
    content: str | None,
    summary: str | None = None,
    title: str | None = None,
) -> ContentEligibility:
    """Assess whether *content* is usable as summarization input.

    The existing summary is consulted when source content is unavailable or
    unusable, so a valid existing summary is never destroyed by empty or
    unusable content.
    """
    summary_normalized = normalize_text(summary) if summary is not None else ""
    has_valid_summary = summary_normalized != ""

    # A valid existing summary makes the article eligible regardless of content
    # usability.  It is never overwritten by empty, unusable, or even usable
    # source content.
    if has_valid_summary:
        return ContentEligibility(True, "existing_summary_valid", summary_normalized)

    # --- content is None: nothing to extract ---------------------------------
    if content is None:
        return ContentEligibility(False, "awaiting_extraction", None)

    # --- empty / whitespace-only content -------------------------------------
    raw_normalized = normalize_text(content)
    if not raw_normalized:
        return ContentEligibility(False, "empty_content", None)

    # --- strip HTML and remove scripts, styles, navigation, boilerplate ------
    extracted_text = normalize_text(_extract_text_from_html(content))

    # --- HTML-only / boilerplate-only: extraction yielded nothing -------------
    if not extracted_text:
        return ContentEligibility(False, "html_only_or_boilerplate", None)

    # --- title-only: extracted text is essentially just the title ------------
    if title is not None:
        title_normalized = normalize_text(title)
        if title_normalized and extracted_text.casefold() == title_normalized.casefold():
            return ContentEligibility(False, "title_only", None)

    # --- short but potentially meaningful ------------------------------------
    if len(extracted_text) < MIN_CONTENT_CHARS:
        return ContentEligibility(False, "insufficient_content", None)

    # --- valid extracted article content -------------------------------------
    return ContentEligibility(True, "eligible", extracted_text)


def is_eligible_for_summarize(
    content: str | None,
    summary: str | None = None,
    title: str | None = None,
) -> bool:
    """Return ``True`` when article content can be summarized."""
    return assess_content_eligibility(content, summary, title).eligible
