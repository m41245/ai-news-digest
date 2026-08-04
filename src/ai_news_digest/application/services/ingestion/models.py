from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class IngestionResult:
    """
    Statistics produced by an ingestion run.
    """

    feeds_processed: int
    articles_fetched: int
    articles_inserted: int
    articles_skipped: int
    failed_feeds: int
