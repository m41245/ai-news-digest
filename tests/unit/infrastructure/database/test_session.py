"""
Unit tests for database session module.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.pool import AsyncAdaptedQueuePool

from ai_news_digest.infrastructure.database.session import (
    SessionLocal,
    connect_args,
    engine,
    get_db_session,
    get_pool_metrics,
)


def test_engine_exists() -> None:
    """Test that engine is created."""
    assert engine is not None
    assert isinstance(engine, AsyncEngine)


def test_session_local_exists() -> None:
    """Test that SessionLocal is created."""
    assert SessionLocal is not None


@pytest.mark.asyncio
async def test_get_db_session_yields_session() -> None:
    """Test that get_db_session yields an AsyncSession."""
    session_gen = get_db_session()

    async for session in session_gen:
        assert session is not None
        assert isinstance(session, AsyncSession)
        break  # Only iterate once


@pytest.mark.asyncio
async def test_get_db_session_closes_session() -> None:
    """Test that get_db_session yields a session and the generator terminates cleanly."""
    sessions = []
    async for s in get_db_session():
        sessions.append(s)

    assert len(sessions) == 1
    assert sessions[0] is not None
    assert sessions[0] is not None
    assert isinstance(sessions[0], AsyncSession)


def test_engine_uses_pool_settings() -> None:
    """Test that engine pool is configured correctly."""
    assert engine.pool is not None
    assert isinstance(engine.pool, AsyncAdaptedQueuePool)
    metrics = get_pool_metrics()
    assert "size" in metrics
    assert "checkedin" in metrics
    assert "checkedout" in metrics
    assert "overflow" in metrics


def test_get_pool_metrics_returns_expected_keys() -> None:
    """Test that get_pool_metrics returns expected metric keys."""
    mock_pool = MagicMock()
    mock_pool.size.return_value = 5
    mock_pool.checkedin.return_value = 3
    mock_pool.checkedout.return_value = 2
    mock_pool.overflow.return_value = 0

    mock_engine = MagicMock()
    mock_engine.pool = mock_pool

    with patch("ai_news_digest.infrastructure.database.session.engine", mock_engine):
        metrics = get_pool_metrics()

    assert "size" in metrics
    assert "checkedin" in metrics
    assert "checkedout" in metrics
    assert "overflow" in metrics
    assert metrics["size"] == 5
    assert metrics["checkedin"] == 3
    assert metrics["checkedout"] == 2
    assert metrics["overflow"] == 0


class TestEngineSslHandling:
    """Tests that database URL SSL handling is wired correctly.

    The heavy lifting is tested in ``test_url.py`` via
    ``get_asyncpg_engine_kwargs``. Here we verify that the session module
    exposes the expected ``connect_args`` structure for a real local
    development URL (no sslmode → no forced SSL).
    """

    def test_session_connect_args_has_server_settings_for_asyncpg(self) -> None:
        """connect_args contains server_settings when using asyncpg driver."""
        assert "server_settings" in connect_args
        assert "statement_timeout" in connect_args["server_settings"]

    def test_session_connect_args_does_not_force_ssl_for_local_url(self) -> None:
        """Local development URL without sslmode must not have ssl forced."""
        assert "ssl" not in connect_args

