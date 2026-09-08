from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from ai_news_digest.core.logging import get_logger
from ai_news_digest.domain.enums.notification import NotificationType
from ai_news_digest.domain.models.notification_preference import NotificationPreference
from ai_news_digest.domain.models.story_cluster import StoryCluster
from ai_news_digest.domain.models.user import User
from ai_news_digest.domain.models.user_preference import UserPreferenceProfile
from ai_news_digest.domain.ports.notification_repository import (
    NotificationPreferenceRepository,
    NotificationRepository,
)
from ai_news_digest.domain.ports.user_preference_repository import (
    UserPreferenceRepository,
)

logger = get_logger(__name__)


class NotificationEligibilityEngine:
    """
    Deterministic notification eligibility service.

    Evaluates a story against a user's preferences to determine if they
    should receive a notification.
    """

    def __init__(
        self,
        notification_repository: NotificationRepository,
        notification_preference_repo: NotificationPreferenceRepository,
        user_preference_repo: UserPreferenceRepository,
    ) -> None:
        self._notification_repository = notification_repository
        self._notification_preference_repo = notification_preference_repo
        self._user_preference_repo = user_preference_repo

    async def evaluate_story(
        self,
        user: User,
        story: StoryCluster,
        notification_type: NotificationType,
        article_id: UUID | None = None,
        company_id: UUID | None = None,
        topic_id: UUID | None = None,
    ) -> tuple[bool, str | None, dict[str, str | None]]:
        """
        Evaluate whether a user should receive a notification for a story.

        Returns (is_eligible, suppression_reason, metadata).
        """
        metadata: dict[str, str | None] = {}
        pref = await self._notification_preference_repo.get_by_user_id(user.id)
        if pref is None:
            pref = NotificationPreference.create_default(user.id)
        user_pref = await self._user_preference_repo.get_by_user_id(user.id)
        if user_pref is None:
            user_pref = UserPreferenceProfile(user_id=user.id)

        if not pref.in_app_enabled and not pref.email_enabled:
            return False, "notifications_disabled", metadata

        if notification_type == NotificationType.IMPORTANT_STORY:
            if not self._check_importance(story, pref):
                return False, "below_importance_threshold", metadata
            if not self._check_confidence(story, pref):
                return False, "below_confidence_threshold", metadata

        if notification_type in (
            NotificationType.FOLLOWED_COMPANY_UPDATE,
            NotificationType.FOLLOWED_TOPIC_UPDATE,
        ):
            if not pref.notify_followed_companies and not pref.notify_followed_topics:
                return False, "followed_updates_disabled", metadata

            if company_id is not None and company_id in user_pref.muted_company_ids:
                return False, "muted_company", metadata

            if topic_id is not None and topic_id in user_pref.muted_topic_ids:
                return False, "muted_topic", metadata

        if (
            notification_type == NotificationType.CONTRADICTION_DETECTED
            and not pref.notify_corrections
        ):
            return False, "corrections_disabled", metadata

        if (
            notification_type == NotificationType.CORRECTION_PUBLISHED
            and not pref.notify_corrections
        ):
            return False, "corrections_disabled", metadata

        if (
            notification_type == NotificationType.STORY_EVOLUTION
            and not pref.notify_story_evolution
        ):
            return False, "story_evolution_disabled", metadata

        if (
            notification_type == NotificationType.DIGEST_READY
            and not pref.daily_digest_enabled
            and not pref.weekly_digest_enabled
        ):
            return False, "digest_notifications_disabled", metadata

        if not self._check_quiet_hours(pref):
            return False, "quiet_hours", metadata

        if not await self._check_daily_cap(user, pref, metadata):
            return False, "daily_cap_reached", metadata

        metadata["notification_type"] = notification_type.value
        metadata["story_id"] = str(story.id) if story else None
        metadata["article_id"] = str(article_id) if article_id else None
        metadata["company_id"] = str(company_id) if company_id else None
        metadata["topic_id"] = str(topic_id) if topic_id else None

        return True, None, metadata

    def _check_importance(self, story: StoryCluster | None, pref: NotificationPreference) -> bool:
        if story is None or story.importance_score is None:
            return True
        return story.importance_score >= pref.min_importance

    def _check_confidence(self, story: StoryCluster | None, pref: NotificationPreference) -> bool:
        if story is None or story.confidence is None:
            return True
        return story.confidence >= pref.min_confidence

    def _check_quiet_hours(self, pref: NotificationPreference) -> bool:
        if not pref.quiet_hours_start or not pref.quiet_hours_end:
            return True
        try:
            from zoneinfo import ZoneInfo

            tz = ZoneInfo(pref.timezone)
            now = datetime.now(tz)
            current_minutes = now.hour * 60 + now.minute
            start_parts = pref.quiet_hours_start.split(":")
            end_parts = pref.quiet_hours_end.split(":")
            start_minutes = int(start_parts[0]) * 60 + int(start_parts[1])
            end_minutes = int(end_parts[0]) * 60 + int(end_parts[1])
            if start_minutes <= end_minutes:
                in_quiet = start_minutes <= current_minutes < end_minutes
            else:
                in_quiet = current_minutes >= start_minutes or current_minutes < end_minutes
            return not in_quiet
        except Exception:
            return True

    async def _check_daily_cap(
        self,
        user: User,
        pref: NotificationPreference,
        metadata: dict[str, str | None],
    ) -> bool:
        today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        count = await self._notification_repository.count_unread_since(user.id, today)
        if count >= pref.max_per_day:
            return False
        metadata["daily_count"] = str(count + 1)
        metadata["daily_cap"] = str(pref.max_per_day)
        return True

    def build_deduplication_key(
        self,
        user_id: UUID,
        notification_type: NotificationType,
        story_id: UUID | None = None,
        article_id: UUID | None = None,
        company_id: UUID | None = None,
        topic_id: UUID | None = None,
        digest_id: UUID | None = None,
    ) -> str:
        parts = [
            str(user_id),
            notification_type.value,
            str(story_id or ""),
            str(article_id or ""),
            str(company_id or ""),
            str(topic_id or ""),
            str(digest_id or ""),
        ]
        return ":".join(parts)


__all__ = ["NotificationEligibilityEngine"]
