"""
Unit tests for IngestAllSourcesUseCase.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from ai_news_digest.application.use_cases.article.ingest_all_sources import (
    IngestAllSourcesUseCase,
    IngestionSummary,
)
from ai_news_digest.application.use_cases.article.ingest_from_source import (
    IngestionResult,
)
from ai_news_digest.domain.models.source import Source


@pytest.fixture
def sample_sources() -> list[Source]:
    """Create sample sources for testing."""
    return [
        Source.create(
            name="Source 1",
            feed_url="https://example1.com/feed.xml",
            is_active=True,
        ),
        Source.create(
            name="Source 2",
            feed_url="https://example2.com/feed.xml",
            is_active=True,
        ),
        Source.create(
            name="Source 3",
            feed_url="https://example3.com/feed.xml",
            is_active=True,
        ),
    ]


async def test_ingest_all_sources_success(
    sample_sources: list[Source],
    mock_source_repository: AsyncMock,
    mock_ingest_from_source: AsyncMock,
) -> None:
    """Test ingesting from all enabled sources."""
    # Arrange
    mock_source_repository.list_enabled.return_value = sample_sources

    # Mock different results for each source
    async def ingest_side_effect(source: Source) -> IngestionResult:
        if source.name == "Source 1":
            return IngestionResult(fetched=5, imported=5, skipped=0)
        elif source.name == "Source 2":
            return IngestionResult(fetched=3, imported=2, skipped=1)
        else:
            return IngestionResult(fetched=4, imported=3, skipped=1)

    mock_ingest_from_source.execute.side_effect = ingest_side_effect

    use_case = IngestAllSourcesUseCase(
        source_repository=mock_source_repository,
        ingest_from_source=mock_ingest_from_source,
    )

    # Act
    result = await use_case.execute()

    # Assert
    assert result.sources_processed == 3
    assert result.sources_failed == 0
    assert result.fetched == 12  # 5 + 3 + 4
    assert result.imported == 10  # 5 + 2 + 3
    assert result.skipped == 2  # 0 + 1 + 1
    mock_source_repository.list_enabled.assert_called_once()
    assert mock_ingest_from_source.execute.call_count == 3


async def test_ingest_all_sources_no_sources(
    mock_source_repository: AsyncMock,
    mock_ingest_from_source: AsyncMock,
) -> None:
    """Test ingesting when no enabled sources exist."""
    # Arrange
    mock_source_repository.list_enabled.return_value = []

    use_case = IngestAllSourcesUseCase(
        source_repository=mock_source_repository,
        ingest_from_source=mock_ingest_from_source,
    )

    # Act
    result = await use_case.execute()

    # Assert
    assert result.sources_processed == 0
    assert result.sources_failed == 0
    assert result.fetched == 0
    assert result.imported == 0
    assert result.skipped == 0
    mock_ingest_from_source.execute.assert_not_called()


async def test_ingest_all_sources_single_source(
    mock_source_repository: AsyncMock,
    mock_ingest_from_source: AsyncMock,
) -> None:
    """Test ingesting from a single enabled source."""
    # Arrange
    source = Source.create(
        name="Single Source",
        feed_url="https://example.com/feed.xml",
        is_active=True,
    )
    mock_source_repository.list_enabled.return_value = [source]
    mock_ingest_from_source.execute.return_value = IngestionResult(
        fetched=10, imported=8, skipped=2
    )

    use_case = IngestAllSourcesUseCase(
        source_repository=mock_source_repository,
        ingest_from_source=mock_ingest_from_source,
    )

    # Act
    result = await use_case.execute()

    # Assert
    assert result.sources_processed == 1
    assert result.fetched == 10
    assert result.imported == 8
    assert result.skipped == 2
    mock_ingest_from_source.execute.assert_called_once_with(source)


async def test_ingest_all_sources_all_skipped(
    sample_sources: list[Source],
    mock_source_repository: AsyncMock,
    mock_ingest_from_source: AsyncMock,
) -> None:
    """Test ingesting when all articles are skipped (duplicates)."""
    # Arrange
    mock_source_repository.list_enabled.return_value = sample_sources
    mock_ingest_from_source.execute.return_value = IngestionResult(fetched=5, imported=0, skipped=5)

    use_case = IngestAllSourcesUseCase(
        source_repository=mock_source_repository,
        ingest_from_source=mock_ingest_from_source,
    )

    # Act
    result = await use_case.execute()

    # Assert
    assert result.sources_processed == 3
    assert result.fetched == 15  # 5 * 3
    assert result.imported == 0
    assert result.skipped == 15  # 5 * 3


async def test_ingest_all_sources_one_failing_source_continues(
    sample_sources: list[Source],
    mock_source_repository: AsyncMock,
    mock_ingest_from_source: AsyncMock,
) -> None:
    """A failing source must not stop processing of other sources."""
    # Arrange
    mock_source_repository.list_enabled.return_value = sample_sources

    call_count = 0

    async def ingest_side_effect(source: Source) -> IngestionResult:
        nonlocal call_count
        call_count += 1
        if source.name == "Source 2":
            raise ConnectionError("feed unavailable")
        return IngestionResult(fetched=2, imported=2, skipped=0)

    mock_ingest_from_source.execute.side_effect = ingest_side_effect

    use_case = IngestAllSourcesUseCase(
        source_repository=mock_source_repository,
        ingest_from_source=mock_ingest_from_source,
    )

    # Act
    result = await use_case.execute()

    # Assert
    assert result.sources_processed == 2
    assert result.sources_failed == 1
    assert result.imported == 4
    assert call_count == 3


async def test_ingest_all_sources_summary_defaults() -> None:
    """IngestionSummary defaults to zero across all counters."""
    summary = IngestionSummary()

    assert summary.sources_processed == 0
    assert summary.sources_failed == 0
    assert summary.fetched == 0
    assert summary.imported == 0
    assert summary.skipped == 0
    assert summary.failed == 0
