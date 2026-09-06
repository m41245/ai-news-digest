from __future__ import annotations

from uuid import UUID

from ai_news_digest.domain.models.notification import Notification, NotificationDelivery
from ai_news_digest.domain.models.notification_preference import NotificationPreference
from ai_news_digest.infrastructure.database.models.notification_model import (
    NotificationDeliveryModel,
    NotificationModel,
    NotificationPreferenceModel,
)


class NotificationMapper:
    """Maps between Notification domain objects and ORM entities."""

    @staticmethod
    def to_model(notification: Notification) -> NotificationModel:
        return NotificationModel(
            id=str(notification.id),
            user_id=str(notification.user_id),
            notification_type=notification.notification_type.value,
            title=notification.title,
            body=notification.body,
            severity=notification.severity.value,
            story_id=str(notification.story_id) if notification.story_id is not None else None,
            article_id=(
                str(notification.article_id) if notification.article_id is not None else None
            ),
            company_id=(
                str(notification.company_id) if notification.company_id is not None else None
            ),
            topic_id=str(notification.topic_id) if notification.topic_id is not None else None,
            digest_id=str(notification.digest_id) if notification.digest_id is not None else None,
            extra_data=notification.metadata,
            deduplication_key=notification.deduplication_key,
            created_at=notification.created_at,
            read_at=notification.read_at,
            dismissed_at=notification.dismissed_at,
            expires_at=notification.expires_at,
            scheduled_for=notification.scheduled_for,
        )

    @staticmethod
    def update_model(model: NotificationModel, notification: Notification) -> None:
        model.title = notification.title
        model.body = notification.body
        model.severity = notification.severity.value
        model.read_at = notification.read_at
        model.dismissed_at = notification.dismissed_at
        model.expires_at = notification.expires_at
        model.scheduled_for = notification.scheduled_for

    @staticmethod
    def to_domain(model: NotificationModel) -> Notification:
        from ai_news_digest.domain.enums.notification import (
            NotificationSeverity,
            NotificationType,
        )

        try:
            notification_type = NotificationType(model.notification_type)
        except ValueError:
            notification_type = NotificationType.SYSTEM

        try:
            severity = NotificationSeverity(model.severity)
        except ValueError:
            severity = NotificationSeverity.INFO

        return Notification(
            id=UUID(model.id),
            user_id=UUID(model.user_id),
            notification_type=notification_type,
            title=model.title,
            body=model.body,
            severity=severity,
            story_id=UUID(model.story_id) if model.story_id is not None else None,
            article_id=UUID(model.article_id) if model.article_id is not None else None,
            company_id=UUID(model.company_id) if model.company_id is not None else None,
            topic_id=UUID(model.topic_id) if model.topic_id is not None else None,
            digest_id=UUID(model.digest_id) if model.digest_id is not None else None,
            metadata=model.extra_data,
            deduplication_key=model.deduplication_key,
            created_at=model.created_at,
            read_at=model.read_at,
            dismissed_at=model.dismissed_at,
            expires_at=model.expires_at,
            scheduled_for=model.scheduled_for,
        )


