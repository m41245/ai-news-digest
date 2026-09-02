from __future__ import annotations

import contextlib
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from ai_news_digest.core.exceptions import ResourceNotFoundError
from ai_news_digest.core.logging import get_logger
from ai_news_digest.domain.enums.delivery_status import DeliveryStatus
from ai_news_digest.domain.models.digest_delivery import DigestDelivery
from ai_news_digest.domain.ports.delivery_repository import DeliveryRepository
from ai_news_digest.domain.ports.digest_repository import DigestRepository
from ai_news_digest.infrastructure.email.composer import EmailComposer
from ai_news_digest.infrastructure.email.errors import (
    EmailAuthenticationError,
    EmailConfigurationError,
    EmailConnectionError,
    EmailError,
    EmailInvalidRecipientError,
    EmailPermanentFailureError,
    EmailRateLimitError,
    EmailTimeoutError,
)

if TYPE_CHECKING:
    from ai_news_digest.domain.ports.email_sender import EmailSender

logger = get_logger(__name__)


@dataclass(slots=True, frozen=True)
class DeliveryResult:
    """Result of delivering to a single recipient."""

    recipient: str
    status: DeliveryStatus
    failure_reason: str | None = None


@dataclass(slots=True, frozen=True)
class DeliverySummary:
    """Summary of a bulk digest delivery operation."""

    digest_id: UUID
    total_recipients: int
    sent_count: int
    failed_count: int
    skipped_count: int
    results: list[DeliveryResult]
    has_system_error: bool = False
    system_error: str | None = None


