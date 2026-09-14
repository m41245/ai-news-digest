"""
Unit tests for M82 deterministic conflict detection.
"""

from __future__ import annotations

import pytest
from uuid import uuid4

from ai_news_digest.domain.enums.claim_type import ClaimType
from ai_news_digest.domain.models.claim import Claim
from ai_news_digest.application.evaluation.conflict_detector import (
    DeterministicResult,
    detect_date_conflict,
    detect_event_state_conflict,
    detect_numeric_conflict,
    run_deterministic_detection,
)


def _make_claim(text: str, claim_type: ClaimType = ClaimType.FACT) -> Claim:
    return Claim.create(
        article_id=uuid4(),
        source_id=uuid4(),
        claim_text=text,
        claim_type=claim_type,
    )


class TestNumericConflict:
    def test_conflict_detected(self) -> None:
        a = _make_claim("Model has 70B parameters.")
        b = _make_claim("Model has 120B parameters.")
        result = detect_numeric_conflict(a, b)
        assert result is not None
        assert result.conflict_type.value == "numeric"
        assert result.status.value == "potential"

    def test_same_values_no_conflict(self) -> None:
        a = _make_claim("Model has 70B parameters.")
        b = _make_claim("Model has 70B parameters.")
        result = detect_numeric_conflict(a, b)
        assert result is None

    def test_no_numbers_no_conflict(self) -> None:
        a = _make_claim("Model launched.")
        b = _make_claim("Model released.")
        result = detect_numeric_conflict(a, b)
        assert result is None

    def test_percentage_conflict(self) -> None:
        a = _make_claim("Market share is 10%.")
        b = _make_claim("Market share is 30%.")
        result = detect_numeric_conflict(a, b)
        assert result is not None

    def test_overlapping_ranges_no_conflict(self) -> None:
        a = _make_claim("Users are between 100 and 200.")
        b = _make_claim("Users are between 150 and 250.")
        result = detect_numeric_conflict(a, b)
        assert result is None


class TestDateConflict:
    def test_conflict_detected(self) -> None:
        a = _make_claim("Product launches on June 1.")
        b = _make_claim("Product launches on June 15.")
        result = detect_date_conflict(a, b)
        assert result is not None
        assert result.conflict_type.value == "date"

    def test_same_date_no_conflict(self) -> None:
        a = _make_claim("Event on June 1, 2024.")
        b = _make_claim("Event on June 1, 2024.")
        result = detect_date_conflict(a, b)
        assert result is None

    def test_no_dates_no_conflict(self) -> None:
        a = _make_claim("Company announced a product.")
        b = _make_claim("Company released a product.")
        result = detect_date_conflict(a, b)
        assert result is None


class TestEventStateConflict:
    def test_conflict_detected(self) -> None:
        a = _make_claim("Company plans acquisition.", claim_type=ClaimType.BUSINESS)
        b = _make_claim("Company completed acquisition.", claim_type=ClaimType.BUSINESS)
        result = detect_event_state_conflict(a, b)
        assert result is not None
        assert result.conflict_type.value == "event_status"

    def test_same_state_no_conflict(self) -> None:
        a = _make_claim("Product launched.", claim_type=ClaimType.ANNOUNCEMENT)
        b = _make_claim("Product launched.", claim_type=ClaimType.ANNOUNCEMENT)
        result = detect_event_state_conflict(a, b)
        assert result is None

    def test_compatible_states_no_conflict(self) -> None:
        a = _make_claim("Product announced.", claim_type=ClaimType.ANNOUNCEMENT)
        b = _make_claim("Product released.", claim_type=ClaimType.ANNOUNCEMENT)
        result = detect_event_state_conflict(a, b)
        assert result is None


class TestRunDeterministicDetection:
    def test_numeric_detected(self) -> None:
        a = _make_claim("Model has 70B parameters.")
        b = _make_claim("Model has 120B parameters.")
        result = run_deterministic_detection(a, b)
        assert result is not None
        assert result.conflict_type.value == "numeric"

    def test_no_detection_when_unrelated(self) -> None:
        a = _make_claim("Company A released product X.")
        b = _make_claim("Company B released product Y.")
        result = run_deterministic_detection(a, b)
        assert result is None


__all__ = [
    "TestNumericConflict",
    "TestDateConflict",
    "TestEventStateConflict",
    "TestRunDeterministicDetection",
]
