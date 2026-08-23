"""
Unit tests for CLI printer.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from ai_news_digest.application.use_cases.article.ingest_all_sources import IngestionSummary
from ai_news_digest.cli.printer import ConsolePrinter


@pytest.fixture
def printer() -> ConsolePrinter:
    """Create a ConsolePrinter instance."""
    return ConsolePrinter()


@pytest.fixture
def sample_summary() -> IngestionSummary:
    """Create a sample IngestionSummary."""
    return IngestionSummary(
        sources_processed=5,
        fetched=100,
        imported=95,
        skipped=5,
    )


def test_console_printer_print_header(printer: ConsolePrinter) -> None:
    """Test print_header method."""
    with patch("builtins.print") as mock_print:
        printer.print_header()

        assert mock_print.call_count >= 5


def test_console_printer_print_summary(
    printer: ConsolePrinter, sample_summary: IngestionSummary
) -> None:
    """Test print_summary method."""
    with patch("builtins.print") as mock_print:
        printer.print_summary(sample_summary)

        assert mock_print.call_count >= 6


def test_console_printer_print_error(printer: ConsolePrinter) -> None:
    """Test print_error method."""
    with patch("builtins.print") as mock_print:
        printer.print_error("Test error message")

        assert mock_print.call_count >= 4


def test_console_printer_print_summary_zero_values(printer: ConsolePrinter) -> None:
    """Test print_summary with zero values."""
    summary = IngestionSummary(
        sources_processed=0,
        fetched=0,
        imported=0,
        skipped=0,
    )

    with patch("builtins.print") as mock_print:
        printer.print_summary(summary)

        assert mock_print.call_count >= 6
