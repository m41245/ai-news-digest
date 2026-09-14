"""
Unit tests for M82 conflict explanation utilities.
"""

from __future__ import annotations

import pytest

from ai_news_digest.application.evaluation.conflict_explanation import (
    build_conflict_explanation,
)
from ai_news_digest.domain.enums.conflict_type import ConflictType


class TestBuildConflictExplanation:
    def test_numeric_explanation(self) -> None:
        explanation = build_conflict_explanation(
            ConflictType.NUMERIC,
            "Model has 70B parameters.",
            "Model has 120B parameters.",
        )
        assert "different numeric values" in explanation.lower()

    def test_date_explanation(self) -> None:
        explanation = build_conflict_explanation(
            ConflictType.DATE,
            "Launches June 1.",
            "Launches June 15.",
        )
        assert "different dates" in explanation.lower()

    def test_event_status_explanation(self) -> None:
        explanation = build_conflict_explanation(
            ConflictType.EVENT_STATUS,
            "Planned acquisition.",
            "Completed acquisition.",
        )
        assert "incompatible event statuses" in explanation.lower()

    def test_extra_detail_appended(self) -> None:
        explanation = build_conflict_explanation(
            ConflictType.NUMERIC,
            "Model has 70B parameters.",
            "Model has 120B parameters.",
            extra_detail=" Same model.",
        )
        assert "same model" in explanation.lower()

    def test_other_explanation(self) -> None:
        explanation = build_conflict_explanation(
            ConflictType.OTHER,
            "Some claim.",
            "Another claim.",
        )
        assert "incompatible facts" in explanation.lower()


__all__ = ["TestBuildConflictExplanation"]
