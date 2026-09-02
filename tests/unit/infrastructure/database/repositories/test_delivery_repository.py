"""Unit tests for SqlAlchemyDeliveryRepository."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from ai_news_digest.core.exceptions import ResourceNotFoundError
from ai_news_digest.domain.enums.delivery_status import DeliveryStatus
from ai_news_digest.domain.models.digest_delivery import DigestDelivery
from ai_news_digest.infrastructure.database.repositories.delivery_repository import (
    DeliveryRepository,
)


@pytest.fixture
def mock_session() -> AsyncMock:
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def repository(mock_session: AsyncMock) -> DeliveryRepository:
    return DeliveryRepository(mock_session)


def _make_delivery(
    digest_id: UUID | None = None,
    recipient: str = "user@example.com",
) -> DigestDelivery:
    return DigestDelivery.create(
        digest_id=digest_id or uuid4(),
        recipient=recipient,
    )


@pytest.mark.asyncio
async def test_delivery_repository_create(
    repository: DeliveryRepository, mock_session: AsyncMock
) -> None:
    delivery = _make_delivery()
    mock_model = MagicMock()
    mock_model.id = str(delivery.id)
    mock_model.digest_id = str(delivery.digest_id)
    mock_model.recipient = delivery.recipient
    mock_model.status = delivery.status.value
    mock_model.attempt_count = delivery.attempt_count
    mock_model.sent_at = delivery.sent_at
    mock_model.failed_at = delivery.failed_at
    mock_model.failure_reason = delivery.failure_reason
    mock_model.provider_message_id = delivery.provider_message_id
    mock_model.created_at = delivery.created_at
    mock_model.updated_at = delivery.updated_at
    mock_session.refresh.return_value = mock_model

    with (
        patch.object(repository, "_add", new_callable=AsyncMock),
        patch.object(repository, "_commit", new_callable=AsyncMock),
        patch(
            "ai_news_digest.infrastructure.database.repositories.delivery_repository.DigestDeliveryMapper.to_model"
        ) as mock_to_model,
        patch(
            "ai_news_digest.infrastructure.database.repositories.delivery_repository.DigestDeliveryMapper.to_domain"
        ) as mock_to_domain,
    ):
        mock_to_model.return_value = mock_model
        mock_to_domain.return_value = delivery
        result = await repository.create(delivery)
        assert result == delivery


@pytest.mark.asyncio
async def test_delivery_repository_get_by_id_found(
    repository: DeliveryRepository, mock_session: AsyncMock
) -> None:
    delivery = _make_delivery()
    mock_result = MagicMock()
    mock_model = MagicMock()
    mock_model.id = str(delivery.id)
    mock_model.digest_id = str(delivery.digest_id)
    mock_model.recipient = delivery.recipient
    mock_model.status = delivery.status.value
    mock_model.attempt_count = delivery.attempt_count
    mock_model.sent_at = delivery.sent_at
    mock_model.failed_at = delivery.failed_at
    mock_model.failure_reason = delivery.failure_reason
    mock_model.provider_message_id = delivery.provider_message_id
    mock_model.created_at = delivery.created_at
    mock_model.updated_at = delivery.updated_at
    mock_result.scalar_one_or_none.return_value = mock_model
    mock_session.execute.return_value = mock_result

    with patch(
        "ai_news_digest.infrastructure.database.repositories.delivery_repository.DigestDeliveryMapper.to_domain"
    ) as mock_to_domain:
        mock_to_domain.return_value = delivery
        result = await repository.get_by_id(delivery.id)
        assert result is not None
        assert result.id == delivery.id


@pytest.mark.asyncio
async def test_delivery_repository_get_by_id_not_found(
    repository: DeliveryRepository, mock_session: AsyncMock
) -> None:
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    result = await repository.get_by_id(uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_delivery_repository_get_by_digest_and_recipient(
    repository: DeliveryRepository, mock_session: AsyncMock
) -> None:
    delivery = _make_delivery(recipient="alice@example.com")
    mock_result = MagicMock()
    mock_model = MagicMock()
    mock_model.id = str(delivery.id)
    mock_model.digest_id = str(delivery.digest_id)
    mock_model.recipient = "alice@example.com"
    mock_model.status = delivery.status.value
    mock_model.attempt_count = delivery.attempt_count
    mock_model.sent_at = delivery.sent_at
    mock_model.failed_at = delivery.failed_at
    mock_model.failure_reason = delivery.failure_reason
    mock_model.provider_message_id = delivery.provider_message_id
    mock_model.created_at = delivery.created_at
    mock_model.updated_at = delivery.updated_at
    mock_result.scalar_one_or_none.return_value = mock_model
    mock_session.execute.return_value = mock_result

    with patch(
        "ai_news_digest.infrastructure.database.repositories.delivery_repository.DigestDeliveryMapper.to_domain"
    ) as mock_to_domain:
        mock_to_domain.return_value = delivery
        result = await repository.get_by_digest_and_recipient(
            delivery.digest_id, "alice@example.com"
        )
        assert result is not None
        assert result.recipient == "alice@example.com"


@pytest.mark.asyncio
async def test_delivery_repository_list_by_digest(
    repository: DeliveryRepository, mock_session: AsyncMock
) -> None:
    digest_id = uuid4()
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_model = MagicMock()
    mock_model.id = str(uuid4())
    mock_model.digest_id = str(digest_id)
    mock_model.recipient = "a@b.com"
    mock_model.status = DeliveryStatus.PENDING.value
    mock_model.attempt_count = 0
    mock_model.sent_at = None
    mock_model.failed_at = None
    mock_model.failure_reason = None
    mock_model.provider_message_id = None
    mock_model.created_at = datetime.now(UTC)
    mock_model.updated_at = datetime.now(UTC)
    mock_scalars.all.return_value = [mock_model]
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute.return_value = mock_result

    with patch(
        "ai_news_digest.infrastructure.database.repositories.delivery_repository.DigestDeliveryMapper.to_domain"
    ) as mock_to_domain:
        mock_to_domain.side_effect = lambda m: m
        results = await repository.list_by_digest(digest_id)
        assert len(results) == 1


@pytest.mark.asyncio
async def test_delivery_repository_increment_attempt(
    repository: DeliveryRepository, mock_session: AsyncMock
) -> None:
    delivery_id = uuid4()
    mock_model = MagicMock()
    mock_model.id = str(delivery_id)
    mock_model.digest_id = str(uuid4())
    mock_model.recipient = "a@b.com"
    mock_model.status = "pending"
    mock_model.attempt_count = 5
    mock_model.sent_at = None
    mock_model.failed_at = None
    mock_model.failure_reason = None
    mock_model.provider_message_id = None
    mock_model.created_at = datetime.now(UTC)
    mock_model.updated_at = datetime.now(UTC)

    mock_execute_result = MagicMock()
    mock_execute_result.scalar_one_or_none.return_value = mock_model
    mock_session.execute.return_value = mock_execute_result

    with (
        patch.object(repository, "_commit", new_callable=AsyncMock),
    ):
        result = await repository.increment_attempt(delivery_id)
        assert result is not None
        assert result.attempt_count == 5


@pytest.mark.asyncio
async def test_delivery_repository_update_not_found(
    repository: DeliveryRepository, mock_session: AsyncMock
) -> None:
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    delivery = _make_delivery()
    with pytest.raises(ResourceNotFoundError, match="was not found"):
        await repository.update(delivery)


@pytest.mark.asyncio
async def test_delivery_repository_delete(
    repository: DeliveryRepository, mock_session: AsyncMock
) -> None:
    delivery_id = uuid4()
    mock_model = MagicMock()
    mock_model.id = str(delivery_id)
    mock_model.digest_id = str(uuid4())
    mock_model.recipient = "a@b.com"
    mock_model.status = "pending"
    mock_model.attempt_count = 0
    mock_model.sent_at = None
    mock_model.failed_at = None
    mock_model.failure_reason = None
    mock_model.provider_message_id = None
    mock_model.created_at = datetime.now(UTC)
    mock_model.updated_at = datetime.now(UTC)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_model
    mock_session.execute.return_value = mock_result

    with patch.object(repository, "_commit", new_callable=AsyncMock):
        await repository.delete(delivery_id)
        mock_session.delete.assert_called_once_with(mock_model)


@pytest.mark.asyncio
async def test_delivery_repository_delete_not_found(
    repository: DeliveryRepository, mock_session: AsyncMock
) -> None:
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    with pytest.raises(ResourceNotFoundError, match="was not found"):
        await repository.delete(uuid4())


__all__ = [
    "test_delivery_repository_create",
    "test_delivery_repository_delete",
    "test_delivery_repository_delete_not_found",
    "test_delivery_repository_get_by_digest_and_recipient",
    "test_delivery_repository_get_by_id_found",
    "test_delivery_repository_get_by_id_not_found",
    "test_delivery_repository_increment_attempt",
    "test_delivery_repository_list_by_digest",
    "test_delivery_repository_update_not_found",
]
