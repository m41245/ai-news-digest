from __future__ import annotations

from typing import Any


class CompanyRepository:
    """
    Repository interface for company entities.
    """

    async def get_by_id(self, company_id: str) -> Any | None:
        raise NotImplementedError

    async def get_by_slug(self, slug: str) -> Any | None:
        raise NotImplementedError

    async def list_by_ids(self, company_ids: list[str]) -> list[Any]:
        raise NotImplementedError

    async def create(self, company: Any) -> Any:
        raise NotImplementedError

    async def update(self, company: Any) -> Any:
        raise NotImplementedError

    async def delete(self, company_id: str) -> None:
        raise NotImplementedError
