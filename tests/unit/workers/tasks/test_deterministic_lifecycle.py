"""
Regression tests for the deterministic article lifecycle.

The audit surfaced an apparent inconsistency: one section described the
deterministic path as summarize -> categorize -> analyze, while another implied
NEW -> SUMMARIZED -> ANALYZED with CATEGORIZED skipped. The actual code keeps
CATEGORIZED in the path, so these tests lock that behavior down.

They exercise the worker task implementations directly against a mock
container so the lifecycle transitions are verified without a database.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from ai_news_digest.domain.enums.article_status import ArticleStatus
from ai_news_digest.workers.tasks import process
from tests.unit.workers.tasks.conftest import (
    container_generator,
    make_article,
)


async def test_summarize_deterministic_transitions_new_to_summarized(
    mock_container: MagicMock,
) -> None:
    """A NEW article becomes SUMMARIZED through the deterministic summarizer."""
    article = make_article(ArticleStatus.NEW)
    mock_container.article_repository.get_by_id.return_value = article
    mock_container.summarize_article = None

    with patch.object(process, "get_container", container_generator(mock_container)):
        result = await process.summarize_article(article.id)

    assert result == {
        "status": "completed",
        "article_id": str(article.id),
        "article_status": "summarized",
    }
    assert article.status == ArticleStatus.SUMMARIZED


async def test_categorize_deterministic_transitions_summarized_to_categorized(
    mock_container: MagicMock,
) -> None:
    """A SUMMARIZED article becomes CATEGORIZED through the deterministic path."""
    article = make_article(ArticleStatus.SUMMARIZED)
    mock_container.article_repository.get_by_id.return_value = article
    mock_container.categorize_article = None

    with patch.object(process, "get_container", container_generator(mock_container)):
        result = await process.categorize_article(article.id)

    assert result == {
        "status": "completed",
        "article_id": str(article.id),
        "article_status": "categorized",
    }
    assert article.status == ArticleStatus.CATEGORIZED


async def test_analyze_deterministic_passes_through_categorized(
    mock_container: MagicMock,
) -> None:
    """The deterministic analyze path persists CATEGORIZED before ANALYZED."""
    article = make_article(ArticleStatus.NEW)
    mock_container.article_repository.get_by_id.return_value = article
    mock_container.analyze_article = None
    mock_container.analyze_and_materialize = None

    seen_categorized = False

    async def _fake_categorize(article, *_args, **_kwargs):
        nonlocal seen_categorized
        article.mark_categorized()
        seen_categorized = True
        return article

    with (
        patch.object(process, "get_container", container_generator(mock_container)),
        patch(
            "ai_news_digest.application.services.deterministic_article_processor.deterministic_categorize",
            side_effect=_fake_categorize,
        ),
    ):
        result = await process.analyze_article(article.id)

    assert result["status"] == "completed"
    assert result["article_status"] == "analyzed"
    assert seen_categorized is True
    assert article.status == ArticleStatus.ANALYZED


async def test_process_article_deterministic_lifecycle_new_to_categorized(
    mock_container: MagicMock,
) -> None:
    """process_article runs summarize then categorize, ending at CATEGORIZED."""
    article = make_article(ArticleStatus.NEW)
    mock_container.article_repository.get_by_id.return_value = article
    mock_container.process_article = None

    observed: list[str] = []

    async def _capture_update(updated):
        observed.append(updated.status)
        return updated

    mock_container.article_repository.update_flush_only.side_effect = _capture_update

    with patch.object(process, "get_container", container_generator(mock_container)):
        result = await process.process_article(article.id)

    assert result["status"] == "completed"
    assert result["article_status"] == "categorized"
    # The single persisted state is the final CATEGORIZED state; the
    # intermediate SUMMARIZED state is applied to the in-memory article
    # before categorization runs, so the persisted row reflects the end state.
    assert observed == [ArticleStatus.CATEGORIZED]
    assert article.status == ArticleStatus.CATEGORIZED


async def test_deterministic_summarize_is_idempotent_on_summarized(
    mock_container: MagicMock,
) -> None:
    """A SUMMARIZED article is not resummarized by the deterministic summarizer."""
    article = make_article(ArticleStatus.SUMMARIZED)
    mock_container.article_repository.get_by_id.return_value = article
    mock_container.summarize_article = None

    with patch.object(process, "get_container", container_generator(mock_container)):
        result = await process.summarize_article(article.id)

    assert result["status"] == "already_processed"


async def test_deterministic_categorize_is_idempotent_on_categorized(
    mock_container: MagicMock,
) -> None:
    """A CATEGORIZED article is not recategorized by the deterministic path."""
    article = make_article(ArticleStatus.CATEGORIZED)
    mock_container.article_repository.get_by_id.return_value = article
    mock_container.categorize_article = None

    with patch.object(process, "get_container", container_generator(mock_container)):
        result = await process.categorize_article(article.id)

    assert result["status"] == "not_ready"
