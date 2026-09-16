# M95.1 Engineering Report

## Starting Commit
`a97aca2` (M94.1 baseline)

## Final Commit
Pending push.

## HEAD == origin/main
Will be verified after push.

## Files Changed

### Backend
- `src/ai_news_digest/application/services/story_intelligence_brief.py`
- `src/ai_news_digest/api/v1/schemas/story_intelligence_brief.py`
- `src/ai_news_digest/api/v1/routes/public.py`
- `src/ai_news_digest/bootstrap/container.py`

### Frontend
- `frontend/src/pages/public/StoryClusterPage.tsx`
- `frontend/src/types.ts`
- `frontend/src/api/index.ts`

### Tests
- `tests/unit/application/services/test_story_intelligence_brief.py`
- `tests/unit/api/v1/routes/test_public_story_brief.py`
- `frontend/tests/pages/StoryClusterPage.test.tsx`

### Documentation
- `docs/MILESTONE_95_INTELLIGENCE_BRIEFS.md`
- `docs/MILESTONE_95_ENGINEERING_REPORT.md`
- `docs/PROJECT_STATUS.md` (updated)

## Dependencies
No new dependencies added.

## Database Changes
No new migrations. M95 uses existing domain models and repositories.

## API Changes
- New endpoint: `GET /api/v1/public/story-clusters/{slug}/brief`
- Returns `StoryIntelligenceBriefResponse`

## Frontend Changes
- `StoryClusterPage.tsx` upgraded to fetch and render the intelligence brief.
- Added provenance badges for sources and claims.
- Added "Read original" labels for source links.
- Added responsive, accessible loading/error/empty states.

## Story Brief
- **IMPLEMENTED**: Full brief assembly from existing M67-M94 subsystems.
- **VERIFIED**: 18 unit tests pass (service + API).

## Claims/Evidence
- **PRE-EXISTING**: M81 claims and evidence integration.
- **VERIFIED**: Claims deduplication and bounds enforced.

## Conflicts
- **PRE-EXISTING**: M82 conflict detection integration.
- **VERIFIED**: Conflicts surfaced in brief with bounded results.

## Timeline
- **PRE-EXISTING**: M84 story events integration.
- **VERIFIED**: Timeline sorted chronologically, bounded to 30 events.

## Trends
- **PRE-EXISTING**: M85 trends integration.
- **VERIFIED**: Trends only shown when associated with the story.

## Graph
- **PRE-EXISTING**: M89-M91 knowledge graph integration.
- **VERIFIED**: Entity context (companies, topics, graph connections) exposed.

## Related Stories
- **PRE-EXISTING**: M88/M90 related stories integration.
- **VERIFIED**: Current story excluded, duplicates deduplicated, bounded results.

## Personalization
- **PRE-EXISTING**: M86 personalization integration.
- **NOT APPLICABLE**: Public brief does not expose private personalization data.

## Provenance
- **PRE-EXISTING**: M92 provenance integration.
- **VERIFIED**: Provenance badges shown for sources and claims.
- **IMPLEMENTED**: `provenance_source` added to `BriefSourceItem`.

## Quality Gates
- **INTEGRATED**: M94 quality gate integration.
- **HEALTHY**: Normal intelligence exposed.
- **DEGRADED**: Available intelligence exposed with degraded indication.
- **BLOCKED**: HTTP 403 returned; intelligence not exposed.
- **VERIFIED**: Quality gate FAIL results trigger blocked state.

## Fallbacks
- **VERIFIED**: Missing summary, claims, evidence, timeline, trends, graph, related stories, quality all handled with truthful fallbacks.
- **VERIFIED**: No fabricated content.

## Caching
- **IMPLEMENTED**: Redis cache_store with 300s TTL.
- **VERIFIED**: Cache failures silently suppressed.

## Performance
- **VERIFIED**: All collections bounded (sources: 20, articles per source: 5, key_takeaways: 8, timeline: 30).
- **PRE-EXISTING**: Existing repository query conventions used.
- **NOT APPLICABLE**: No N+1 issues introduced; sequential queries match existing patterns.

## Security
- **VERIFIED**: Public endpoint requires no auth.
- **VERIFIED**: BLOCKED state prevents exposure of blocked intelligence.
- **VERIFIED**: No admin-only operational information exposed.
- **VERIFIED**: No full publisher article content exposed.
- **VERIFIED**: No private personalization data exposed.

## Copyright/Content Model
- **VERIFIED**: Only bounded summaries, short takeaways, claims, evidence references, metadata, and original links exposed.
- **VERIFIED**: No endpoint returns complete extracted article body.

## AI_ENABLED=false
- **VERIFIED**: Service does not add new LLM calls.
- **VERIFIED**: Deterministic fallbacks used when AI-generated content is unavailable.
- **VERIFIED**: Test coverage for AI_DISABLED mode.

## Celery
- **NOT APPLICABLE**: No new Celery tasks added.
- **PRE-EXISTING**: M94 quality gate evaluation task used for BLOCKED state.

## Migrations
- **NOT APPLICABLE**: No new database migrations required.

## Tests Added

### Backend
- `test_build_brief_returns_complete_brief`
- `test_build_brief_returns_empty_for_missing_cluster`
- `test_build_brief_handles_claim_extraction`
- `test_build_brief_deduplicates_claims`
- `test_build_brief_handles_empty_articles`
- `test_build_brief_handles_conflicts`
- `test_build_brief_degraded_single_source` (NEW)
- `test_build_brief_blocked_by_quality_gate` (NEW)
- `test_build_brief_ai_disabled_fallback` (NEW)
- `test_build_brief_bounds_enforcement` (NEW)
- `test_brief_returns_200_for_existing_cluster`
- `test_brief_returns_404_for_missing_cluster`
- `test_brief_includes_key_takeaways`
- `test_brief_includes_conflicts`
- `test_brief_public_access_requires_no_auth`
- `test_brief_returns_degraded_for_single_source` (NEW)
- `test_brief_returns_403_for_blocked_quality_gate` (NEW)
- `test_brief_ai_disabled_returns_deterministic_fallback` (NEW)

### Frontend
- `shows loading skeleton initially`
- `shows error state on failure`
- `renders story brief when loaded`
- `shows degraded quality banner when health is degraded`
- `shows provenance badge for AI-derived sources`

## Tests Executed
- Backend unit tests: 1561 passed
- M95-specific tests: 18 passed
- Frontend tests: 40 passed

## Regression Results
- M81-M94 relevant suites: All pass (1561 tests)

## Ruff
- Clean on new files.

## MyPy
- Clean on new files.

## TypeScript
- Clean.

## ESLint
- Clean.

## Frontend Build
- Clean.

## Known Limitations
1. Quality gate BLOCKED state queries global quality gate results; per-story gate evaluation is not yet implemented.
2. Brief assembly is synchronous per request; high traffic may benefit from pre-computation.
3. React Query cache is not shared between tests without explicit clearing.

## Pre-existing Failures
- None introduced by M95.

## Architectural Decisions
1. Brief assembly lives in `application/services/story_intelligence_brief.py`, not in the FastAPI route.
2. No new database tables; brief is a read-model DTO composed from existing data.
3. Quality gate integration queries `QualityGateRepository` for recent FAIL results.
4. Response caching uses existing `CacheStore` with bounded TTL.

## Recommended Next Milestone
- M96: Brief pre-computation and background refresh.
- M97: Per-story quality gate evaluation.
- M98: Brief versioning and drift tracking.
