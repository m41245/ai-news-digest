# M87 Advanced Recommendation Intelligence — Final Engineering Report

## Executive Summary

Milestone 87 implements a deterministic, explainable recommendation engine for the AI News Digest platform. The engine combines multiple orthogonal signals—global importance, M86 personal relevance, freshness, story activity, trend momentum, story evolution, diversity, and novelty—into a bounded 0-100 `recommendation_score`. The implementation reuses the existing M86 personalization architecture, keeps global `ranking_score` separate, and introduces no behavioral tracking, collaborative filtering, or embeddings.

**Commit:** a9cf4deab2315aff329561150e485ccafd39d149  
**Branch:** main  
**Status:** ACCEPTED

## What Was Done

### Backend

1. **Recommendation Engine** (`src/ai_news_digest/application/services/recommendation/`)
   - `constants.py`: `RecommendationWeights`, `RecommendationDefaults`, `RecommendationSignal`, `ScoredCluster`
   - `recommendation_engine.py`: `RecommendationEngine` with `score_cluster`, `score_trend`, `select_diverse`
   - Deterministic scoring with fixed-point weights; all scores bounded to [0, 100]

2. **Use Case** (`src/ai_news_digest/application/use_cases/recommendation/`)
   - `get_recommendations.py`: `GetRecommendationsUseCase` orchestrating candidate retrieval, M86 personalization reuse, engine scoring, diversity selection, and response building
   - Handles both story clusters and trends in a single ranked list
   - Fallback recommendations for cold-start users with empty preferences

3. **API** (`src/ai_news_digest/api/v1/`)
   - `routes/recommendations.py`: `GET /api/v1/me/recommendations` with `page`, `page_size`, `sort` params
   - `schemas/recommendation.py`: `RecommendationResponseWrapper`, `RecommendationSort`
   - `dto/recommendation.py`: `RecommendationItemResponse`, `RecommendationResponse`

4. **Domain/Infrastructure Extensions**
   - Extended repository ports with batch ID lookups: `get_by_ids`, `get_by_cluster_ids`, `list_by_cluster_ids`
   - Implemented batch lookups in SQLAlchemy repositories
   - Registered `GetRecommendationsUseCase` in DI container

### Frontend

1. **RecommendationsPage** (`frontend/src/pages/dashboard/RecommendationsPage.tsx`)
   - Displays recommendations with score badges, item type tags, importance/trend indicators, activity status, companies, topics, categories, and explanation tags
   - Sections for stories and trends

2. **API Client & Types**
   - Added `personalizedApi.recommendations` to `frontend/src/api/index.ts`
   - Added `RecommendationItemResponse` and `RecommendationResponse` to `frontend/src/types.ts`
   - Registered `/me/recommendations` route in `App.tsx`

### Tests

- `tests/unit/application/services/recommendation/test_recommendation_engine.py`: engine scoring, diversity, bounds
- `tests/unit/application/use_cases/recommendation/test_get_recommendations.py`: use case orchestration, fallback, empty states
- `tests/unit/api/v1/routes/test_recommendations.py`: authenticated endpoint, pagination, sorting

## Scoring Model

### Story Cluster Signals

| Signal | Weight |
|--------|--------|
| Base score | 30.0 |
| Followed company | +12.0 |
| Followed topic | +10.0 |
| Followed category | +8.0 |
| Followed source | +6.0 |
| Preferred source type | +4.0 |
| High importance (>=0.8) | +10.0 |
| Strong confidence (>=0.9) | +6.0 |
| Multiple sources (>=3) | +4.0 |
| Recently updated (7d) | +4.0 |
| Fresh coverage (24h) | +6.0 |
| Breaking story | +12.0 |
| Developing story | +8.0 |
| Ongoing story | +4.0 |
| Stale story | -6.0 |
| Trend momentum strong | +8.0 |
| Trend momentum | +4.0 |
| Recent event (48h) | +4.0 |
| Multiple recent events | +2.0 |

### Diversity Penalties

- Max same company: 2
- Max same topic: 2
- Max same category: 2
- Max same source: 3
- Penalty per over-concentration: -15.0

## Quality Gates

| Gate | Result |
|------|--------|
| M87 unit tests | 23/23 pass |
| Full backend unit suite | 1613/1613 pass |
| MyPy (changed files) | Clean |
| Ruff (changed files) | Clean |
| Frontend typecheck | Pass |
| Frontend lint | Pass |

## Key Decisions

1. **Reused M86 architecture**: `PersonalizedRelevanceEngine` is called directly inside `RecommendationEngine.score_cluster`, avoiding duplicate preference logic.
2. **Separate scores**: `ranking_score` (global) remains untouched; `recommendation_score` is a new additive signal specific to the recommendations endpoint.
3. **Deterministic diversity**: `select_diverse` applies bounded penalties for over-concentration, preserving score order while ensuring variety.
4. **No new migrations**: Batch repository lookups were added to existing ports and implementations without schema changes.
5. **Activity enum handling**: Used `hasattr(status, "value")` guard for `StoryActivityStatus` StrEnum compatibility.

## Issues Fixed During Implementation

1. **TypeScript strict null checks**: Changed `!== null` to `!= null` in `RecommendationsPage.tsx` to satisfy TypeScript when fields are `number | null | undefined`.
2. **Mypy tuple unpacking**: Added `# type: ignore[assignment]` for a mypy quirk with `list[Article] | None` in for-loop unpacking.
3. **Activity variable scope**: Fixed `UnboundLocalError` by including `activity` in the `scored_items` tuple instead of relying on loop-scoped variable.
4. **StoryCluster attribute access**: Corrected `_build_story_response_item` to read `activity_status`/`activity_score` from the `StoryActivity` object rather than `StoryCluster`, which does not have those attributes.
5. **Pre-existing frontend unused imports**: Removed unused type imports from `frontend/src/api/index.ts` to unblock `tsc --noEmit`.

## Verification

- `HEAD == origin/main` at commit `a9cf4deab2315aff329561150e485ccafd39d149`
- All M87 tests pass
- No regressions in full unit test suite
- Documentation updated in `docs/PROJECT_STATUS.md`, `docs/MILESTONE_87_ADVANCED_RECOMMENDATIONS.md`, and `docs/MILESTONE_87_ENGINEERING_REPORT.md`

## Conclusion

**M87 ACCEPTED.** Advanced recommendation intelligence is complete, tested, documented, and merged to `main`.
