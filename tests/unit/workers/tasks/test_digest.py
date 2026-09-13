"""
Unit tests for ``workers/tasks/digest.py`` (``generate_daily_digest``).
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from ai_news_digest.application.use_cases.digest.generate_intelligent_digest import (
    IntelligentDigestResult,
)
from ai_news_digest.core.exceptions import ValidationError
from ai_news_digest.workers.celery_app import celery_app
from ai_news_digest.workers.tasks import digest
from tests.unit.workers.tasks.conftest import container_generator


async def test_generate_daily_digest_success(mock_container: MagicMock) -> None:
    """A successful run returns the digest metadata dict."""
    now = datetime.now(UTC)
    digest_id = uuid4()
    mock_container.generate_intelligent_digest.execute.return_value = IntelligentDigestResult(
        digest_id=str(digest_id),
        generated_at=now,
        candidate_count=5,
        story_count=3,
        top_story_cluster_id=None,
        generation_method="ai",
        provider="openai",
        model="gpt-4o-mini",
        fallback_used=False,
    )
    mock_container.digest_repository.get_by_title.return_value = None

    with patch.object(digest, "get_container", container_generator(mock_container)):
        result = await digest.generate_daily_digest()

    assert result["status"] == "completed"
    assert result["digest_id"] == str(digest_id)
    assert result["generation_method"] == "ai"
    assert result["fallback_used"] == "False"


async def test_generate_daily_digest_value_error_skipped(
    mock_container: MagicMock,
) -> None:
    """A ``ValidationError`` from the use case is converted into a ``skipped`` status."""
    mock_container.generate_intelligent_digest.execute.side_effect = ValidationError("no articles")
    mock_container.digest_repository.get_by_title.return_value = None

    with patch.object(digest, "get_container", container_generator(mock_container)):
        result = await digest.generate_daily_digest()

    assert result == {
        "status": "skipped",
        "reason": "no_eligible_articles",
    }


async def test_generate_daily_digest_validation_error_propagates(
    mock_container: MagicMock,
) -> None:
    """
    Defect guard: only ``core.exceptions.ValidationError`` is caught and turned
    into a ``skipped`` status. Any other ``Exception`` (e.g. ``ValueError``)
    propagated by the use case falls through to the generic handler and is
    re-raised (triggering a retry) rather than returning ``skipped``. This test
    pins that actual behaviour.
    """
    mock_container.generate_intelligent_digest.execute.side_effect = ValueError(
        "No digest-eligible articles were found."
    )
    mock_container.digest_repository.get_by_title.return_value = None

    with (
        patch.object(digest, "get_container", container_generator(mock_container)),
        pytest.raises(ValueError),
    ):
        await digest.generate_daily_digest()


async def test_generate_daily_digest_generic_error_propagates(
    mock_container: MagicMock,
) -> None:
    """An unexpected error is logged and re-raised by the task wrapper."""
    mock_container.generate_intelligent_digest.execute.side_effect = RuntimeError("boom")
    mock_container.digest_repository.get_by_title.return_value = None

    with (
        patch.object(digest, "get_container", container_generator(mock_container)),
        pytest.raises(RuntimeError, match="boom"),
    ):
        await digest.generate_daily_digest()


def test_generate_daily_digest_registration() -> None:
    """The task is registered with the expected name and retries."""
    assert digest.generate_daily_digest.name == "workers.tasks.digest.generate_daily_digest"
    assert digest.generate_daily_digest.name in celery_app.tasks
    assert digest.generate_daily_digest.max_retries == 3
    assert digest.generate_daily_digest.default_retry_delay == 60
