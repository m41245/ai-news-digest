from __future__ import annotations

from ai_news_digest.application.use_cases.article.ingest_all_sources import (
    IngestionSummary,
)


class ConsolePrinter:
    """
    Helper responsible for writing application output to the console.
    """

    @staticmethod
    def print_header() -> None:
        print()
        print("=" * 50)
        print(" AI News Digest")
        print("=" * 50)
        print()

    @staticmethod
    def print_summary(
        summary: IngestionSummary,
    ) -> None:
        print(f"Sources processed : {summary.sources_processed}")
        print(f"Articles fetched  : {summary.fetched}")
        print(f"Imported          : {summary.imported}")
        print(f"Skipped           : {summary.skipped}")
        print()
        print("Done.")

    @staticmethod
    def print_error(
        message: str,
    ) -> None:
        print()
        print("ERROR")
        print("-" * 50)
        print(message)
