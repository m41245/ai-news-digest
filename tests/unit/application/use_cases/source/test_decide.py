from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from ai_news_digest.application.dto.source.decision_request import SourceDecisionRequest
from ai_news_digest.application.exceptions.source import SourceNotFoundError
from ai_news_digest.application.use_cases.source.decide import (
    ApproveSourceUseCase,
    DeactivateSourceUseCase,
    RejectSourceUseCase,
)
from ai_news_digest.core.exceptions import ValidationError
from ai_news_digest.domain.enums.source_status import SourceStatus
from ai_news_digest.domain.models.source import Source


def _source(status: SourceStatus = SourceStatus.PENDING_REVIEW, is_active: bool = True) -> Source:
    return Source.create(
        name="Test Source",
        feed_url="https://example.com/feed.xml",
        status=status,
        is_active=is_active,
    )


@pytest.mark.asyncio
async def test_approve_source_use_case_validates_feed_and_updates() -> None:
    source = _source()
    repository = AsyncMock()
    repository.get_by_id.return_value = source
    repository.update.return_value = source
    audit_repository = AsyncMock()
    fetcher = AsyncMock()
    fetcher.fetch.return_value = [MagicMock()]

    use_case = ApproveSourceUseCase(
        source_repository=repository,
        audit_repository=audit_repository,
        rss_fetcher=fetcher,
    )
    request = SourceDecisionRequest(id=source.id, reason="approved")

    response = await use_case.execute(request, actor_user_id=uuid4())

    assert response.status == SourceStatus.VERIFIED.value
    fetcher.fetch.assert_awaited_once()
    repository.update.assert_awaited_once()
    audit_repository.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_approve_source_use_case_fails_closed_on_bad_feed() -> None:
    source = _source()
    repository = AsyncMock()
    repository.get_by_id.return_value = source
    audit_repository = AsyncMock()
    fetcher = AsyncMock()
    fetcher.fetch.side_effect = Exception("boom")

    use_case = ApproveSourceUseCase(
        source_repository=repository,
        audit_repository=audit_repository,
        rss_fetcher=fetcher,
    )
    request = SourceDecisionRequest(id=source.id, reason="approved")

    with pytest.raises(ValidationError):
        await use_case.execute(request, actor_user_id=uuid4())

    repository.update.assert_not_awaited()
    audit_repository.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_approve_source_use_case_fails_closed_on_missing_fetcher() -> None:
    source = _source()
    repository = AsyncMock()
    repository.get_by_id.return_value = source
    audit_repository = AsyncMock()

    use_case = ApproveSourceUseCase(
        source_repository=repository,
        audit_repository=audit_repository,
        rss_fetcher=None,
    )
    request = SourceDecisionRequest(id=source.id, reason="approved")

    with pytest.raises(ValidationError):
        await use_case.execute(request, actor_user_id=uuid4())

    repository.update.assert_not_awaited()
    audit_repository.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_approve_source_use_case_fails_closed_on_empty_feed() -> None:
    source = _source()
    repository = AsyncMock()
    repository.get_by_id.return_value = source
    audit_repository = AsyncMock()
    fetcher = AsyncMock()
    fetcher.fetch.return_value = []

    use_case = ApproveSourceUseCase(
        source_repository=repository,
        audit_repository=audit_repository,
        rss_fetcher=fetcher,
    )
    request = SourceDecisionRequest(id=source.id, reason="approved")

    with pytest.raises(ValidationError):
        await use_case.execute(request, actor_user_id=uuid4())

    repository.update.assert_not_awaited()
    audit_repository.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_approve_source_use_case_idempotent() -> None:
    source = _source(status=SourceStatus.VERIFIED, is_active=True)
    repository = AsyncMock()
    repository.get_by_id.return_value = source
    repository.update.return_value = source
    audit_repository = AsyncMock()
    fetcher = AsyncMock()
    fetcher.fetch.return_value = [MagicMock()]

    use_case = ApproveSourceUseCase(
        source_repository=repository,
        audit_repository=audit_repository,
        rss_fetcher=fetcher,
    )
    request = SourceDecisionRequest(id=source.id, reason="approved")

    response = await use_case.execute(request, actor_user_id=uuid4())

    assert response.status == SourceStatus.VERIFIED.value
    repository.update.assert_not_awaited()
    audit_repository.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_reject_source_use_case_updates_and_audits() -> None:
    source = _source()
    repository = AsyncMock()
    repository.get_by_id.return_value = source
    repository.update.return_value = source
    audit_repository = AsyncMock()

    use_case = RejectSourceUseCase(
        source_repository=repository,
        audit_repository=audit_repository,
    )
    request = SourceDecisionRequest(id=source.id, reason="rejected")

    response = await use_case.execute(request, actor_user_id=uuid4())

    assert response.status == SourceStatus.REJECTED.value
    repository.update.assert_awaited_once()
    audit_repository.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_reject_source_use_case_idempotent() -> None:
    source = _source(status=SourceStatus.REJECTED, is_active=True)
    repository = AsyncMock()
    repository.get_by_id.return_value = source
    repository.update.return_value = source
    audit_repository = AsyncMock()

    use_case = RejectSourceUseCase(
        source_repository=repository,
        audit_repository=audit_repository,
    )
    request = SourceDecisionRequest(id=source.id, reason="rejected")

    response = await use_case.execute(request, actor_user_id=uuid4())

    assert response.status == SourceStatus.REJECTED.value
    repository.update.assert_not_awaited()
    audit_repository.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_deactivate_source_use_case_updates_and_audits() -> None:
    source = _source(status=SourceStatus.VERIFIED, is_active=True)
    repository = AsyncMock()
    repository.get_by_id.return_value = source
    repository.update.return_value = source
    audit_repository = AsyncMock()

    use_case = DeactivateSourceUseCase(
        source_repository=repository,
        audit_repository=audit_repository,
    )
    request = SourceDecisionRequest(id=source.id, reason="deactivated")

    response = await use_case.execute(request, actor_user_id=uuid4())

    assert response.is_active is False
    repository.update.assert_awaited_once()
    audit_repository.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_deactivate_source_use_case_idempotent() -> None:
    source = _source(status=SourceStatus.VERIFIED, is_active=False)
    repository = AsyncMock()
    repository.get_by_id.return_value = source
    repository.update.return_value = source
    audit_repository = AsyncMock()

    use_case = DeactivateSourceUseCase(
        source_repository=repository,
        audit_repository=audit_repository,
    )
    request = SourceDecisionRequest(id=source.id, reason="deactivated")

    response = await use_case.execute(request, actor_user_id=uuid4())

    assert response.is_active is False
    repository.update.assert_not_awaited()
    audit_repository.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_approve_source_use_case_rolls_back_on_audit_failure() -> None:
    source = _source()
    repository = AsyncMock()
    repository.get_by_id.return_value = source
    repository.update.return_value = source
    repository.commit = AsyncMock()
    repository.rollback = AsyncMock()
    audit_repository = AsyncMock()
    audit_repository.create.side_effect = RuntimeError("audit write failed")
    audit_repository.commit = AsyncMock()
    audit_repository.rollback = AsyncMock()
    fetcher = AsyncMock()
    fetcher.fetch.return_value = [MagicMock()]

    use_case = ApproveSourceUseCase(
        source_repository=repository,
        audit_repository=audit_repository,
        rss_fetcher=fetcher,
    )
    request = SourceDecisionRequest(id=source.id, reason="approved")

    with pytest.raises(RuntimeError, match="audit write failed"):
        await use_case.execute(request, actor_user_id=uuid4())

    repository.rollback.assert_awaited()
    audit_repository.rollback.assert_awaited()


