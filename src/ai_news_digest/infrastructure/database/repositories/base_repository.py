from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, Generic, TypeVar

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

ModelT = TypeVar("ModelT")
AddModelT = TypeVar("AddModelT")


class BaseRepository(Generic[ModelT]):
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
        """
        Add an ORM model to the current transaction.

        Does not commit.
        """
        self._session.add(model)
        return model

    async def _add_all(
        self,
        models: Iterable[AddModelT],
    ) -> None:
        """
        Add multiple ORM models to the current transaction.

        Does not commit.
        """
        self._session.add_all(list(models))

    async def _flush(self) -> None:
        """
        Flush pending SQL to the database without committing.

        Useful when primary keys are required before commit.
        """
        await self._session.flush()

    async def _commit(self) -> None:
        """
        Commit the current transaction.
        """
        await self._session.commit()

    async def _rollback(self) -> None:
        """
        Roll back the current transaction.
        """
        await self._session.rollback()

    async def _refresh(
        self,
        model: ModelT,
    ) -> ModelT:
        """
        Refresh an ORM model from the database.
        """
        await self._session.refresh(model)
        return model

    async def _add_and_refresh(
        self,
        model: ModelT,
    ) -> ModelT:
        """
        Persist, commit and refresh a model.
        """
        await self._add(model)
        await self._commit()
        await self._refresh(model)
        return model

    async def _delete(
        self,
        model: ModelT,
    ) -> None:
        """
        Delete an ORM model and commit.
        """
        await self._session.delete(model)
        await self._commit()
