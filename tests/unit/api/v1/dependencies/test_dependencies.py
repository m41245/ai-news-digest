"""
Unit tests for the get_container FastAPI dependency.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from ai_news_digest.api.v1.dependencies.dependencies import get_container
from ai_news_digest.bootstrap.container import Container


async def test_get_container_yields_container_with_session() -> None:
    """The dependency must yield a Container backed by an AsyncSession."""
    mock_session = MagicMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    async def _mock_db_session():
        async with mock_session:
            yield mock_session

    containers = []
    with patch(
        "ai_news_digest.api.v1.dependencies.dependencies.get_db_session",
        return_value=_mock_db_session(),
    ):
        async for container in get_container():
            containers.append(container)

    assert len(containers) == 1
    container = containers[0]
    assert isinstance(container, Container)
    assert container._session is mock_session

    # The session context manager must be entered and exited exactly once.
    mock_session.__aenter__.assert_called_once()
    mock_session.__aexit__.assert_called_once()


async def test_get_container_yields_multiple_containers() -> None:
    """The dependency must yield a fresh Container per session."""
    mock_session = MagicMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    async def _mock_db_session():
        async with mock_session:
            yield mock_session

    with patch(
        "ai_news_digest.api.v1.dependencies.dependencies.get_db_session",
        return_value=_mock_db_session(),
    ):
        containers = [container async for container in get_container()]

    assert len(containers) == 1
    assert isinstance(containers[0], Container)
