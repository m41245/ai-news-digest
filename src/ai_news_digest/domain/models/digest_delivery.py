from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from ai_news_digest.domain.enums.delivery_status import DeliveryStatus

if TYPE_CHECKING:
    pass


@dataclass(slots=True)
class DigestDelivery:
    """
    Represents a single digest delivery attempt to a recipient.
    """

    id: UUID
    digest_id: UUID
    recipient: str
    status: DeliveryStatus
    attempt_count: int
    sent_at: datetime | None
    failed_at: datetime | None
    failure_reason: str | None
    provider_message_id: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        digest_id: UUID,
        recipient: str,
    ) -> DigestDelivery:
        """
        Factory method for creating a pending delivery record.
        """
        now = datetime.now(UTC)
        return cls(
            id=uuid4(),
            digest_id=digest_id,
            recipient=recipient,
            status=DeliveryStatus.PENDING,
            attempt_count=0,
            sent_at=None,
            failed_at=None,
            failure_reason=None,
            provider_message_id=None,
            created_at=now,
            updated_at=now,
        )


__all__ = ["DigestDelivery"]
