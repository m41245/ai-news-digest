from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass(slots=True)
class User:
    """
    Represents an application user.
    """

    id: UUID
    email: str
    hashed_password: str
    is_active: bool
    is_admin: bool
    created_at: datetime

    @classmethod
    def create(
        cls,
        *,
        email: str,
        hashed_password: str,
        is_active: bool = True,
        is_admin: bool = False,
    ) -> User:
        """
        Factory method for creating a new user.
        """
        return cls(
            id=uuid4(),
            email=email,
            hashed_password=hashed_password,
            is_active=is_active,
            is_admin=is_admin,
            created_at=datetime.now(UTC),
        )
