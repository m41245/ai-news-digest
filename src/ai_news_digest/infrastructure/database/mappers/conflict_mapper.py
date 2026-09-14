from __future__ import annotations

import json
from uuid import UUID

from ai_news_digest.domain.enums.conflict_status import ConflictStatus
from ai_news_digest.domain.enums.conflict_type import ConflictType
from ai_news_digest.domain.models.conflict import Conflict
from ai_news_digest.infrastructure.database.models.conflict_model import (
    ConflictModel,
)


class ConflictMapper:
    """
    Maps between Conflict domain objects and ConflictModel ORM entities.
    """

    @staticmethod
    def to_model(conflict: Conflict) -> ConflictModel:
        """Convert a domain Conflict into a new ORM ConflictModel."""
        return ConflictModel(
            id=str(conflict.id),
            claim_a_id=str(conflict.claim_a_id),
            claim_b_id=str(conflict.claim_b_id),
            article_a_id=str(conflict.article_a_id),
            article_b_id=str(conflict.article_b_id),
            source_a_id=str(conflict.source_a_id),
            source_b_id=str(conflict.source_b_id),
            conflict_type=conflict.conflict_type.value,
            status=conflict.status.value,
            confidence=conflict.confidence,
            explanation=conflict.explanation,
            detection_version=conflict.detection_version,
            story_cluster_id=str(conflict.story_cluster_id) if conflict.story_cluster_id else None,
            same_source=conflict.same_source,
            conflict_metadata=json.dumps(conflict.metadata, ensure_ascii=False)
            if conflict.metadata
            else None,
        )

    @staticmethod
    def update_model(model: ConflictModel, conflict: Conflict) -> None:
        """Update an existing ORM model from a domain Conflict."""
        model.status = conflict.status.value
        model.confidence = conflict.confidence
        model.explanation = conflict.explanation
        model.story_cluster_id = (
            str(conflict.story_cluster_id) if conflict.story_cluster_id else None
        )
        model.same_source = conflict.same_source
        model.conflict_metadata = (
            json.dumps(conflict.metadata, ensure_ascii=False)
            if conflict.metadata
            else None
        )

    @staticmethod
    def to_domain(model: ConflictModel) -> Conflict:
        """Convert an ORM ConflictModel into a domain Conflict."""
        try:
            conflict_type = ConflictType(model.conflict_type)
        except ValueError:
            conflict_type = ConflictType.OTHER

        try:
            conflict_status = ConflictStatus(model.status)
        except ValueError:
            conflict_status = ConflictStatus.POTENTIAL

        metadata: dict[str, str] = {}
        if model.conflict_metadata:
            try:
                parsed = json.loads(model.conflict_metadata)
                if isinstance(parsed, dict):
                    metadata = {str(k): str(v) for k, v in parsed.items()}
            except (ValueError, TypeError):
                pass

        return Conflict(
            id=UUID(model.id),
            claim_a_id=UUID(model.claim_a_id),
            claim_b_id=UUID(model.claim_b_id),
            article_a_id=UUID(model.article_a_id),
            article_b_id=UUID(model.article_b_id),
            source_a_id=UUID(model.source_a_id),
            source_b_id=UUID(model.source_b_id),
            conflict_type=conflict_type,
            status=conflict_status,
            confidence=model.confidence,
            explanation=model.explanation,
            detection_version=model.detection_version,
            story_cluster_id=UUID(model.story_cluster_id) if model.story_cluster_id else None,
            same_source=model.same_source,
            metadata=metadata,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


__all__ = ["ConflictMapper"]
