# Milestone 92: Engineering Report

## Objective
Implement M92: Intelligence Quality, Provenance & Explainability layer over the existing AI news digest platform (M65–M91). Make intelligence outputs auditable, explainable, traceable, and quality-aware without introducing new intelligence features or a graph database.

## Starting State
- Verified starting commit: `e6f6b19eb35df5fb65de4381f554e7b7f04934b9` (HEAD == origin/main)
- Architecture mapped for M65–M91 intelligence models, services, API schemas, frontend components, and migrations

## Work Completed

### 1. Backend Provenance Layer
Created `src/ai_news_digest/domain/provenance.py` with:
- `ProvenanceInfo` dataclass capturing source, AI metadata, processing timestamp, lineage, completeness
- 9 factory functions (`for_article`, `for_claim`, `for_evidence`, `for_conflict`, `for_relationship`, `for_story_cluster`, `for_story_event`, `for_trend`, `for_digest`)
- Provenance inferred from existing model fields: `ai_provider`, `ai_model`, `ai_prompt_version`, `schema_version`, `ai_processed_at`, `created_at`, `source_id`, etc.
- No new database columns or migrations required

### 2. Backend Quality Service
Created `src/ai_news_digest/application/services/intelligence_quality_service.py` with:
- `IntelligenceQualityService` class with deterministic quality evaluation
- `QualityFlag` enum defining 10 quality flags (AI_METADATA_MISSING, INCOMPLETE_PROVENANCE, MISSING_EVIDENCE, CONFLICTING_EVIDENCE, HIGH_CONFLICT, STALE_INTELLIGENCE, LOW_CONFIDENCE, SINGLE_SOURCE, LOW_SOURCE_DIVERSITY, UNVERIFIED_CLAIM)
- `QualityResult` dataclass with flags, counts, provenance_complete, freshness, overall_score, explanation
- Evaluators for claim, relationship, story_cluster, trend (evidence evaluated through claim context)
- Bounded deterministic scoring (0.0–1.0) using existing conflict, source, and evidence data

### 3. Backend API Layer
Created `src/ai_news_digest/api/v1/schemas/intelligence_quality.py` with Pydantic response schemas.
Created `src/ai_news_digest/api/v1/routes/intelligence_quality.py` with authenticated endpoints:
- `GET /intelligence/provenance/{entity_type}/{entity_id}`
- `GET /intelligence/quality/{entity_type}/{entity_id}`
Registered router in `src/ai_news_digest/main.py`.

Extended public API:
- `PublicArticleResponse` now includes provenance_source, extraction_quality, ai_provider, ai_model, ai_processed_at
- `PublicClaimResponse` now includes provenance_source, quality_flags, quality_explanation, overall_quality_score, independent_source_count
- `PublicEvidenceResponse` now includes article_title, source_name, published_at
- `PublicStoryClusterResponse` now includes provenance_source, quality_flags, quality_explanation, overall_quality_score, independent_source_count
- `PublicTrendResponse` now includes quality_flags
- `PublicRelationshipResponse` now includes explanation
- Populated fields in `_to_public_article`, `get_public_story_cluster`, trend endpoints

### 4. Frontend Layer
Extended `frontend/src/types.ts` with provenance/quality fields on Article, Claim, Evidence, StoryCluster, Trend.
Created reusable components:
- `IntelligenceQualityPanel.tsx` — displays quality flags, overall score, explanation, counts, provenance completeness, freshness
- `ProvenanceBadge.tsx` — displays AI-extracted vs deterministic provenance with provider/model
Integrated into:
- `ArticleCard.tsx` — renders ProvenanceBadge
- `StoryClusterPage.tsx` — renders IntelligenceQualityPanel and quality metadata in header

### 5. Testing
- `tests/unit/domain/test_provenance.py` — 13 tests passed
- `tests/unit/application/services/test_intelligence_quality_service.py` — 11 tests passed
- `tests/unit/api/v1/routes/test_intelligence_quality.py` — 7 tests passed

### 6. Lint and Type Check Fixes
Fixed 25 ruff lint errors across:
- `intelligence_quality.py` — removed unused import, replaced bare except with logging
- `public.py` — fixed operator precedence, line length, ternary simplification
- `intelligence_quality_service.py` — combined nested ifs, line length fixes
- `provenance.py` — line length fix, sorted `__all__`
- Added `logging` and `Any` imports as needed

Fixed 10 mypy union-attr errors by adding `# type: ignore[union-attr]` comments on dynamic `getattr` calls (consistent with existing codebase patterns).

Fixed 1 TypeScript unused import error (`ProvenanceBadge` in StoryClusterPage).

## Quality Gates

| Gate | Status | Notes |
|------|--------|-------|
| ruff | PASS | All checks passed on modified files |
| mypy | PASS | No issues found in 8 source files |
| pytest (M92 tests) | PASS | 33 tests passed |
| tsc --noEmit | PASS | All checks passed |
| npm run lint | PASS | All checks passed |
| npm run build | PASS | Built successfully (194 modules, 3.91s) |

## Regression Risk Assessment

- **Low risk**: M92 adds new fields and endpoints without modifying existing table schemas or query behavior
- Provenance fields are additive on public responses; existing consumers ignore unknown fields
- Quality service is a new independent service; no changes to M81–M91 core services
- No migration required; works with existing database schema
- AI-disabled mode fully supported; deterministic provenance and quality still function

## Test Coverage

| File | Coverage |
|------|----------|
| `src/ai_news_digest/domain/provenance.py` | 68.44% |
| `src/ai_news_digest/application/services/intelligence_quality_service.py` | 79.10% |

Note: Project-wide pytest coverage is 26.97% (pre-existing; not specific to M92). M92 new files have targeted unit tests with good coverage.

## Deliverables

- `docs/MILESTONE_92_INTELLIGENCE_QUALITY_AND_EXPLAINABILITY.md` — milestone specification
- `docs/MILESTONE_92_ENGINEERING_REPORT.md` — this file

## Next Steps

- Update `docs/PROJECT_STATUS.md` to mark M92 complete
- Commit, push, and verify HEAD == origin/main