@pytest.mark.asyncio
async def test_approve_source_use_case_no_audit_on_source_update_failure() -> None:
    source = _source()
    repository = AsyncMock()
    repository.get_by_id.return_value = source
    repository.update.side_effect = RuntimeError("source update failed")
    repository.commit = AsyncMock()
    repository.rollback = AsyncMock()
    audit_repository = AsyncMock()
    audit_repository.commit = AsyncMock()
    audit_repository.rollback = AsyncMock()
    fetcher = AsyncMock()
    fetcher.fetch.return_value = [MagicMock()]

    use_case = ApproveSourceUseCase(
        source_repository=repository,
        audit_repository=audit_repository,
        rss_fetcher=fetcher,
    )
    request = SourceDecisionRequest(id=source.id, reason="approved")

    with pytest.raises(RuntimeError, match="source update failed"):
        await use_case.execute(request, actor_user_id=uuid4())

    audit_repository.create.assert_not_awaited()
    repository.rollback.assert_awaited()


@pytest.mark.asyncio
async def test_decide_missing_actor_fails_closed() -> None:
    source = _source()
    repository = AsyncMock()
    repository.get_by_id.return_value = source
    repository.update.return_value = source
    audit_repository = AsyncMock()
    fetcher = AsyncMock()
    fetcher.fetch.return_value = [MagicMock()]

    use_case = ApproveSourceUseCase(
        source_repository=repository,
        audit_repository=audit_repository,
        rss_fetcher=fetcher,
    )
    request = SourceDecisionRequest(id=source.id, reason="approved")

    with pytest.raises(ValidationError):
        await use_case.execute(request)

    repository.get_by_id.assert_not_awaited()
    repository.update.assert_not_awaited()
    audit_repository.create.assert_not_awaited()
    fetcher.fetch.assert_not_awaited()