class NotificationPreferenceMapper:
    """Maps between NotificationPreference domain objects and ORM entities."""

    @staticmethod
    def to_model(preference: NotificationPreference) -> NotificationPreferenceModel:
        return NotificationPreferenceModel(
            user_id=str(preference.user_id),
            in_app_enabled=preference.in_app_enabled,
            email_enabled=preference.email_enabled,
            immediate_enabled=preference.immediate_enabled,
            daily_digest_enabled=preference.daily_digest_enabled,
            weekly_digest_enabled=preference.weekly_digest_enabled,
            min_importance=preference.min_importance,
            min_confidence=preference.min_confidence,
            notify_followed_companies=preference.notify_followed_companies,
            notify_followed_topics=preference.notify_followed_topics,
            notify_corrections=preference.notify_corrections,
            notify_story_evolution=preference.notify_story_evolution,
            quiet_hours_start=preference.quiet_hours_start,
            quiet_hours_end=preference.quiet_hours_end,
            timezone=preference.timezone,
            max_per_day=preference.max_per_day,
            unsubscribe_token=preference.unsubscribe_token,
            created_at=preference.created_at,
            updated_at=preference.updated_at,
        )

    @staticmethod
    def update_model(
        model: NotificationPreferenceModel,
        preference: NotificationPreference,
    ) -> None:
        model.in_app_enabled = preference.in_app_enabled
        model.email_enabled = preference.email_enabled
        model.immediate_enabled = preference.immediate_enabled
        model.daily_digest_enabled = preference.daily_digest_enabled
        model.weekly_digest_enabled = preference.weekly_digest_enabled
        model.min_importance = preference.min_importance
        model.min_confidence = preference.min_confidence
        model.notify_followed_companies = preference.notify_followed_companies
        model.notify_followed_topics = preference.notify_followed_topics
        model.notify_corrections = preference.notify_corrections
        model.notify_story_evolution = preference.notify_story_evolution
        model.quiet_hours_start = preference.quiet_hours_start
        model.quiet_hours_end = preference.quiet_hours_end
        model.timezone = preference.timezone
        model.max_per_day = preference.max_per_day
        model.unsubscribe_token = preference.unsubscribe_token
        model.updated_at = preference.updated_at

    @staticmethod
    def to_domain(model: NotificationPreferenceModel) -> NotificationPreference:
        return NotificationPreference(
            user_id=UUID(model.user_id),
            in_app_enabled=model.in_app_enabled,
            email_enabled=model.email_enabled,
            immediate_enabled=model.immediate_enabled,
            daily_digest_enabled=model.daily_digest_enabled,
            weekly_digest_enabled=model.weekly_digest_enabled,
            min_importance=model.min_importance,
            min_confidence=model.min_confidence,
            notify_followed_companies=model.notify_followed_companies,
            notify_followed_topics=model.notify_followed_topics,
            notify_corrections=model.notify_corrections,
            notify_story_evolution=model.notify_story_evolution,
            quiet_hours_start=model.quiet_hours_start,
            quiet_hours_end=model.quiet_hours_end,
            timezone=model.timezone,
            max_per_day=model.max_per_day,
            unsubscribe_token=model.unsubscribe_token,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class NotificationDeliveryMapper:
    """Maps between NotificationDelivery domain objects and ORM entities."""

    @staticmethod
    def to_model(delivery: NotificationDelivery) -> NotificationDeliveryModel:
        return NotificationDeliveryModel(
            id=str(delivery.id),
            notification_id=str(delivery.notification_id),
            channel=delivery.channel.value,
            status=delivery.status.value,
            provider_message_id=delivery.provider_message_id,
            attempt_count=delivery.attempt_count,
            last_attempt_at=delivery.last_attempt_at,
            delivered_at=delivery.delivered_at,
            failure_reason=delivery.failure_reason,
            created_at=delivery.created_at,
            updated_at=delivery.updated_at,
            scheduled_for=delivery.scheduled_for,
            claimed_at=delivery.claimed_at,
            processing_started_at=delivery.processing_started_at,
            next_attempt_at=delivery.next_attempt_at,
            provider_idempotency_key=delivery.provider_idempotency_key,
            delivery_window=delivery.delivery_window,
            suppression_reason=delivery.suppression_reason,
        )

    @staticmethod
    def update_model(model: NotificationDeliveryModel, delivery: NotificationDelivery) -> None:
        model.status = delivery.status.value
        model.provider_message_id = delivery.provider_message_id
        model.attempt_count = delivery.attempt_count
        model.last_attempt_at = delivery.last_attempt_at
        model.delivered_at = delivery.delivered_at
        model.failure_reason = delivery.failure_reason
        model.updated_at = delivery.updated_at
        model.scheduled_for = delivery.scheduled_for
        model.claimed_at = delivery.claimed_at
        model.processing_started_at = delivery.processing_started_at
        model.next_attempt_at = delivery.next_attempt_at
        model.provider_idempotency_key = delivery.provider_idempotency_key
        model.delivery_window = delivery.delivery_window
        model.suppression_reason = delivery.suppression_reason

    @staticmethod
    def to_domain(model: NotificationDeliveryModel) -> NotificationDelivery:
        from ai_news_digest.domain.enums.notification import (
            DeliveryChannel,
            DeliveryStatus,
        )

        try:
            channel = DeliveryChannel(model.channel)
        except ValueError:
            channel = DeliveryChannel.IN_APP

        try:
            status = DeliveryStatus(model.status)
        except ValueError:
            status = DeliveryStatus.PENDING

        return NotificationDelivery(
            id=UUID(model.id),
            notification_id=UUID(model.notification_id),
            channel=channel,
            status=status,
            provider_message_id=model.provider_message_id,
            attempt_count=model.attempt_count,
            last_attempt_at=model.last_attempt_at,
            delivered_at=model.delivered_at,
            failure_reason=model.failure_reason,
            created_at=model.created_at,
            updated_at=model.updated_at,
            scheduled_for=model.scheduled_for,
            claimed_at=model.claimed_at,
            processing_started_at=model.processing_started_at,
            next_attempt_at=model.next_attempt_at,
            provider_idempotency_key=model.provider_idempotency_key,
            delivery_window=model.delivery_window,
            suppression_reason=model.suppression_reason,
        )


__all__ = [
    "NotificationDeliveryMapper",
    "NotificationMapper",
    "NotificationPreferenceMapper",
]
