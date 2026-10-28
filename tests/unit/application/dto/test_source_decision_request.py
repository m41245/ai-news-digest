from __future__ import annotations

from uuid import uuid4

from ai_news_digest.application.dto.source.decision_request import SourceDecisionRequest


def test_source_decision_request_defaults() -> None:
    request = SourceDecisionRequest(id=uuid4(), reason="ok")

    assert request.reason == "ok"
    assert request.decision is None


def test_source_decision_request_decision_override() -> None:
    request = SourceDecisionRequest(id=uuid4(), reason="ok", decision="REJECT")

    assert request.decision == "REJECT"
