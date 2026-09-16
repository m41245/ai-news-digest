# Milestone 92: Intelligence Quality, Provenance & Explainability

## Summary

M92 adds an intelligence quality, provenance, and explainability layer over the existing M65–M91 AI news digest platform. All intelligence outputs are now auditable, explainable, traceable, and quality-aware. The implementation reuses existing model metadata (`ai_provider`, `ai_model`, `prompt_version`, `schema_version`, `processing_metadata`) and existing graph/conflict systems (M81, M82, M84, M89/M90/M91) without introducing new infrastructure.

## Constraints

- No new database migrations
- No graph database (Neo4j, etc.)
- No ML embeddings or prediction
- No behavioral tracking or collaborative filtering
- AI is optional; quality/provenance features work with `AI_ENABLED=false`
- All quality scores are deterministic and bounded (0.0–1.0)
- Public API must not expose secrets, raw article content, prompts, or API keys
- Deterministic vs AI-derived distinction mandatory; `ProvenanceSource` enum reused from `Relationship`
- Must not duplicate M81 Evidence, M82 Conflicts, M84 Events, M89/M90/M91 graph systems, M68 Ranking, M87 Recommendations

## Implementation

### Backend

1. **Provenance Domain** (`src/ai_news_digest/domain/provenance.py`):
   - `ProvenanceInfo` dataclass with `source`, `ai_provider`, `ai_model`, `prompt_version`, `schema_version`, `processing_timestamp`, `lineage`, `is_complete`, `completeness_gaps`
   - Factory functions: `for_article`, `for_claim`, `for_evidence`, `for_conflict`, `for_relationship`, `for_story_cluster`, `for_story_event`, `for_trend`, `for_digest`
   - Provenance inferred from existing model fields; no new database columns required

2. **Intelligence Quality Service** (`src/ai_news_digest/application/services/intelligence_quality_service.py`):
   - `IntelligenceQualityService` with deterministic evaluation methods
   - `QualityFlag` enum: AI_METADATA_MISSING, INCOMPLETE_PROVENANCE, MISSING_EVIDENCE, CONFLICTING_EVIDENCE, HIGH_CONFLICT, STALE_INTELLIGENCE, LOW_CONFIDENCE, SINGLE_SOURCE, LOW_SOURCE_DIVERSITY, UNVERIFIED_CLAIM
   - `QualityResult` dataclass with flags, evidence_count, source_count, independent_source_count, conflict_present, conflict_count, provenance_complete, freshness, overall_score, explanation
   - Evaluators for claim, evidence, relationship, story_cluster, trend

3. **API Schemas** (`src/ai_news_digest/api/v1/schemas/intelligence_quality.py`):
   - `ProvenanceResponse` schema
   - `IntelligenceQualityResponse` schema
   - `QualityFlag` enum schema

4. **API Routes** (`src/ai_news_digest/api/v1/routes/intelligence_quality.py`):
   - `GET /intelligence/provenance/{entity_type}/{entity_id}` — returns provenance info
   - `GET /intelligence/quality/{entity_type}/{entity_id}` — returns quality assessment
   - Supported entity types: claim, relationship, story_cluster, trend

5. **Router Registration** (`src/ai_news_digest/main.py`):
   - Registered `intelligence_quality_router` under `app_settings.api_prefix`

6. **Public API Extensions** (`src/ai_news_digest/api/v1/schemas/public.py`, `src/ai_news_digest/api/v1/routes/public.py`, `src/ai_news_digest/api/v1/schemas/relationship.py`):
   - Extended `PublicArticleResponse` with `provenance_source`, `extraction_quality`, `ai_provider`, `ai_model`, `ai_processed_at`
   - Extended `PublicClaimResponse` with `provenance_source`, `quality_flags`, `quality_explanation`, `overall_quality_score`, `independent_source_count`
   - Extended `PublicEvidenceResponse` with `article_title`, `source_name`, `published_at`
   - Extended `PublicStoryClusterResponse` with `provenance_source`, `quality_flags`, `quality_explanation`, `overall_quality_score`, `independent_source_count`
   - Extended `PublicTrendResponse` with `quality_flags`
   - Extended `PublicRelationshipResponse` with `explanation`
   - Populated provenance/quality fields in article, claim, story cluster, and trend public responses