@pytest.mark.asyncio
async def test_decide_invalid_actor_fails_closed() -> None:
    source = _source()
    repository = AsyncMock()
    repository.get_by_id.return_value = source
    repository.update.return_value = source
    audit_repository = AsyncMock()
    fetcher = AsyncMock()
    fetcher.fetch.return_value = [MagicMock()]

    use_case = ApproveSourceUseCase(
        source_repository=repository,
        audit_repository=audit_repository,
        rss_fetcher=fetcher,
    )
    request = SourceDecisionRequest(id=source.id, reason="approved")

    with pytest.raises(ValidationError):
        await use_case.execute(request, actor_user_id="not-a-uuid")

    repository.get_by_id.assert_not_awaited()
    repository.update.assert_not_awaited()
    audit_repository.create.assert_not_awaited()
    fetcher.fetch.assert_not_awaited()


@pytest.mark.asyncio
async def test_decide_spoofed_body_actor_ignored() -> None:
    source = _source()
    repository = AsyncMock()
    repository.get_by_id.return_value = source
    repository.update.return_value = source
    audit_repository = AsyncMock()
    fetcher = AsyncMock()
    fetcher.fetch.return_value = [MagicMock()]

    authenticated = uuid4()
    spoofed = uuid4()

    use_case = ApproveSourceUseCase(
        source_repository=repository,
        audit_repository=audit_repository,
        rss_fetcher=fetcher,
    )
    request = SourceDecisionRequest(id=source.id, reason="approved", actor_user_id=spoofed)

    await use_case.execute(request, actor_user_id=authenticated)

    audit = audit_repository.create.call_args.args[0]
    assert audit.actor_user_id == authenticated
    assert audit.actor_user_id != spoofed


@pytest.mark.asyncio
async def test_decide_audit_metadata_success() -> None:
    source = _source()
    repository = AsyncMock()
    repository.get_by_id.return_value = source
    repository.update.return_value = source
    audit_repository = AsyncMock()

    authenticated = uuid4()

    use_case = RejectSourceUseCase(
        source_repository=repository,
        audit_repository=audit_repository,
    )
    request = SourceDecisionRequest(id=source.id, reason="rejected")

    await use_case.execute(request, actor_user_id=authenticated)

    audit = audit_repository.create.call_args.args[0]
    assert audit.actor_user_id == authenticated
    assert audit.decision == "REJECT"
    assert audit.reason == "rejected"
    assert audit.previous_status == "pending_review"
    assert audit.resulting_status == "rejected"
    assert audit.previous_is_active is True
    assert audit.resulting_is_active is True


