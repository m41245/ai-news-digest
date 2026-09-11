"""
Unit tests for migration and schema consistency.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from alembic.config import Config


def test_alembic_config_loads() -> None:
    """Test that Alembic configuration is valid."""
    alembic_ini = Path(__file__).resolve().parent.parent.parent / "alembic.ini"
    config = Config(str(alembic_ini))
    assert config is not None
    script_location = config.get_main_option("script_location")
    assert script_location is not None
    assert "migrations" in script_location


def test_migration_files_exist() -> None:
    """Test that all migration files are present and importable."""
    migrations_dir = Path(__file__).resolve().parent.parent.parent / "migrations" / "versions"
    migration_files = sorted(migrations_dir.glob("*.py"))

    assert len(migration_files) >= 1, "No migration files found"

    for migration_file in migration_files:
        assert migration_file.exists()
        content = migration_file.read_text()
        assert "revision:" in content
        assert "down_revision:" in content
        assert "upgrade()" in content
        assert "downgrade()" in content


def test_migration_chain_consistency() -> None:
    """Test that migration revisions form a valid chain."""
    migrations_dir = Path(__file__).resolve().parent.parent.parent / "migrations" / "versions"
    migration_files = sorted(migrations_dir.glob("*.py"))

    revisions = {}
    for migration_file in migration_files:
        content = migration_file.read_text()
        revision_match = re.search(r"Revision ID:\s*(\w+)", content)
        down_revision_match = re.search(r"^Revises:\s*(\w*)\s*$", content, re.MULTILINE)

        revision = revision_match.group(1) if revision_match else None
        down_revision = down_revision_match.group(1) if down_revision_match else None
        if down_revision == "":
            down_revision = None

        assert revision is not None, f"Missing revision in {migration_file}"
        revisions[revision] = down_revision

    # First migration should have None down_revision
    first_migration = migration_files[0]
    content = first_migration.read_text()
    down_revision_match = re.search(r"^Revises:\s*(\w*)\s*$", content, re.MULTILINE)
    down_revision = down_revision_match.group(1) if down_revision_match else None
    if down_revision == "":
        down_revision = None
    assert down_revision is None

    # All other revisions should reference a known parent
    for rev, down in revisions.items():
        if down is not None:
            assert down in revisions, f"Migration {rev} references unknown parent {down}"


def test_article_status_enum_in_migration() -> None:
    """Test that ArticleStatus enum values are present across migrations."""
    migrations_dir = Path(__file__).resolve().parent.parent.parent / "migrations" / "versions"
    all_migration_content = ""
    for migration_file in sorted(migrations_dir.glob("*.py")):
        all_migration_content += migration_file.read_text()

    # Verify the initial migration creates the articlestatus enum
    assert "articlestatus" in all_migration_content
    assert "new" in all_migration_content
    assert "summarized" in all_migration_content
    assert "categorized" in all_migration_content
    assert "ready" in all_migration_content


def test_migration_files_are_importable() -> None:
    """Test that all migration modules can be imported without errors."""
    migrations_dir = Path(__file__).resolve().parent.parent.parent / "migrations" / "versions"
    project_root = Path(__file__).resolve().parent.parent.parent

    for migration_file in sorted(migrations_dir.glob("*.py")):
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import sys; import importlib.util; "
                f"sys.path.insert(0, r'{project_root}'); "
                f"spec = importlib.util.spec_from_file_location('migration', r'{migration_file}'); "
                "mod = importlib.util.module_from_spec(spec); "
                "spec.loader.exec_module(mod); print('OK')",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Failed to import {migration_file.name}: {result.stderr}"


def test_migration_revision_ids_are_unique() -> None:
    """Test that all migration revision IDs are unique."""
    migrations_dir = Path(__file__).resolve().parent.parent.parent / "migrations" / "versions"
    revision_ids = []

    for migration_file in sorted(migrations_dir.glob("*.py")):
        content = migration_file.read_text()
        revision_match = re.search(r"Revision ID:\s*(\w+)", content)
        assert revision_match is not None, f"Missing revision in {migration_file}"
        revision_ids.append(revision_match.group(1))

    assert len(revision_ids) == len(set(revision_ids)), "Duplicate revision IDs found"


def test_migration_heads_are_consistent() -> None:
    """Test that alembic heads can be resolved without errors."""
    alembic_ini = Path(__file__).resolve().parent.parent.parent / "alembic.ini"
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", str(alembic_ini), "heads"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"alembic heads failed: {result.stderr}"
    assert "head" in result.stdout.lower() or "revision" in result.stdout.lower()


def test_psycopg2_not_in_dependencies() -> None:
    """psycopg2 must not be a declared dependency; asyncpg is the driver."""
    pyproject = Path(__file__).resolve().parent.parent.parent / "pyproject.toml"
    content = pyproject.read_text()
    assert "psycopg2" not in content, "psycopg2 must not be in pyproject.toml dependencies"


def test_migrations_use_async_engine() -> None:
    """migrations/env.py must use async_engine_from_config, not sync create_engine."""
    env_py = Path(__file__).resolve().parent.parent.parent / "migrations" / "env.py"
    content = env_py.read_text()
    assert "async_engine_from_config" in content
    assert "create_engine" not in content


def test_migrations_env_uses_shared_database_connection_helper() -> None:
    """Alembic must use the same URL and connect-args helper as the app.

    This prevents libpq-only parameters such as ``channel_binding`` from
    leaking into asyncpg during the Docker startup migration.
    """
    env_py = Path(__file__).resolve().parent.parent.parent / "migrations" / "env.py"
    content = env_py.read_text()
    assert "get_asyncpg_engine_kwargs" in content
    assert "connect_args=connect_args" in content
    assert "ai_news_digest.infrastructure.database.url" in content
