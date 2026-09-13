# M65 — Article Intelligence Pipeline

**Date:** 2026-09-12  
**Commit SHA:** (pending commit)  
**Status:** COMPLETE — LOCAL QUALITY GATES PASSED

---

## 1. Objective

Implement structured AI analysis for stored articles with validated output, normalization, and persistence.

## 2. Scope

### In Scope
- Structured AI output validation using Pydantic v2
- Company name normalization with canonical entities and aliases
- Topic normalization with deduplication
- Updated analysis use cases with v1 structured prompt
- Database schema migration for AI metadata fields
- Admin endpoints for triggering article analysis
- Frontend type extensions for AI fields

### Out of Scope
- Real-time streaming analysis
- Multi-provider fallback logic
- Historical backfill of existing articles

## 3. Implementation Summary

### New Modules
- `src/ai_news_digest/application/ai/structured_output.py` — Pydantic v2 validation for structured AI output
- `src/ai_news_digest/application/ai/company_normalizer.py` — Company canonicalization with aliases
- `src/ai_news_digest/application/ai/topic_normalizer.py` — Topic deduplication and normalization

### Updated Modules
- `src/ai_news_digest/application/use_cases/article/analyze_article.py` — v1 structured prompt, validation, normalization, bounded input
- `src/ai_news_digest/application/use_cases/article/analyze_and_materialize.py` — Updated to use new normalizers
- `src/ai_news_digest/domain/models/article.py` — Added `ai_input_tokens`, `ai_output_tokens`, `ai_prompt_version`
- `src/ai_news_digest/infrastructure/database/models/article_model.py` — DB columns for new AI metadata
- `src/ai_news_digest/infrastructure/database/mappers/article_mapper.py` — Mapper updates for new fields
- `src/ai_news_digest/api/v1/schemas/article.py` — Extended `ArticleResponse`
- `src/ai_news_digest/api/v1/routes/articles.py` — Returns new fields in responses
- `src/ai_news_digest/api/v1/routes/admin.py` — New analysis trigger endpoints
- `src/ai_news_digest/frontend/src/types.ts` — Extended Article interface
- `src/ai_news_digest/frontend/src/api/index.ts` — Added `triggerArticleAnalysis`/`triggerPendingAnalysis`

### Database Migration
- `migrations/versions/018_add_ai_metadata_fields.py` — Adds `ai_input_tokens`, `ai_output_tokens`, `ai_prompt_version`

## 4. Architecture Notes

### StructuredIntelligence Validation
`StructuredIntelligence` is implemented as a **Pydantic v2 BaseModel** with field validators that:
- Strip and validate non-empty `summary`
- Bound `key_takeaways` to 8 items (max 300 chars each)
- Truncate `why_it_matters` to 2000 chars
- Deduplicate and bound `categories` (5 items, 64 chars)
- Deduplicate and bound `companies` (10 items, 128 chars)
- Deduplicate and bound `topics` (10 items, 64 chars)
- Clamp `confidence` and `importance` to [0.0, 1.0]

### ArticleResponse Contract
There are three distinct representations:
1. **Domain `Article`** (`domain/models/article.py`) — dataclass with `tuple[str, ...]` for list fields
2. **Application DTO `ArticleResponse`** (`application/dto/article/response.py`) — frozen dataclass including AI fields
3. **API `ArticleResponse`** (`api/v1/schemas/article.py`) — Pydantic BaseModel with `list[str] | None` for list fields

The application DTO was updated in M65.1 to include all AI intelligence fields, making it consistent with the API schema.

### Processing Lifecycle
The M65 structured analysis pipeline runs AFTER the legacy summarization/categorization pipeline:
1. `NEW` → `summarize_article` → `SUMMARIZED`
2. `SUMMARIZED` → `categorize_article` → `CATEGORIZED`
3. `CATEGORIZED` → `analyze_article` + `analyze_and_materialize` → `ANALYZED`

The `analysis` capability is now properly registered for all configured providers in `bootstrap/container.py`.

## 5. Test Results

### New Tests
- `tests/unit/application/ai/test_structured_output.py` — Structured output validation (35 tests)
- `tests/unit/application/ai/test_company_normalizer.py` — Company normalization
- `tests/unit/application/ai/test_topic_normalizer.py` — Topic normalization
- `tests/unit/infrastructure/database/mappers/test_article_mapper.py` — Round-trip persistence tests for AI fields
- `tests/unit/bootstrap/test_container.py` — Analysis capability wiring tests

### Updated Tests
- `tests/unit/application/use_cases/article/test_analyze_article.py` — Updated for v1 structured prompt
- `tests/unit/application/use_cases/article/test_analyze_and_materialize.py` — Updated for new normalizers

### Test Summary
- **Application tests:** 526 passed
- **API tests:** Included in 526
- **AI and article use case tests:** Included in 526
- **Infrastructure tests:** Included in 526
- **Admin route tests:** Included in 526
- **Migration tests:** 10 passed

## 6. Lint and Type Check

### Ruff
- Passed on all changed files
- No pre-existing warnings in changed files

### MyPy
- **0 errors** in 328 source files (resolved the 20 false-positive errors on routes file)
- Schema file passes cleanly
- Routes file passes cleanly

## 7. API Changes

### New Admin Endpoints
- `POST /admin/articles/{id}/analyze` — Trigger analysis for a single article
- `POST /admin/articles/analyze-pending` — Trigger analysis for all pending articles

### Extended Response Fields
- `importance_score` — AI-assigned importance (0.0-1.0)
- `confidence` — AI confidence level (0.0-1.0)
- `key_takeaways` — List of key insights
- `why_it_matters` — Explanation of significance
- `companies` — List of mentioned companies (canonicalized)
- `topics` — List of topics (deduplicated)
- `categories` — List of categories
- `ai_provider` — AI provider used
- `ai_model` — AI model used
- `ai_processed_at` — Timestamp of AI processing

## 8. Frontend Changes

### Type Extensions
- Extended `Article` interface with AI fields
- Added API functions for triggering analysis

## 9. Known Issues

- None. All quality gates pass.

## 10. Next Steps

1. Monitor M65 structured analysis pipeline in production
2. Verify Celery Beat scheduled analysis runs correctly
3. Consider M66 next milestone

## 11. Verification Checklist

- [x] New AI modules created and tested
- [x] StructuredIntelligence converted to Pydantic v2 model
- [x] Article analysis use cases updated with v1 structured prompt
- [x] Database migration created and applied
- [x] Admin endpoints added and tested
- [x] Frontend types extended
- [x] Unit tests pass for all M65 modules
- [x] Ruff lint passes on changed files
- [x] MyPy passes cleanly (0 errors in 328 source files)
- [x] Application DTO ArticleResponse updated with AI fields
- [x] Container registers analysis capability for providers
- [x] Round-trip persistence tests added
- [x] Documentation updated

---

## Summary

M65 Article Intelligence Pipeline is complete and hardened in M65.1. All new modules use Pydantic v2 validation, the container properly wires the analysis capability, application DTOs are consistent with API schemas, and all quality gates pass.