@pytest.mark.asyncio
async def test_approve_idempotent_does_not_fetch() -> None:
    source = _source(status=SourceStatus.VERIFIED, is_active=True)
    repository = AsyncMock()
    repository.get_by_id.return_value = source
    repository.update.return_value = source
    audit_repository = AsyncMock()
    fetcher = AsyncMock()
    fetcher.fetch.return_value = [MagicMock()]

    use_case = ApproveSourceUseCase(
        source_repository=repository,
        audit_repository=audit_repository,
        rss_fetcher=fetcher,
    )
    request = SourceDecisionRequest(id=source.id, reason="approved")

    response = await use_case.execute(request, actor_user_id=uuid4())

    assert response.changed is False
    fetcher.fetch.assert_not_awaited()
    repository.update.assert_not_awaited()
    audit_repository.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_decide_approve_audit_metadata_success() -> None:
    source = _source()
    repository = AsyncMock()
    repository.get_by_id.return_value = source
    repository.update.return_value = source
    audit_repository = AsyncMock()
    fetcher = AsyncMock()
    fetcher.fetch.return_value = [MagicMock()]

    authenticated = uuid4()

    use_case = ApproveSourceUseCase(
        source_repository=repository,
        audit_repository=audit_repository,
        rss_fetcher=fetcher,
    )
    request = SourceDecisionRequest(id=source.id, reason="approved")

    await use_case.execute(request, actor_user_id=authenticated)

    audit = audit_repository.create.call_args.args[0]
    assert audit.actor_user_id == authenticated
    assert audit.decision == "APPROVE"
    assert audit.reason == "approved"
    assert audit.previous_status == "pending_review"
    assert audit.resulting_status == "verified"
    assert audit.previous_is_active is True
    assert audit.resulting_is_active is True
    assert audit.validation_outcome == "feed validated: 1 entries"


@pytest.mark.asyncio
async def test_decide_empty_string_actor_fails_closed() -> None:
    source = _source()
    repository = AsyncMock()
    repository.get_by_id.return_value = source
    audit_repository = AsyncMock()

    use_case = ApproveSourceUseCase(
        source_repository=repository,
        audit_repository=audit_repository,
        rss_fetcher=AsyncMock(),
    )
    request = SourceDecisionRequest(id=source.id, reason="approved")

    with pytest.raises(ValidationError):
        await use_case.execute(request, actor_user_id="   ")

    repository.get_by_id.assert_not_awaited()
    repository.update.assert_not_awaited()
    audit_repository.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_decide_invalid_actor_type_fails_closed() -> None:
    source = _source()
    repository = AsyncMock()
    repository.get_by_id.return_value = source
    audit_repository = AsyncMock()

    use_case = ApproveSourceUseCase(
        source_repository=repository,
        audit_repository=audit_repository,
        rss_fetcher=AsyncMock(),
    )
    request = SourceDecisionRequest(id=source.id, reason="approved")

    with pytest.raises(ValidationError):
        await use_case.execute(request, actor_user_id=123)  # type: ignore[arg-type]

    repository.get_by_id.assert_not_awaited()
    repository.update.assert_not_awaited()
    audit_repository.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_decide_missing_repository_fails_closed() -> None:
    use_case = ApproveSourceUseCase(decision="APPROVE")
    request = SourceDecisionRequest(id=uuid4(), reason="approved")

    with pytest.raises(ValidationError):
        await use_case.execute(request, actor_user_id=uuid4())


@pytest.mark.asyncio
async def test_decide_source_not_found() -> None:
    repository = AsyncMock()
    repository.get_by_id.return_value = None
    use_case = ApproveSourceUseCase(
        source_repository=repository,
        audit_repository=AsyncMock(),
        rss_fetcher=AsyncMock(),
    )
    request = SourceDecisionRequest(id=uuid4(), reason="approved")

    with pytest.raises(SourceNotFoundError):
        await use_case.execute(request, actor_user_id=uuid4())

    repository.update.assert_not_awaited()


@pytest.mark.asyncio
async def test_deactivate_audit_metadata_success() -> None:
    source = _source(status=SourceStatus.VERIFIED, is_active=True)
    repository = AsyncMock()
    repository.get_by_id.return_value = source
    repository.update.return_value = source
    audit_repository = AsyncMock()

    authenticated = uuid4()

    use_case = DeactivateSourceUseCase(
        source_repository=repository,
        audit_repository=audit_repository,
    )
    request = SourceDecisionRequest(id=source.id, reason="deactivated")

    await use_case.execute(request, actor_user_id=authenticated)

    audit = audit_repository.create.call_args.args[0]
    assert audit.actor_user_id == authenticated
    assert audit.decision == "DEACTIVATE"
    assert audit.reason == "deactivated"
    assert audit.previous_status == "verified"
    assert audit.resulting_status == "verified"
    assert audit.previous_is_active is True
    assert audit.resulting_is_active is False
    assert audit.validation_outcome is None


