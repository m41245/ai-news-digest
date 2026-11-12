from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

from ai_news_digest.application.ai.category_vocabulary import (
    ArticleCategory,
    normalize_category,
)
from ai_news_digest.application.services.content_eligibility import (
    ContentEligibility,
    assess_content_eligibility,
    normalize_text,
)
from ai_news_digest.domain.enums.article_status import ArticleStatus
from ai_news_digest.domain.models.article import Article
from ai_news_digest.domain.models.category import Category
from ai_news_digest.domain.models.topic import Topic

if TYPE_CHECKING:
    from ai_news_digest.domain.ports.article_repository import ArticleRepository
    from ai_news_digest.domain.ports.category_repository import CategoryRepository
    from ai_news_digest.domain.ports.topic_repository import TopicRepository


def _slugify(value: str) -> str:
    """Create a URL-safe slug from a topic name."""
    slug = "".join(char.lower() if char.isalnum() else "-" for char in value.strip()).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug or "topic"


def deterministic_category(text: str) -> str:
    """Return a deterministic category label derived from *text*.

    The label is derived from a stable hash of the normalized text so that the
    same input always maps to the same category. The result is always a valid
    :class:`ArticleCategory` value.
    """
    digest = hashlib.sha256(normalize_text(text).casefold().encode("utf-8")).hexdigest()
    index = int(digest, 16) % len(ArticleCategory)
    return list(ArticleCategory)[index].value


def deterministic_topics(text: str, category: ArticleCategory) -> tuple[str, ...]:
    """Return deterministic topic names for *text* within *category*.

    Topics are derived from the normalized text and the category so the output
    is stable for identical input. At least one topic is always returned.
    """
    normalized = normalize_text(text)
    if not normalized:
        return (category.display_name,)

    tokens = [token for token in normalized.split() if token.isalpha()]
    if not tokens:
        return (category.display_name,)

    # Single deterministic topic per call keeps the topic set stable for tests
    # and downstream consumers that expect a one-to-one article-topic mapping.
    selected = tokens[:1]
    return tuple(selected)


def _truncate(text: str | None, max_length: int) -> str:
    """Truncate *text* to *max_length* characters without breaking words."""
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    truncated = text[: max_length - 1]
    last_space = truncated.rfind(" ")
    if last_space > max_length // 2:
        return truncated[:last_space] + "..."
    return truncated + "..."


async def deterministic_summarize(article: Article) -> Article:
    """Produce a deterministic summary for an article.

    This is a pure in-memory transformation. No database writes occur here; the
    caller is responsible for persisting the returned article.

    An article is only marked ``SUMMARIZED`` when a meaningful, non-empty
    summary can be produced from usable source content or a valid existing
    summary.  Articles with ``None``, empty, whitespace-only, HTML-only,
    boilerplate-only, or title-only content (and no valid existing summary)
    are returned unchanged (status remains ``NEW``) so the caller can detect
    ineligibility and avoid a false successful transition.

    HTML is normalized via trafilatura, which strips scripts, styles,
    navigation, and boilerplate.  HTML tags and scripts are never accepted as
    meaningful article content, and article content is never invented from a
    title.
    """
    if article.status != ArticleStatus.NEW:
        return article

    eligibility: ContentEligibility = assess_content_eligibility(
        content=article.content,
        summary=article.summary,
        title=article.title,
    )

    if not eligibility.eligible:
        # Ineligible content: leave status unchanged (NEW) so the caller can
        # detect ineligibility and avoid a false successful transition.
        return article

    if eligibility.reason == "existing_summary_valid":
        # Preserve the valid existing summary; do not overwrite it with
        # empty or unusable content.
        article.mark_summarized()
        return article

    # Valid extracted content: use the cleaned extracted text as the summary.
    article.summary = _truncate(eligibility.usable_text or "", 8000) or article.summary
    article.mark_summarized()
    return article


async def deterministic_categorize(
    article: Article,
    category_repository: CategoryRepository | None,
    topic_repository: TopicRepository | None,
    article_repository: ArticleRepository | None,
) -> Article:
    """Categorize an article deterministically and persist the result.

    All persistence is performed through the provided repositories using
    flush-only operations. The caller is responsible for committing (or
    rolling back) the shared session once this function returns. If this
    function raises, the caller must roll back the session; no partial state
    is committed by this function.
    """
    category_name = deterministic_category(article.title or article.summary)
    category: Category | None = None
    if category_repository is not None:
        category = await category_repository.get_by_name(category_name)
        if category is None:
            category = Category.create(name=category_name, description=category_name)
            category = await category_repository.create_flush_only(category)

    topic_names = deterministic_topics(
        article.title or article.summary, normalize_category(category_name)
    )
    topic_ids: list[str] = []
    if topic_repository is not None:
        for name in topic_names:
            if not name:
                continue
            slug = _slugify(name)
            existing = await topic_repository.get_by_slug(slug)
            if existing is not None:
                topic_ids.append(existing.id)
            else:
                topic = Topic.create(name=name, slug=slug)
                created = await topic_repository.create_flush_only(topic)
                topic_ids.append(created.id)

    if topic_ids and article_repository is not None:
        await article_repository.replace_topics_flush_only(article.id, topic_ids)

    article.mark_categorized()
    if category is not None:
        article.category_id = category.id
    return article


__all__ = [
    "deterministic_categorize",
    "deterministic_category",
    "deterministic_summarize",
    "deterministic_topics",
    "normalize_text",
]
