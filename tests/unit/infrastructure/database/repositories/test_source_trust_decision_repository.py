from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from ai_news_digest.domain.models.source_trust_decision import SourceTrustDecision
from ai_news_digest.infrastructure.database.repositories.source_trust_decision_repository import (
    SourceTrustDecisionRepository,
)


@pytest.fixture
def mock_session() -> AsyncSession:
    session = MagicMock(spec=AsyncSession)
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def repository(mock_session: AsyncSession) -> SourceTrustDecisionRepository:
    return SourceTrustDecisionRepository(session=mock_session)


@pytest.mark.asyncio
async def test_create_source_trust_decision(repository, mock_session) -> None:
    decision = SourceTrustDecision(
        source_id=uuid4(),
        actor_user_id=uuid4(),
        decision="APPROVE",
        previous_status="pending_review",
        resulting_status="verified",
        previous_is_active=True,
        resulting_is_active=True,
        reason="approved",
        validation_outcome="feed validated: 1 entries",
    )

    model = MagicMock()
    model.id = str(decision.id)
    model.source_id = str(decision.source_id)
    model.actor_user_id = str(decision.actor_user_id)
    model.decision = decision.decision
    model.previous_status = decision.previous_status
    model.resulting_status = decision.resulting_status
    model.previous_is_active = decision.previous_is_active
    model.resulting_is_active = decision.resulting_is_active
    model.reason = decision.reason
    model.validation_outcome = decision.validation_outcome
    model.created_at = decision.created_at

    mock_session.refresh.side_effect = lambda m: None

    # _refresh calls session.refresh(model); return model unchanged
    async def _refresh(model_obj):
        return model_obj

    mock_session.refresh = AsyncMock(return_value=None)

    # The repository creates its own model internally; mock add no-op
    mock_session.add = MagicMock()

    created = await repository.create(decision)

    assert created.decision == "APPROVE"
    mock_session.flush.assert_awaited()


@pytest.mark.asyncio
async def test_list_for_source(repository, mock_session) -> None:
    model = MagicMock()
    model.id = str(uuid4())
    model.source_id = str(uuid4())
    model.actor_user_id = str(uuid4())
    model.decision = "APPROVE"
    model.previous_status = "pending_review"
    model.resulting_status = "verified"
    model.previous_is_active = True
    model.resulting_is_active = True
    model.reason = "approved"
    model.validation_outcome = None

    from datetime import UTC, datetime

    model.created_at = datetime.now(UTC)

    result = MagicMock()
    result.scalars.return_value.all.return_value = [model]
    mock_session.execute.return_value = result

    decisions = await repository.list_for_source(uuid4())

    assert len(decisions) == 1
    assert decisions[0].decision == "APPROVE"


@pytest.mark.asyncio
async def test_count_for_source(repository, mock_session) -> None:
    result = MagicMock()
    result.scalar_one.return_value = 3
    mock_session.execute.return_value = result

    count = await repository.count_for_source(uuid4())

    assert count == 3


@pytest.mark.asyncio
async def test_commit_source_trust_decision(repository, mock_session) -> None:
    await repository.commit()
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_rollback_source_trust_decision(repository, mock_session) -> None:
    await repository.rollback()
    mock_session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_for_source_with_limit(repository, mock_session) -> None:
    model = MagicMock()
    model.id = str(uuid4())
    model.source_id = str(uuid4())
    model.actor_user_id = str(uuid4())
    model.decision = "APPROVE"
    model.previous_status = "pending_review"
    model.resulting_status = "verified"
    model.previous_is_active = True
    model.resulting_is_active = True
    model.reason = "approved"
    model.validation_outcome = None
    from datetime import UTC, datetime

    model.created_at = datetime.now(UTC)

    result = MagicMock()
    result.scalars.return_value.all.return_value = [model]
    mock_session.execute.return_value = result

    decisions = await repository.list_for_source(uuid4(), limit=2, offset=1)

    assert len(decisions) == 1
