from __future__ import annotations

from typing import Any
from uuid import UUID

from ai_news_digest.application.dto.source import SourceResponse
from ai_news_digest.application.exceptions.source import SourceNotFoundError
from ai_news_digest.core.exceptions import ValidationError
from ai_news_digest.domain.enums.source_status import SourceStatus
from ai_news_digest.domain.models.source_trust_decision import SourceTrustDecision


def _coerce_actor(actor: Any) -> UUID:
    if actor is None:
        raise ValidationError("Actor identity is required.")
    if isinstance(actor, UUID):
        return actor
    if isinstance(actor, str):
        value = actor.strip()
        if not value:
            raise ValidationError("Actor identity is required.")
        try:
            return UUID(value)
        except ValueError as exc:
            raise ValidationError("Invalid actor identity.") from exc
    raise ValidationError("Invalid actor identity.")


class DecideSourceTrustUseCase:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._source_repository = (
            kwargs.get("source_repository")
            or kwargs.get("repository")
            or kwargs.get("source_repo")
            or (args[0] if len(args) > 0 else None)
        )
        self._audit_repository = (
            kwargs.get("audit_repository")
            or kwargs.get("source_trust_decision_repository")
            or kwargs.get("source_audit_repository")
            or kwargs.get("decision_repository")
            or (args[1] if len(args) > 1 else None)
        )
        self._rss_fetcher = (
            kwargs.get("rss_fetcher")
            or kwargs.get("feed_fetcher")
            or kwargs.get("fetcher")
            or (args[2] if len(args) > 2 else None)
        )
        self._decision = kwargs.get("decision", "APPROVE")

    async def execute(self, request: Any, *, actor_user_id: Any = None) -> SourceResponse:
        source_id = getattr(request, "id", None)
        reason = getattr(request, "reason", "") or ""
        decision = getattr(request, "decision", None) or self._decision

        if self._source_repository is None:
            raise ValidationError("Source repository is required.")

        resolved_actor = _coerce_actor(actor_user_id)

        source = await self._source_repository.get_by_id(source_id)
        if source is None:
            raise SourceNotFoundError(str(source_id))

        previous_status = (
            source.status.value if hasattr(source.status, "value") else str(source.status)
        )
        previous_is_active = source.is_active
        validation_outcome: str | None = None

        already_approved = (
            decision == "APPROVE" and source.status == SourceStatus.VERIFIED and source.is_active
        )
        if decision == "APPROVE" and not already_approved:
            fetcher = self._rss_fetcher
            if fetcher is None:
                raise ValidationError("Feed validation unavailable: RSS fetcher is not configured.")
            try:
                entries = await fetcher.fetch(source.feed_url)
            except Exception as exc:
                raise ValidationError(f"Feed validation failed: {exc}") from exc
            if not entries:
                raise ValidationError("Feed validation failed: no credible feed entries found.")
            validation_outcome = f"feed validated: {len(entries)} entries"

        changed = False
        if decision == "APPROVE":
            if already_approved:
                changed = False
            elif source.status != SourceStatus.VERIFIED or not source.is_active:
                source.status = SourceStatus.VERIFIED
                source.is_active = True
                changed = True
        elif decision == "REJECT":
            if source.status != SourceStatus.REJECTED:
                source.status = SourceStatus.REJECTED
                changed = True
        elif decision == "DEACTIVATE" and source.is_active:
            source.is_active = False
            changed = True

        if changed:
            try:
                updated = await self._source_repository.update(source)
                source = updated
                resulting_status = (
                    source.status.value if hasattr(source.status, "value") else str(source.status)
                )
                resulting_is_active = source.is_active
                if self._audit_repository is not None:
                    audit = SourceTrustDecision(
                        source_id=source.id,
                        actor_user_id=resolved_actor,
                        decision=decision,
                        previous_status=previous_status,
                        resulting_status=resulting_status,
                        previous_is_active=previous_is_active,
                        resulting_is_active=resulting_is_active,
                        reason=reason,
                        validation_outcome=validation_outcome,
                    )
                    await self._audit_repository.create(audit)
                if hasattr(self._source_repository, "commit"):
                    await self._source_repository.commit()
            except Exception:
                if hasattr(self._source_repository, "rollback"):
                    await self._source_repository.rollback()
                if self._audit_repository is not None and hasattr(
                    self._audit_repository, "rollback"
                ):
                    await self._audit_repository.rollback()
                raise

        return SourceResponse(
            id=str(source.id),
            name=source.name,
            feed_url=source.feed_url,
            website_url=source.website_url,
            description=source.description,
            is_active=source.is_active,
            status=source.status.value if hasattr(source.status, "value") else str(source.status),
            decision=decision,
            previous_status=previous_status,
            previous_is_active=previous_is_active,
            reason=reason,
            validation_outcome=validation_outcome,
            changed=changed,
        )


class ApproveSourceUseCase(DecideSourceTrustUseCase):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("decision", "APPROVE")
        super().__init__(*args, **kwargs)


class RejectSourceUseCase(DecideSourceTrustUseCase):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("decision", "REJECT")
        super().__init__(*args, **kwargs)


class DeactivateSourceUseCase(DecideSourceTrustUseCase):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("decision", "DEACTIVATE")
        super().__init__(*args, **kwargs)
