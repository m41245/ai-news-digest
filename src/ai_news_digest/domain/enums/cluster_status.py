from __future__ import annotations

from enum import StrEnum


class ClusterStatus(StrEnum):
    """
    Lifecycle status of a story cluster.
    """

    ACTIVE = "active"

    ARCHIVED = "archived"

    MERGED = "merged"
