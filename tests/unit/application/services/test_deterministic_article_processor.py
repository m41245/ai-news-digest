"""Unit tests for deterministic_article_processor."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from ai_news_digest.application.services.deterministic_article_processor import (
    deterministic_categorize,
    deterministic_category,
    deterministic_summarize,
    deterministic_topics,
    normalize_text,
)
from ai_news_digest.domain.enums.article_status import ArticleStatus
from ai_news_digest.domain.models.article import Article


def make_article(status: ArticleStatus = ArticleStatus.NEW) -> Article:
    article = Article.create(
        title="Test Article",
        url=f"https://example.com/{uuid4()}",
        summary="",
        content="Article body content.",
        source_id=uuid4(),
        published_at=datetime.now(UTC),
    )
    article.status = status
    return article


def test_normalize_text_collapses_whitespace() -> None:
    assert normalize_text("  a   b \n c ") == "a b c"


def test_deterministic_category_word_boundary() -> None:
    assert deterministic_category("data modeling techniques") != deterministic_category(
        "new language model released"
    )


async def test_deterministic_summarize_bounds_length() -> None:
    article = make_article()
    article.content = "word " * 10000
    result = await deterministic_summarize(article)
    assert len(result.summary) <= 8000
    assert result.status == ArticleStatus.SUMMARIZED


async def test_deterministic_summarize_uses_existing_summary() -> None:
    article = make_article()
    article.summary = "Existing summary text."
    result = await deterministic_summarize(article)
    assert result.summary == "Existing summary text."
    assert result.status == ArticleStatus.SUMMARIZED


async def test_deterministic_categorize_no_repositories() -> None:
    article = make_article()
    result = await deterministic_categorize(article, None, None, None)
    assert result.status == ArticleStatus.CATEGORIZED
    assert result.category_id is None


async def test_deterministic_categorize_category_failure_propagates() -> None:
    repo = AsyncMock()
    repo.get_by_name.return_value = None
    repo.create_flush_only.side_effect = RuntimeError("db fail")
    article = make_article()
    with pytest.raises(RuntimeError, match="db fail"):
        await deterministic_categorize(article, repo, None, None)


async def test_deterministic_categorize_topic_create_failure_propagates() -> None:
    category_repo = AsyncMock()
    category = MagicMock()
    category.id = uuid4()
    category_repo.get_by_name.return_value = category

    topic_repo = AsyncMock()
    topic_repo.get_by_slug.return_value = None
    topic_repo.create_flush_only.side_effect = RuntimeError("topic db fail")

    article_repo = AsyncMock()
    article = make_article()
    with pytest.raises(RuntimeError, match="topic db fail"):
        await deterministic_categorize(article, category_repo, topic_repo, article_repo)


async def test_deterministic_categorize_replace_topics_failure_propagates() -> None:
    category_repo = AsyncMock()
    category = MagicMock()
    category.id = uuid4()
    category_repo.get_by_name.return_value = category

    topic_repo = AsyncMock()
    existing_topic = MagicMock()
    existing_topic.id = uuid4()
    existing_topic.name = "OpenAI"
    topic_repo.get_by_slug.return_value = existing_topic

    article_repo = AsyncMock()
    article_repo.replace_topics_flush_only.side_effect = RuntimeError("replace fail")

    article = make_article()
    article.topics = ("OpenAI",)
    with pytest.raises(RuntimeError, match="replace fail"):
        await deterministic_categorize(article, category_repo, topic_repo, article_repo)


def test_deterministic_topics_fallback() -> None:
    from ai_news_digest.application.ai.category_vocabulary import ArticleCategory

    topics = deterministic_topics("nothing relevant here", ArticleCategory.AI_RESEARCH)
    assert len(topics) >= 1


# ----------------------------------------------------------------------
# Empty-content ineligibility tests
# ----------------------------------------------------------------------


def make_article_with_content(
    status: ArticleStatus = ArticleStatus.NEW,
    content: str | None = None,
    summary: str | None = None,
    title: str = "Test Article",
) -> Article:
    article = Article.create(
        title=title,
        url=f"https://example.com/{uuid4()}",
        summary=summary or "",
        content=content,
        source_id=uuid4(),
        published_at=datetime.now(UTC),
    )
    article.status = status
    return article


async def test_deterministic_summarize_content_none_remains_new() -> None:
    article = make_article_with_content(content=None, summary=None)
    result = await deterministic_summarize(article)
    assert result.status == ArticleStatus.NEW
    assert result.summary is None or result.summary == ""


async def test_deterministic_summarize_content_empty_remains_new() -> None:
    article = make_article_with_content(content="", summary=None)
    result = await deterministic_summarize(article)
    assert result.status == ArticleStatus.NEW


async def test_deterministic_summarize_content_whitespace_only_remains_new() -> None:
    article = make_article_with_content(content="   \n  \t  ", summary=None)
    result = await deterministic_summarize(article)
    assert result.status == ArticleStatus.NEW


async def test_deterministic_summarize_summary_whitespace_only_remains_new() -> None:
    article = make_article_with_content(content=None, summary="   \n  ")
    result = await deterministic_summarize(article)
    assert result.status == ArticleStatus.NEW


async def test_deterministic_summarize_valid_content_produces_summary() -> None:
    article = make_article_with_content(
        content="This is a real article with meaningful content about artificial intelligence."
    )
    result = await deterministic_summarize(article)
    assert result.status == ArticleStatus.SUMMARIZED
    assert result.summary is not None
    assert len(result.summary) > 0


async def test_deterministic_summarize_valid_existing_summary_stays_summarized() -> None:
    article = make_article_with_content(content=None, summary="Existing summary text.")
    result = await deterministic_summarize(article)
    assert result.status == ArticleStatus.SUMMARIZED
    assert result.summary == "Existing summary text."


async def test_deterministic_summarize_not_new_not_transitioned() -> None:
    article = make_article_with_content(status=ArticleStatus.SUMMARIZED, content="Some content.")
    result = await deterministic_summarize(article)
    assert result.status == ArticleStatus.SUMMARIZED


# ----------------------------------------------------------------------
# Content eligibility through deterministic_summarize
# ----------------------------------------------------------------------


async def test_deterministic_summarize_html_content_is_stripped() -> None:
    """HTML is normalized via trafilatura; tags are not stored as summary."""
    article = make_article_with_content(
        content="<html><body><p>Breaking news about AI developments today.</p></body></html>",
        summary=None,
    )
    result = await deterministic_summarize(article)
    assert result.status == ArticleStatus.SUMMARIZED
    assert result.summary is not None
    assert "<html>" not in result.summary
    assert "<body>" not in result.summary
    assert "<p>" not in result.summary
    assert "Breaking news" in result.summary


async def test_deterministic_summarize_html_script_only_remains_new() -> None:
    """Script-only HTML is not accepted as meaningful content."""
    article = make_article_with_content(content="<script>alert('xss')</script>", summary=None)
    result = await deterministic_summarize(article)
    assert result.status == ArticleStatus.NEW
    assert result.summary is None or result.summary == ""


async def test_deterministic_summarize_html_style_only_remains_new() -> None:
    """Style-only HTML is not accepted as meaningful content."""
    article = make_article_with_content(
        content="<style>body { display: none; }</style>", summary=None
    )
    result = await deterministic_summarize(article)
    assert result.status == ArticleStatus.NEW


async def test_deterministic_summarize_malformed_html_remains_new() -> None:
    """Malformed HTML is not accepted as meaningful content."""
    article = make_article_with_content(
        content="<broken><unclosed><div>no proper structure", summary=None
    )
    result = await deterministic_summarize(article)
    assert result.status == ArticleStatus.NEW


async def test_deterministic_summarize_title_only_remains_new() -> None:
    """Content that is only the title does not produce a summary."""
    article = make_article_with_content(
        content="Breaking News: AI Act Signed",
        summary=None,
        title="Breaking News: AI Act Signed",
    )
    result = await deterministic_summarize(article)
    assert result.status == ArticleStatus.NEW


async def test_deterministic_summarize_title_only_with_valid_summary_preserved() -> None:
    """Title-only content with a valid existing summary keeps the summary."""
    article = make_article_with_content(
        content="Breaking News: AI Act Signed",
        summary="The EU AI Act has been signed into law.",
        title="Breaking News: AI Act Signed",
    )
    result = await deterministic_summarize(article)
    assert result.status == ArticleStatus.SUMMARIZED
    assert result.summary == "The EU AI Act has been signed into law."


async def test_deterministic_summarize_plain_text_above_threshold() -> None:
    """Plain text content that clears the minimum is eligible."""
    article = make_article_with_content(
        content="AI startup raises $5M in seed funding.", summary=None
    )
    result = await deterministic_summarize(article)
    assert result.status == ArticleStatus.SUMMARIZED
    assert result.summary is not None


async def test_deterministic_summarize_existing_summary_not_overwritten() -> None:
    """A valid existing summary is not overwritten by usable content."""
    article = make_article_with_content(
        content="New article content about AI.",
        summary="Pre-existing valid summary.",
    )
    result = await deterministic_summarize(article)
    assert result.status == ArticleStatus.SUMMARIZED
    assert result.summary == "Pre-existing valid summary."


async def test_deterministic_summarize_usable_content_preserves_valid_summary() -> None:
    """Usable content does not overwrite a valid existing summary."""
    article = make_article_with_content(
        content="This is a real article with meaningful content about artificial intelligence developments.",
        summary="Pre-existing valid summary.",
    )
    result = await deterministic_summarize(article)
    assert result.status == ArticleStatus.SUMMARIZED
    assert result.summary == "Pre-existing valid summary."


async def test_deterministic_summarize_unicode_punctuation() -> None:
    """Content with legitimate punctuation and Unicode is accepted."""
    article = make_article_with_content(
        content="Café résumé naïve — AI & ML: 2026 update.", summary=None
    )
    result = await deterministic_summarize(article)
    assert result.status == ArticleStatus.SUMMARIZED
    assert result.summary is not None
    assert "Café" in result.summary


async def test_deterministic_summarize_extraction_retry_becomes_eligible() -> None:
    """An article awaiting extraction becomes eligible once content arrives."""
    article = make_article_with_content(content=None, summary=None)
    result = await deterministic_summarize(article)
    assert result.status == ArticleStatus.NEW

    article.content = "Extracted article content about AI developments."
    result = await deterministic_summarize(article)
    assert result.status == ArticleStatus.SUMMARIZED