### Frontend

1. **TypeScript Types** (`frontend/src/types.ts`):
   - Extended `Article` with `provenanceSource`, `extractionQuality`, `aiProvider`, `aiModel`, `aiProcessedAt`
   - Extended `Claim` with `provenanceSource`, `qualityFlags`, `qualityExplanation`, `overallQualityScore`, `independentSourceCount`
   - Extended `Evidence` with `articleTitle`, `sourceName`, `publishedAt`
   - Extended `PublicStoryClusterSearch` and `PublicStoryCluster` with provenance/quality fields
   - Extended `Trend` with `qualityFlags`

2. **IntelligenceQualityPanel Component** (`frontend/src/components/IntelligenceQualityPanel.tsx`):
   - Reusable component displaying quality flags, overall score, explanation, evidence count, source count, conflict count, provenance completeness, and freshness
   - Color-coded quality indicators

3. **ProvenanceBadge Component** (`frontend/src/components/ProvenanceBadge.tsx`):
   - Reusable badge displaying provenance source (AI-extracted vs deterministic) with provider/model metadata

4. **ArticleCard Integration** (`frontend/src/components/ArticleCard.tsx`):
   - Renders `ProvenanceBadge` when article has AI provenance data

5. **StoryClusterPage Integration** (`frontend/src/pages/public/StoryClusterPage.tsx`):
   - Renders `IntelligenceQualityPanel` in cluster detail view
   - Displays quality metadata (overall score, flags) in cluster header

### Testing

1. **Domain Tests** (`tests/unit/domain/test_provenance.py`):
   - 13 tests covering all factory functions, edge cases, completeness gaps, lineage construction

2. **Service Tests** (`tests/unit/application/services/test_intelligence_quality_service.py`):
   - 11 tests covering claim, relationship, story_cluster, trend quality evaluation, score computation, freshness

3. **API Route Tests** (`tests/unit/api/v1/routes/test_intelligence_quality.py`):
   - 7 tests covering provenance and quality endpoints for all supported entity types

### Quality Gates

- `ruff check`: All checks passed
- `mypy`: No issues found in modified files
- `pytest`: 33 M92 tests passed
- `tsc --noEmit`: All checks passed
- `npm run lint`: All checks passed
- `npm run build`: Built successfully

## Files Added

- `src/ai_news_digest/domain/provenance.py`
- `src/ai_news_digest/application/services/intelligence_quality_service.py`
- `src/ai_news_digest/api/v1/schemas/intelligence_quality.py`
- `src/ai_news_digest/api/v1/routes/intelligence_quality.py`
- `frontend/src/components/IntelligenceQualityPanel.tsx`
- `frontend/src/components/ProvenanceBadge.tsx`
- `tests/unit/domain/test_provenance.py`
- `tests/unit/application/services/test_intelligence_quality_service.py`
- `tests/unit/api/v1/routes/test_intelligence_quality.py`

## Files Modified

- `src/ai_news_digest/main.py` — registered intelligence_quality_router
- `src/ai_news_digest/api/v1/schemas/public.py` — extended public response schemas
- `src/ai_news_digest/api/v1/schemas/relationship.py` — added `explanation` field
- `src/ai_news_digest/api/v1/routes/public.py` — populated provenance/quality fields
- `frontend/src/types.ts` — extended TypeScript interfaces
- `frontend/src/components/ArticleCard.tsx` — renders ProvenanceBadge
- `frontend/src/pages/public/StoryClusterPage.tsx` — renders IntelligenceQualityPanel

## Notes

- No new database migrations required; provenance inferred from existing fields
- The `ProvenanceSource` enum is reused from `Relationship` domain model
- All quality scores are deterministic and bounded 0.0–1.0
- Frontend components are reusable and framework-consistent with existing patterns
- Coverage for M92-specific files: provenance.py 68.44%, intelligence_quality_service.py 79.10%