@pytest.mark.asyncio
async def test_reject_rolls_back_on_audit_failure() -> None:
    source = _source()
    repository = AsyncMock()
    repository.get_by_id.return_value = source
    repository.update.return_value = source
    repository.rollback = AsyncMock()
    audit_repository = AsyncMock()
    audit_repository.create.side_effect = RuntimeError("audit write failed")
    audit_repository.rollback = AsyncMock()

    use_case = RejectSourceUseCase(
        source_repository=repository,
        audit_repository=audit_repository,
    )
    request = SourceDecisionRequest(id=source.id, reason="rejected")

    with pytest.raises(RuntimeError, match="audit write failed"):
        await use_case.execute(request, actor_user_id=uuid4())

    repository.rollback.assert_awaited()
    audit_repository.rollback.assert_awaited()


@pytest.mark.asyncio
async def test_deactivate_rolls_back_on_audit_failure() -> None:
    source = _source(status=SourceStatus.VERIFIED, is_active=True)
    repository = AsyncMock()
    repository.get_by_id.return_value = source
    repository.update.return_value = source
    repository.rollback = AsyncMock()
    audit_repository = AsyncMock()
    audit_repository.create.side_effect = RuntimeError("audit write failed")
    audit_repository.rollback = AsyncMock()

    use_case = DeactivateSourceUseCase(
        source_repository=repository,
        audit_repository=audit_repository,
    )
    request = SourceDecisionRequest(id=source.id, reason="deactivated")

    with pytest.raises(RuntimeError, match="audit write failed"):
        await use_case.execute(request, actor_user_id=uuid4())

    repository.rollback.assert_awaited()
    audit_repository.rollback.assert_awaited()


@pytest.mark.asyncio
async def test_approve_invalid_feed_response_fails_closed() -> None:
    source = _source()
    repository = AsyncMock()
    repository.get_by_id.return_value = source
    audit_repository = AsyncMock()
    fetcher = AsyncMock()
    fetcher.fetch.return_value = None

    use_case = ApproveSourceUseCase(
        source_repository=repository,
        audit_repository=audit_repository,
        rss_fetcher=fetcher,
    )
    request = SourceDecisionRequest(id=source.id, reason="approved")

    with pytest.raises(ValidationError):
        await use_case.execute(request, actor_user_id=uuid4())

    repository.update.assert_not_awaited()
    audit_repository.create.assert_not_awaited()


class _NoCommitRepo:
    def __init__(self, source: Source) -> None:
        self._source = source

    async def get_by_id(self, _: UUID) -> Source | None:
        return self._source

    async def update(self, s: Source) -> Source:
        return s


@pytest.mark.asyncio
async def test_decide_approve_without_audit_and_without_commit() -> None:
    source = _source()
    repository = _NoCommitRepo(source)
    fetcher = AsyncMock()
    fetcher.fetch.return_value = [MagicMock()]

    use_case = ApproveSourceUseCase(
        source_repository=repository,
        audit_repository=None,
        rss_fetcher=fetcher,
    )
    request = SourceDecisionRequest(id=source.id, reason="approved")

    response = await use_case.execute(request, actor_user_id=uuid4())

    assert response.changed is True
    assert response.status == SourceStatus.VERIFIED.value


@pytest.mark.asyncio
async def test_decide_commit_failure_rolls_back() -> None:
    source = _source()
    repository = AsyncMock()
    repository.get_by_id.return_value = source
    repository.update.return_value = source
    repository.commit = AsyncMock(side_effect=RuntimeError("commit failed"))
    repository.rollback = AsyncMock()
    audit_repository = AsyncMock()
    audit_repository.rollback = AsyncMock()
    fetcher = AsyncMock()
    fetcher.fetch.return_value = [MagicMock()]

    use_case = ApproveSourceUseCase(
        source_repository=repository,
        audit_repository=audit_repository,
        rss_fetcher=fetcher,
    )
    request = SourceDecisionRequest(id=source.id, reason="approved")

    with pytest.raises(RuntimeError, match="commit failed"):
        await use_case.execute(request, actor_user_id=uuid4())

    repository.rollback.assert_awaited()
    audit_repository.rollback.assert_awaited()
