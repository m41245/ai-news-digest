from __future__ import annotations

from uuid import UUID

from ai_news_digest.domain.models.story_activity import StoryActivity
from ai_news_digest.infrastructure.database.models.story_activity_model import (
    StoryActivityModel,
)


class StoryActivityMapper:
    """Convert between StoryActivity domain model and StoryActivityModel ORM model."""

    @staticmethod
    def to_model(activity: StoryActivity) -> StoryActivityModel:
        return StoryActivityModel(
            id=str(activity.id),
            story_cluster_id=str(activity.story_cluster_id),
            status=activity.status.value,
            activity_score=activity.activity_score,
            confidence=activity.confidence,
            explanation=activity.explanation,
            evaluated_at=activity.evaluated_at,
            detection_version=activity.detection_version,
            article_count_recent=activity.article_count_recent,
            unique_source_count_recent=activity.unique_source_count_recent,
            recent_article_velocity=activity.recent_article_velocity,
            latest_article_at=activity.latest_article_at,
            first_article_at=activity.first_article_at,
            recent_claim_count=activity.recent_claim_count,
            recent_conflict_count=activity.recent_conflict_count,
            state_change_count=activity.state_change_count,
            created_at=activity.created_at,
            updated_at=activity.updated_at,
        )

    @staticmethod
    def to_domain(model: StoryActivityModel) -> StoryActivity:
        from ai_news_digest.domain.enums.story_activity_status import StoryActivityStatus

        return StoryActivity(
            id=UUID(model.id),
            story_cluster_id=UUID(model.story_cluster_id),
            status=StoryActivityStatus(model.status),
            activity_score=model.activity_score,
            confidence=model.confidence,
            explanation=model.explanation,
            evaluated_at=model.evaluated_at,
            detection_version=model.detection_version,
            article_count_recent=model.article_count_recent,
            unique_source_count_recent=model.unique_source_count_recent,
            recent_article_velocity=model.recent_article_velocity,
            latest_article_at=model.latest_article_at,
            first_article_at=model.first_article_at,
            recent_claim_count=model.recent_claim_count,
            recent_conflict_count=model.recent_conflict_count,
            state_change_count=model.state_change_count,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def update_model(model: StoryActivityModel, activity: StoryActivity) -> None:
        model.status = activity.status.value
        model.activity_score = activity.activity_score
        model.confidence = activity.confidence
        model.explanation = activity.explanation
        model.evaluated_at = activity.evaluated_at
        model.detection_version = activity.detection_version
        model.article_count_recent = activity.article_count_recent
        model.unique_source_count_recent = activity.unique_source_count_recent
        model.recent_article_velocity = activity.recent_article_velocity
        model.latest_article_at = activity.latest_article_at
        model.first_article_at = activity.first_article_at
        model.recent_claim_count = activity.recent_claim_count
        model.recent_conflict_count = activity.recent_conflict_count
        model.state_change_count = activity.state_change_count


__all__ = ["StoryActivityMapper"]
