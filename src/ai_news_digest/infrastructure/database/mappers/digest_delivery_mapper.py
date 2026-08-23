from __future__ import annotations

from uuid import UUID

from ai_news_digest.domain.enums.delivery_status import DeliveryStatus
from ai_news_digest.domain.models.digest_delivery import DigestDelivery
from ai_news_digest.infrastructure.database.models.digest_delivery_model import (
    DigestDeliveryModel,
)


class DigestDeliveryMapper:
    """
    Maps between DigestDelivery domain objects and DigestDeliveryModel ORM entities.
    """

    @staticmethod
    def to_model(
        delivery: DigestDelivery,
    ) -> DigestDeliveryModel:
        """
        Convert a domain DigestDelivery into an ORM DigestDeliveryModel.
        """
        return DigestDeliveryModel(
            id=str(delivery.id),
            digest_id=str(delivery.digest_id),
            recipient=delivery.recipient,
            status=delivery.status.value,
            attempt_count=delivery.attempt_count,
            sent_at=delivery.sent_at,
            failed_at=delivery.failed_at,
            failure_reason=delivery.failure_reason,
            provider_message_id=delivery.provider_message_id,
            created_at=delivery.created_at,
            updated_at=delivery.updated_at,
        )

    @staticmethod
    def to_domain(
        model: DigestDeliveryModel,
    ) -> DigestDelivery:
        """
        Convert an ORM DigestDeliveryModel into a domain DigestDelivery.
        """
        return DigestDelivery(
            id=UUID(model.id),
            digest_id=UUID(model.digest_id),
            recipient=model.recipient,
            status=DeliveryStatus(model.status),
            attempt_count=model.attempt_count,
            sent_at=model.sent_at,
            failed_at=model.failed_at,
            failure_reason=model.failure_reason,
            provider_message_id=model.provider_message_id,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def update_model(
        model: DigestDeliveryModel,
        delivery: DigestDelivery,
    ) -> None:
        """
        Update an existing ORM model from a domain DigestDelivery.
        """
        model.digest_id = str(delivery.digest_id)
        model.recipient = delivery.recipient
        model.status = delivery.status.value
        model.attempt_count = delivery.attempt_count
        model.sent_at = delivery.sent_at
        model.failed_at = delivery.failed_at
        model.failure_reason = delivery.failure_reason
        model.provider_message_id = delivery.provider_message_id
        model.updated_at = delivery.updated_at


__all__ = ["DigestDeliveryMapper"]
