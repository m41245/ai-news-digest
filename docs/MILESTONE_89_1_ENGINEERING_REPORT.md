# M89.1 Knowledge Graph Schema & Production Consistency Audit — Engineering Report

## Executive Summary

Milestone 89.1 is a production consistency audit for the M89 Knowledge Graph feature. A critical schema/migration mismatch was discovered and resolved: migration 029 used PostgreSQL native enum types, while the SQLAlchemy model and project convention use String-backed enum columns. The fix aligns migration 029 with the established project pattern (previously applied in migration 006 for `articles.status`).

**Commit:** pending  
**Branch:** main  
**Status:** ACCEPTED

## Audit Findings

### Critical: Migration/Model Schema Mismatch

**Issue:** Migration 029 created PostgreSQL native enum types (`entity_type`, `relationship_type`, `relationship_status`) for the `relationships` table columns. However, the `RelationshipModel` uses `Mapped[EntityType]`, `Mapped[RelationshipType]`, and `Mapped[RelationshipStatus]` with `String` column types — consistent with `ArticleModel`, `StoryClusterModel`, and `TrendModel`.

**Impact:** 
- `alembic upgrade` would fail on fresh databases with `invalid input value for enum relationship_status: "candidate"` because the SQLAlchemy model passes Python enum objects to String columns, but the migration expected native enum values.
- The e2e test `test_application_starts` was failing with the exact error above.

**Root Cause:** Migration 029 was authored with native PostgreSQL enums instead of String columns, breaking the project's established convention.

## Fix Applied

### Migration 029 Rewritten

Replaced PostgreSQL native enum creation and usage with `sa.String` columns:

```python
# Before (broken):
entity_type_enum = sa.Enum("company", "topic", "story", "article", name="entity_type")
relationship_type_enum = sa.Enum(..., name="relationship_type")
relationship_status_enum = sa.Enum("candidate", "verified", ..., name="relationship_status")
entity_type_enum.create(op.get_bind(), checkfirst=True)
# ... columns used entity_type_enum, relationship_type_enum, relationship_status_enum

# After (fixed):
sa.Column("subject_entity_type", sa.String(16), nullable=False, index=True)
sa.Column("relationship_type", sa.String(32), nullable=False, index=True)
sa.Column("status", sa.String(32), nullable=False, server_default="candidate", index=True)
```

Also removed the `Enum.drop()` calls from `downgrade()` since no native enums are created.

## Precedent

Migration 006 previously converted `articles.status` from a native enum to `VARCHAR`/String, establishing the project's preference for String-backed enum columns. M89.1 applies the same pattern to the relationships table.

## Files Changed

| File | Change |
|------|--------|
| `migrations/versions/029_add_knowledge_graph_relationships.py` | Replaced PostgreSQL native enums with String columns |

## Verification

### Tests

| Check | Result |
|-------|--------|
| M89 unit tests (`test_relationship.py`, `test_extract_relationships.py`) | 9/9 passed |
| Full regression suite | 2201/2201 passed |
| e2e `test_application_starts` | Previously failing — now passes |

### Static Analysis

| Check | Result |
|-------|--------|
| Ruff (M89 files) | All checks passed |
| MyPy (M89 modules) | No issues found |

### Schema Consistency

- ✅ `EntityType` enum values match migration String column constraints
- ✅ `RelationshipType` enum values match migration String column constraints
- ✅ `RelationshipStatus` enum values match migration String column constraints
- ✅ `RelationshipModel` uses String columns for all enum-backed fields
- ✅ Repository queries use string comparison (consistent with String columns)
- ✅ API serialization uses `.value` (consistent with String columns)

## Architecture Compliance

- ✅ Schema matches SQLAlchemy model definition
- ✅ Migration follows project convention (String-backed enums)
- ✅ No native PostgreSQL dependencies introduced
- ✅ Enum validation preserved at application layer via Python StrEnum
- ✅ `alembic heads` shows single coherent head (029)
- ✅ Backward compatible with existing M89 code

## Conclusion

M89.1 resolves a critical production-blocking schema mismatch. The relationships table now uses String columns consistent with the rest of the codebase, eliminating the native enum dependency and ensuring reliable database migrations and application startup.
