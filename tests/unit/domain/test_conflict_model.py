"""
Unit tests for M82 conflict domain models.
"""

from __future__ import annotations

import pytest
from uuid import uuid4

from ai_news_digest.domain.enums.conflict_status import ConflictStatus
from ai_news_digest.domain.enums.conflict_type import ConflictType
from ai_news_digest.domain.models.conflict import Conflict


class TestConflictType:
    def test_numeric_value(self) -> None:
        assert ConflictType.NUMERIC.value == "numeric"

    def test_date_value(self) -> None:
        assert ConflictType.DATE.value == "date"

    def test_event_status_value(self) -> None:
        assert ConflictType.EVENT_STATUS.value == "event_status"

    def test_all_types(self) -> None:
        expected = {
            "numeric",
            "date",
            "event_status",
            "product_attribute",
            "company_statement",
            "availability",
            "announcement",
            "quantity",
            "other",
        }
        actual = {t.value for t in ConflictType}
        assert actual == expected


class TestConflictStatus:
    def test_potential_value(self) -> None:
        assert ConflictStatus.POTENTIAL.value == "potential"

    def test_confirmed_value(self) -> None:
        assert ConflictStatus.CONFIRMED.value == "confirmed"

    def test_dismissed_value(self) -> None:
        assert ConflictStatus.DISMISSED.value == "dismissed"

    def test_insufficient_evidence_value(self) -> None:
        assert ConflictStatus.INSUFFICIENT_EVIDENCE.value == "insufficient_evidence"

    def test_all_statuses(self) -> None:
        expected = {
            "potential",
            "confirmed",
            "dismissed",
            "insufficient_evidence",
        }
        actual = {s.value for s in ConflictStatus}
        assert actual == expected


class TestConflict:
    def test_create_conflict(self) -> None:
        conflict = Conflict.create(
            claim_a_id=uuid4(),
            claim_b_id=uuid4(),
            article_a_id=uuid4(),
            article_b_id=uuid4(),
            source_a_id=uuid4(),
            source_b_id=uuid4(),
            conflict_type=ConflictType.NUMERIC,
            confidence=0.7,
            explanation="Different numeric values.",
            detection_version="v1",
        )
        assert conflict.conflict_type == ConflictType.NUMERIC
        assert conflict.status == ConflictStatus.POTENTIAL
        assert conflict.confidence == 0.7
        assert conflict.explanation == "Different numeric values."
        assert conflict.detection_version == "v1"
        assert conflict.same_source is False

    def test_create_clamps_confidence(self) -> None:
        conflict = Conflict.create(
            claim_a_id=uuid4(),
            claim_b_id=uuid4(),
            article_a_id=uuid4(),
            article_b_id=uuid4(),
            source_a_id=uuid4(),
            source_b_id=uuid4(),
            conflict_type=ConflictType.NUMERIC,
            confidence=1.5,
            explanation="High confidence.",
            detection_version="v1",
        )
        assert conflict.confidence == 1.0

        conflict_low = Conflict.create(
            claim_a_id=uuid4(),
            claim_b_id=uuid4(),
            article_a_id=uuid4(),
            article_b_id=uuid4(),
            source_a_id=uuid4(),
            source_b_id=uuid4(),
            conflict_type=ConflictType.NUMERIC,
            confidence=-0.5,
            explanation="Low confidence.",
            detection_version="v1",
        )
        assert conflict_low.confidence == 0.0

    def test_update_status(self) -> None:
        conflict = Conflict.create(
            claim_a_id=uuid4(),
            claim_b_id=uuid4(),
            article_a_id=uuid4(),
            article_b_id=uuid4(),
            source_a_id=uuid4(),
            source_b_id=uuid4(),
            conflict_type=ConflictType.NUMERIC,
            confidence=0.7,
            explanation="Test.",
            detection_version="v1",
        )
        conflict.update_status(ConflictStatus.CONFIRMED)
        assert conflict.status == ConflictStatus.CONFIRMED

    def test_canonical_pair_deduplication(self) -> None:
        a = uuid4()
        b = uuid4()
        c1 = Conflict.create(
            claim_a_id=a,
            claim_b_id=b,
            article_a_id=uuid4(),
            article_b_id=uuid4(),
            source_a_id=uuid4(),
            source_b_id=uuid4(),
            conflict_type=ConflictType.NUMERIC,
            confidence=0.5,
            explanation="Test.",
            detection_version="v1",
        )
        c2 = Conflict.create(
            claim_a_id=b,
            claim_b_id=a,
            article_a_id=uuid4(),
            article_b_id=uuid4(),
            source_a_id=uuid4(),
            source_b_id=uuid4(),
            conflict_type=ConflictType.NUMERIC,
            confidence=0.5,
            explanation="Test.",
            detection_version="v1",
        )
        assert c1.claim_a_id == c2.claim_b_id
        assert c1.claim_b_id == c2.claim_a_id

    def test_same_source_flag(self) -> None:
        sid = uuid4()
        conflict = Conflict.create(
            claim_a_id=uuid4(),
            claim_b_id=uuid4(),
            article_a_id=uuid4(),
            article_b_id=uuid4(),
            source_a_id=sid,
            source_b_id=sid,
            conflict_type=ConflictType.NUMERIC,
            confidence=0.5,
            explanation="Test.",
            detection_version="v1",
            same_source=True,
        )
        assert conflict.same_source is True


__all__ = ["TestConflictType", "TestConflictStatus", "TestConflict"]
