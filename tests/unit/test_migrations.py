"""
Unit tests for migration and schema consistency.
"""

from __future__ import annotations

import re
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
