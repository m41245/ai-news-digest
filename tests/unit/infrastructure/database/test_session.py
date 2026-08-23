"""
Unit tests for database session module.
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from ai_news_digest.infrastructure.database.session import (
    SessionLocal,
    engine,
    get_db_session,
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
    assert isinstance(sessions[0], AsyncSession)
