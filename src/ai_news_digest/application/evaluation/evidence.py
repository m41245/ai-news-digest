from __future__ import annotations

from typing import Any


class ArticleReference:
    """Lightweight reference to an article supporting a detected change."""

    def __init__(self, article_id: str) -> None:
        self.article_id = article_id


class EvidenceItem:
    """Wrapper for a detected change with its supporting evidence."""

    def __init__(
        self,
        description: str,
        detection_method: str,
        evidence_type: str,
        fields_used: list[str],
        items: list[Any],
        confidence: str,
        reason: str,
        detected_at: str | None,
    ) -> None:
        self.description = description
        self.detection_method = detection_method
        self.evidence_type = evidence_type
        self.fields_used = fields_used
        self.items = items
        self.evidence = [ArticleReference(article_id=str(item.get("id"))) for item in items]
        self.confidence = confidence
        self.reason = reason
        self.detected_at = detected_at

    def to_dict(self) -> dict[str, Any]:
        """Serialize the evidence item for API responses."""
        return {
            "description": self.description,
            "detection_method": self.detection_method,
            "evidence_type": self.evidence_type,
            "fields_used": self.fields_used,
            "items": self.items,
            "evidence": [
                {"article_id": ref.article_id} for ref in self.evidence
            ],
            "confidence": self.confidence,
            "reason": self.reason,
            "detected_at": self.detected_at,
        }


def build_change_evidence(
    *,
    description: str,
    detection_method: str,
    evidence_type: str,
    fields_used: list[str],
    items: list[Any],
    confidence: str,
    reason: str,
    detected_at: str | None,
) -> EvidenceItem:
    """Wrap a detected change with its supporting evidence."""
    return EvidenceItem(
        description=description,
        detection_method=detection_method,
        evidence_type=evidence_type,
        fields_used=fields_used,
        items=items,
        confidence=confidence,
        reason=reason,
        detected_at=detected_at,
    )
