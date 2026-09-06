"""
Authenticated notification endpoints.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ai_news_digest.api.v1.dependencies.auth import get_current_active_user
from ai_news_digest.api.v1.dependencies.dependencies import get_container
from ai_news_digest.api.v1.schemas.common import (
    DEFAULT_PAGE_LIMIT,
    MAX_OFFSET,
    MAX_PAGE_LIMIT,
    PaginatedResponse,
)
from ai_news_digest.api.v1.schemas.notifications import (
    NotificationDeliveryHistoryResponse,
    NotificationDeliveryResponse,
    NotificationPreferenceResponse,
    NotificationPreferenceUpdateRequest,
    NotificationResponse,
    NotificationStatsResponse,
    SchedulePreviewResponse,
    TestNotificationRequest,
    UnreadCountResponse,
    UnsubscribeResponse,
)
from ai_news_digest.bootstrap.container import Container
from ai_news_digest.core.exceptions import ResourceNotFoundError
from ai_news_digest.domain.enums.notification import DeliveryChannel
from ai_news_digest.domain.models.notification import Notification, NotificationDelivery
from ai_news_digest.domain.models.user import User

router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"],
)


def _to_response(notification: Notification) -> NotificationResponse:
    return NotificationResponse(
        id=str(notification.id),
        user_id=str(notification.user_id),
        notification_type=notification.notification_type.value,
        title=notification.title,
        body=notification.body,
        severity=notification.severity.value,
        story_id=str(notification.story_id) if notification.story_id else None,
        article_id=str(notification.article_id) if notification.article_id else None,
        company_id=str(notification.company_id) if notification.company_id else None,
        topic_id=str(notification.topic_id) if notification.topic_id else None,
        digest_id=str(notification.digest_id) if notification.digest_id else None,
        metadata=notification.metadata,
        created_at=notification.created_at.isoformat() if notification.created_at else None,
        read_at=notification.read_at.isoformat() if notification.read_at else None,
        dismissed_at=notification.dismissed_at.isoformat() if notification.dismissed_at else None,
        expires_at=notification.expires_at.isoformat() if notification.expires_at else None,
    )


def _delivery_to_response(delivery: Any) -> NotificationDeliveryResponse:
    return NotificationDeliveryResponse(
        id=str(delivery.id),
        notification_id=str(delivery.notification_id),
        channel=delivery.channel.value,
        status=delivery.status.value,
        provider_message_id=delivery.provider_message_id,
        attempt_count=delivery.attempt_count,
        last_attempt_at=delivery.last_attempt_at.isoformat() if delivery.last_attempt_at else None,
        delivered_at=delivery.delivered_at.isoformat() if delivery.delivered_at else None,
        failure_reason=delivery.failure_reason,
        created_at=delivery.created_at.isoformat() if delivery.created_at else None,
        scheduled_for=delivery.scheduled_for.isoformat() if delivery.scheduled_for else None,
        next_attempt_at=delivery.next_attempt_at.isoformat() if delivery.next_attempt_at else None,
        delivery_window=delivery.delivery_window,
        suppression_reason=delivery.suppression_reason,
    )


@router.get(
    "/unread/count",
    response_model=UnreadCountResponse,
    summary="Get unread notification count",
)
async def get_unread_count(
    container: Annotated[Container, Depends(get_container)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> UnreadCountResponse:
    count = await container.notification_service.get_unread_count(current_user.id)
    return UnreadCountResponse(unread_count=count)


@router.get(
    "/preferences",
    response_model=NotificationPreferenceResponse,
    summary="Get notification preferences",
)
async def get_preferences(
    container: Annotated[Container, Depends(get_container)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> NotificationPreferenceResponse:
    pref = await container.notification_service.ensure_default_preferences(current_user.id)
    return NotificationPreferenceResponse(
        user_id=str(pref.user_id),
        in_app_enabled=pref.in_app_enabled,
        email_enabled=pref.email_enabled,
        immediate_enabled=pref.immediate_enabled,
        daily_digest_enabled=pref.daily_digest_enabled,
        weekly_digest_enabled=pref.weekly_digest_enabled,
        min_importance=pref.min_importance,
        min_confidence=pref.min_confidence,
        notify_followed_companies=pref.notify_followed_companies,
        notify_followed_topics=pref.notify_followed_topics,
        notify_corrections=pref.notify_corrections,
        notify_story_evolution=pref.notify_story_evolution,
        quiet_hours_start=pref.quiet_hours_start,
        quiet_hours_end=pref.quiet_hours_end,
        timezone=pref.timezone,
        max_per_day=pref.max_per_day,
    )


@router.put(
    "/preferences",
    response_model=NotificationPreferenceResponse,
    summary="Update notification preferences",
)
async def update_preferences(
    request: NotificationPreferenceUpdateRequest,
    container: Annotated[Container, Depends(get_container)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> NotificationPreferenceResponse:
    updates = request.model_dump(exclude_none=True)
    pref = await container.notification_service.update_preferences(current_user.id, updates)
    return NotificationPreferenceResponse(
        user_id=str(pref.user_id),
        in_app_enabled=pref.in_app_enabled,
        email_enabled=pref.email_enabled,
        immediate_enabled=pref.immediate_enabled,
        daily_digest_enabled=pref.daily_digest_enabled,
        weekly_digest_enabled=pref.weekly_digest_enabled,
        min_importance=pref.min_importance,
        min_confidence=pref.min_confidence,
        notify_followed_companies=pref.notify_followed_companies,
        notify_followed_topics=pref.notify_followed_topics,
        notify_corrections=pref.notify_corrections,
        notify_story_evolution=pref.notify_story_evolution,
        quiet_hours_start=pref.quiet_hours_start,
        quiet_hours_end=pref.quiet_hours_end,
        timezone=pref.timezone,
        max_per_day=pref.max_per_day,
    )


@router.post(
    "/preferences/reset",
    response_model=NotificationPreferenceResponse,
    summary="Reset notification preferences to defaults",
)
async def reset_preferences(
    container: Annotated[Container, Depends(get_container)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> NotificationPreferenceResponse:
    pref = await container.notification_service.reset_preferences(current_user.id)
    return NotificationPreferenceResponse(
        user_id=str(pref.user_id),
        in_app_enabled=pref.in_app_enabled,
        email_enabled=pref.email_enabled,
        immediate_enabled=pref.immediate_enabled,
        daily_digest_enabled=pref.daily_digest_enabled,
        weekly_digest_enabled=pref.weekly_digest_enabled,
        min_importance=pref.min_importance,
        min_confidence=pref.min_confidence,
        notify_followed_companies=pref.notify_followed_companies,
        notify_followed_topics=pref.notify_followed_topics,
        notify_corrections=pref.notify_corrections,
        notify_story_evolution=pref.notify_story_evolution,
        quiet_hours_start=pref.quiet_hours_start,
        quiet_hours_end=pref.quiet_hours_end,
        timezone=pref.timezone,
        max_per_day=pref.max_per_day,
    )


@router.get(
    "/unsubscribe/{token}",
    response_model=UnsubscribeResponse,
    summary="Unsubscribe from email notifications",
)
async def unsubscribe(
    token: str,
    container: Annotated[Container, Depends(get_container)],
) -> UnsubscribeResponse:
    success = await container.notification_service.unsubscribe_email(token)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid unsubscribe token.",
        )
    return UnsubscribeResponse(success=True, message="Unsubscribed from email notifications.")


@router.get(
    "/deliveries/{delivery_id}",
    response_model=NotificationDeliveryResponse,
    summary="Get delivery status",
)
async def get_delivery(
    delivery_id: UUID,
    container: Annotated[Container, Depends(get_container)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> NotificationDeliveryResponse:
    delivery = await container.notification_delivery_repository.get_by_id(delivery_id)
    if delivery is None:
        raise ResourceNotFoundError("Delivery not found.")
    notification = await container.notification_repository.get_by_id(delivery.notification_id)
    if notification is None or notification.user_id != current_user.id:
        raise ResourceNotFoundError("Delivery not found.")
    return _delivery_to_response(delivery)


@router.get(
    "/deliveries",
    response_model=NotificationDeliveryHistoryResponse,
    summary="List delivery history for current user",
)
async def list_deliveries(
    container: Annotated[Container, Depends(get_container)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_LIMIT)] = DEFAULT_PAGE_LIMIT,
    offset: Annotated[int, Query(ge=0, le=MAX_OFFSET)] = 0,
) -> NotificationDeliveryHistoryResponse:
    all_deliveries = await container.notification_delivery_repository.list_pending(
        limit=MAX_PAGE_LIMIT * 10,
    )
    user_notifications, _ = await container.notification_repository.list_for_user(
        user_id=current_user.id,
        limit=MAX_PAGE_LIMIT * 10,
    )
    user_notification_ids = {n.id for n in user_notifications}
    user_deliveries = [
        d for d in all_deliveries
        if d.notification_id in user_notification_ids
    ]
    user_deliveries.sort(
        key=lambda d: d.created_at or datetime.min, reverse=True
    )
    total = len(user_deliveries)
    paged = user_deliveries[offset:offset + limit]
    return NotificationDeliveryHistoryResponse(
        items=[_delivery_to_response(d) for d in paged],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/stats",
    response_model=NotificationStatsResponse,
    summary="Notification stats",
)
async def get_stats(
    container: Annotated[Container, Depends(get_container)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> NotificationStatsResponse:
    notifications, total = await container.notification_repository.list_for_user(
        user_id=current_user.id,
        limit=MAX_PAGE_LIMIT * 10,
    )
    unread = sum(1 for n in notifications if n.read_at is None)
    by_type: dict[str, int] = {}
    by_severity: dict[str, int] = {}
    for n in notifications:
        by_type[n.notification_type.value] = by_type.get(n.notification_type.value, 0) + 1
        by_severity[n.severity.value] = by_severity.get(n.severity.value, 0) + 1

    all_deliveries = (
        await container.notification_delivery_repository.list_pending(
            limit=MAX_PAGE_LIMIT * 10,
        )
    )
    user_deliveries = [
        d for d in all_deliveries
        if d.notification_id in {n.id for n in notifications}
    ]
    _pending_statuses = {"pending", "scheduled", "processing"}
    _failed_statuses = {"failed", "retryable_failure", "permanent_failure"}
    pending = sum(1 for d in user_deliveries if d.status.value in _pending_statuses)
    sent = sum(1 for d in user_deliveries if d.status.value == "sent")
    failed = sum(1 for d in user_deliveries if d.status.value in _failed_statuses)

    return NotificationStatsResponse(
        total=total,
        unread=unread,
        by_type=by_type,
        by_severity=by_severity,
        deliveries_pending=pending,
        deliveries_sent=sent,
        deliveries_failed=failed,
    )


@router.get(
    "/schedule-preview",
    response_model=SchedulePreviewResponse,
    summary="Preview next scheduled notifications",
)
async def schedule_preview(
    container: Annotated[Container, Depends(get_container)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> SchedulePreviewResponse:
    all_deliveries = (
        await container.notification_delivery_repository.list_scheduled(
            limit=MAX_PAGE_LIMIT * 2,
        )
    )
    user_notifications, _ = await container.notification_repository.list_for_user(
        user_id=current_user.id,
        limit=MAX_PAGE_LIMIT * 10,
    )
    user_notification_ids = {n.id for n in user_notifications}
    user_scheduled = [
        d for d in all_deliveries
        if d.notification_id in user_notification_ids
        and d.status.value == "scheduled"
    ]
    user_scheduled.sort(key=lambda d: d.scheduled_for or datetime.min)
    return SchedulePreviewResponse(
        scheduled=[_delivery_to_response(d) for d in user_scheduled],
        count=len(user_scheduled),
    )


@router.post(
    "/test-delivery",
    response_model=NotificationDeliveryResponse,
    summary="Send test notification (dev/admin only)",
)
async def test_delivery(
    request: TestNotificationRequest,
    container: Annotated[Container, Depends(get_container)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> NotificationDeliveryResponse:
    from ai_news_digest.core.config import get_settings
    from ai_news_digest.domain.enums.notification import (
        NotificationSeverity,
        NotificationType,
    )

    settings = get_settings()
    if settings.environment not in ("development", "testing"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Test delivery is only available in development/testing environments.",
        )

    notification = Notification.create(
        user_id=current_user.id,
        notification_type=NotificationType.SYSTEM,
        title=request.title,
        body=request.body,
        severity=NotificationSeverity(request.severity),
    )
    created = await container.notification_repository.create(notification)
    delivery = NotificationDelivery.create(
        notification_id=created.id,
        channel=DeliveryChannel.EMAIL,
    )
    created_delivery = await container.notification_delivery_repository.create(delivery)
    return _delivery_to_response(created_delivery)


@router.get(
    "/",
    response_model=PaginatedResponse[NotificationResponse],
    summary="List current user notifications",
)
async def list_notifications(
    container: Annotated[Container, Depends(get_container)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_LIMIT)] = DEFAULT_PAGE_LIMIT,
    offset: Annotated[int, Query(ge=0, le=MAX_OFFSET)] = 0,
    unread_only: Annotated[bool, Query()] = False,
    notification_type: Annotated[str | None, Query()] = None,
) -> PaginatedResponse[NotificationResponse]:
    notifications, total = await container.notification_service.list_notifications(
        user_id=current_user.id,
        limit=limit,
        offset=offset,
        unread_only=unread_only,
        notification_type=notification_type,
    )
    return PaginatedResponse(
        items=[_to_response(n) for n in notifications],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{notification_id}",
    response_model=NotificationResponse,
    summary="Get a notification",
)
async def get_notification(
    notification_id: UUID,
    container: Annotated[Container, Depends(get_container)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> NotificationResponse:
    notification = await container.notification_service.get_notification(
        notification_id, current_user.id
    )
    if notification is None:
        raise ResourceNotFoundError("Notification not found.")
    return _to_response(notification)


@router.post(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    summary="Mark notification as read",
)
async def mark_read(
    notification_id: UUID,
    container: Annotated[Container, Depends(get_container)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> NotificationResponse:
    notification = await container.notification_service.mark_read(
        notification_id, current_user.id
    )
    if notification is None:
        raise ResourceNotFoundError("Notification not found.")
    return _to_response(notification)


@router.post(
    "/read-all",
    response_model=UnreadCountResponse,
    summary="Mark all notifications as read",
)
async def mark_all_read(
    container: Annotated[Container, Depends(get_container)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> UnreadCountResponse:
    await container.notification_service.mark_all_read(current_user.id)
    return UnreadCountResponse(unread_count=0)


@router.post(
    "/{notification_id}/dismiss",
    response_model=NotificationResponse,
    summary="Dismiss notification",
)
async def dismiss_notification(
    notification_id: UUID,
    container: Annotated[Container, Depends(get_container)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> NotificationResponse:
    notification = await container.notification_service.dismiss(
        notification_id, current_user.id
    )
    if notification is None:
        raise ResourceNotFoundError("Notification not found.")
    return _to_response(notification)


__all__ = ["router"]