class DeliverDigestUseCase:
    """
    Application use case responsible for delivering a digest to all
    eligible recipients with idempotent, per-recipient tracking.
    """

    def __init__(
        self,
        *,
        digest_repository: DigestRepository,
        delivery_repository: DeliveryRepository,
        email_sender: EmailSender,
        email_composer: EmailComposer,
        recipients: list[str],
    ) -> None:
        self._digest_repository = digest_repository
        self._delivery_repository = delivery_repository
        self._email_sender = email_sender
        self._email_composer = email_composer
        self._recipients = list(dict.fromkeys(recipients))

    async def execute(self, digest_id: UUID) -> DeliverySummary:
        """
        Deliver a digest to all configured recipients.

        The operation is idempotent: already-SENT deliveries are skipped.
        Permanent recipient failures are isolated; transient failures
        propagate so the caller can retry.
        """
        digest = await self._digest_repository.get_by_id(digest_id)
        if digest is None:
            raise ResourceNotFoundError(f"Digest with id '{digest_id}' was not found.")

        if not self._recipients:
            return DeliverySummary(
                digest_id=digest_id,
                total_recipients=0,
                sent_count=0,
                failed_count=0,
                skipped_count=0,
                results=[],
            )

        email_message = self._email_composer.compose(digest)

        deliveries = await self._ensure_deliveries(digest_id)

        results: list[DeliveryResult] = []
        sent_count = 0
        failed_count = 0
        skipped_count = 0

        try:
            for delivery in deliveries:
                if delivery.status == DeliveryStatus.SENT:
                    skipped_count += 1
                    results.append(
                        DeliveryResult(
                            recipient=delivery.recipient,
                            status=DeliveryStatus.SENT,
                        )
                    )
                    continue

                try:
                    await self._email_sender.send(
                        recipient=delivery.recipient,
                        subject=email_message.subject,
                        html=email_message.html_body,
                        text=email_message.text_body,
                    )
                    delivery.status = DeliveryStatus.SENT
                    delivery.sent_at = datetime.now(UTC)
                    delivery.attempt_count += 1
                    await self._delivery_repository.update(delivery)
                    sent_count += 1
                    results.append(
                        DeliveryResult(
                            recipient=delivery.recipient,
                            status=DeliveryStatus.SENT,
                        )
                    )
                except EmailInvalidRecipientError as exc:
                    delivery.status = DeliveryStatus.FAILED
                    delivery.failed_at = datetime.now(UTC)
                    delivery.failure_reason = str(exc)
                    delivery.attempt_count += 1
                    await self._delivery_repository.update(delivery)
                    failed_count += 1
                    results.append(
                        DeliveryResult(
                            recipient=delivery.recipient,
                            status=DeliveryStatus.FAILED,
                            failure_reason=str(exc),
                        )
                    )
                except EmailPermanentFailureError as exc:
                    delivery.status = DeliveryStatus.FAILED
                    delivery.failed_at = datetime.now(UTC)
                    delivery.failure_reason = str(exc)
                    delivery.attempt_count += 1
                    await self._delivery_repository.update(delivery)
                    failed_count += 1
                    results.append(
                        DeliveryResult(
                            recipient=delivery.recipient,
                            status=DeliveryStatus.FAILED,
                            failure_reason=str(exc),
                        )
                    )
                except (EmailAuthenticationError, EmailConfigurationError) as exc:
                    for d in deliveries:
                        if d.status == DeliveryStatus.PENDING:
                            try:
                                d.status = DeliveryStatus.FAILED
                                d.failed_at = datetime.now(UTC)
                                d.failure_reason = f"System error: {exc}"
                                d.attempt_count += 1
                                await self._delivery_repository.update(d)
                                failed_count += 1
                                results.append(
                                    DeliveryResult(
                                        recipient=d.recipient,
                                        status=DeliveryStatus.FAILED,
                                        failure_reason=d.failure_reason,
                                    )
                                )
                            except Exception:
                                failed_count += 1
                                results.append(
                                    DeliveryResult(
                                        recipient=d.recipient,
                                        status=DeliveryStatus.FAILED,
                                        failure_reason=f"System error: {exc} (update failed)",
                                    )
                                )
                    return DeliverySummary(
                        digest_id=digest_id,
                        total_recipients=len(self._recipients),
                        sent_count=sent_count,
                        failed_count=failed_count,
                        skipped_count=skipped_count,
                        results=results,
                        has_system_error=True,
                        system_error=str(exc),
                    )
                except (
                    EmailConnectionError,
                    EmailTimeoutError,
                    EmailRateLimitError,
                ) as exc:
                    try:
                        delivery.attempt_count += 1
                        await self._delivery_repository.increment_attempt(delivery.id)
                    except Exception:
                        logger.debug(
                            "delivery_increment_attempt_failed",
                            recipient=delivery.recipient,
                            exc_info=True,
                        )
                    raise EmailError(
                        f"Transient delivery failure for '{delivery.recipient}': {exc}"
                    ) from exc
        except Exception:
            for d in deliveries:
                if d.status == DeliveryStatus.PENDING:
                    try:
                        d.status = DeliveryStatus.FAILED
                        d.failed_at = datetime.now(UTC)
                        d.failure_reason = "System error: operation failed unexpectedly"
                        d.attempt_count += 1
                        await self._delivery_repository.update(d)
                        failed_count += 1
                        results.append(
                            DeliveryResult(
                                recipient=d.recipient,
                                status=DeliveryStatus.FAILED,
                                failure_reason=d.failure_reason,
                            )
                        )
                    except Exception:
                        failed_count += 1
                        results.append(
                            DeliveryResult(
                                recipient=d.recipient,
                                status=DeliveryStatus.FAILED,
                                failure_reason="System error: update failed",
                            )
                        )
            raise

        return DeliverySummary(
            digest_id=digest_id,
            total_recipients=len(self._recipients),
            sent_count=sent_count,
            failed_count=failed_count,
            skipped_count=skipped_count,
            results=results,
        )

    async def _ensure_deliveries(
        self,
        digest_id: UUID,
    ) -> list[DigestDelivery]:
        """
        Return existing delivery records for the digest, creating any that
        are missing. The order matches the configured recipient list.

        If creation fails after some deliveries were persisted, the
        newly-created deliveries are removed so the operation can be
        retried cleanly.
        """
        deliveries: list[DigestDelivery] = []
        created_ids: list[UUID] = []
        try:
            for recipient in self._recipients:
                existing = await self._delivery_repository.get_by_digest_and_recipient(
                    digest_id, recipient
                )
                if existing is not None:
                    deliveries.append(existing)
                else:
                    delivery = DigestDelivery.create(
                        digest_id=digest_id,
                        recipient=recipient,
                    )
                    delivery = await self._delivery_repository.create(delivery)
                    deliveries.append(delivery)
                    created_ids.append(delivery.id)
        except Exception:
            for delivery_id in created_ids:
                with contextlib.suppress(Exception):
                    await self._delivery_repository.delete(delivery_id)
            raise
        return deliveries


__all__ = ["DeliverDigestUseCase", "DeliveryResult", "DeliverySummary"]
