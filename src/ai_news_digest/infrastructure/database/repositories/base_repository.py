from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from ai_news_digest.core.exceptions import DatabaseError

ModelT = TypeVar("ModelT")
AddModelT = TypeVar("AddModelT")


class BaseRepository[ModelT]:
    """
    Base repository providing common SQLAlchemy persistence operations.

    Concrete repositories should inherit from this class and focus on
    entity-specific queries and mapping logic.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _add(
        self,
        model: ModelT,
    ) -> ModelT:
        """Add an ORM model to the current transaction."""
        self._session.add(model)
        return model

    async def _add_all(
        self,
        models: Iterable[AddModelT],
    ) -> None:
        """Add multiple ORM models to the current transaction."""
        self._session.add_all(list(models))

    async def _flush(self) -> None:
        """Flush pending SQL to the database without committing."""
        try:
            await self._session.flush()
        except Exception as exc:
            raise DatabaseError(f"Database flush failed: {exc}") from exc

    async def _commit(self) -> None:
        """Commit the current transaction."""
        try:
            await self._session.commit()
        except Exception as exc:
            raise DatabaseError(f"Database commit failed: {exc}") from exc

    async def _rollback(self) -> None:
        """Roll back the current transaction."""
        try:
            await self._session.rollback()
        except Exception as exc:
            raise DatabaseError(f"Database rollback failed: {exc}") from exc

    async def _refresh(
        self,
        model: ModelT,
    ) -> ModelT:
        """Refresh an ORM model from the database."""
        try:
            await self._session.refresh(model)
            return model
        except Exception as exc:
            raise DatabaseError(f"Database refresh failed: {exc}") from exc

    async def _add_and_refresh(
        self,
        model: ModelT,
    ) -> ModelT:
        """Persist, commit and refresh a model."""
        await self._add(model)
        await self._commit()
        await self._refresh(model)
        return model

    async def _delete(
        self,
        model: ModelT,
    ) -> None:
        """Delete an ORM model and commit."""
        try:
            await self._session.delete(model)
            await self._commit()
        except Exception as exc:
            raise DatabaseError(f"Database delete failed: {exc}") from exc
