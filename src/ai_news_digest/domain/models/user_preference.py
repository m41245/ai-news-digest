from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID


@dataclass(slots=True)
class UserPreferenceProfile:
    """
    Represents a user's personalized preference profile.
    """

    user_id: UUID
    followed_company_ids: frozenset[UUID] = frozenset()
    followed_topic_ids: frozenset[UUID] = frozenset()
    followed_category_ids: frozenset[UUID] = frozenset()
    muted_company_ids: frozenset[UUID] = frozenset()
    muted_topic_ids: frozenset[UUID] = frozenset()
    muted_category_ids: frozenset[UUID] = frozenset()
    min_importance: float = 0.0
    min_confidence: float = 0.0
    feed_sort: str = "published_at"
    freshness_window_days: int | None = None
    preferred_source_types: tuple[str, ...] = ()
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def touch(self) -> None:
        self.updated_at = datetime.now(UTC)
