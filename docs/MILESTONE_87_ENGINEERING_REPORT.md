# Milestone 87 Engineering Report

## Executive Summary

Milestone 87 adds advanced recommendation intelligence to the platform. A new deterministic `RecommendationEngine` combines global importance, M86 personal relevance, freshness, story activity, trend momentum, story evolution, diversity, and novelty into a bounded 0-100 `recommendation_score`. The engine is provider-independent, privacy-conscious, and explainable. All recommendation logic is additive and does not modify the existing global `ranking_score`.

## Architecture

### Domain Layer

- `RecommendationSignal` dataclass for individual signal contributions
- `ScoredCluster` dataclass for scored story/trend candidates
- `RecommendationWeights` and `RecommendationDefaults` for deterministic constants
- Repository ports extended with `get_by_ids`, `get_by_cluster_ids`, and `list_by_cluster_ids`

### Infrastructure Layer

- Repository implementations support batch ID lookups for clusters, activities, and events
- No new database models or migrations required

### Application Layer

- `RecommendationEngine`: pure scoring service with `score_cluster`, `score_trend`, and `select_diverse`
- `GetRecommendationsUseCase`: orchestrates candidate retrieval, scoring, diversity selection, and response building
- Reuses `PersonalizedRelevanceEngine` from M86 for personal relevance signals

### API Layer

- `GET /api/v1/me/recommendations` — authenticated personalized recommendations
- Query params: `page`, `page_size`, `sort`
- Response model: `RecommendationResponseWrapper` extending `RecommendationResponse`

### Frontend

- `/me/recommendations` — RecommendationsPage with score badges, activity/trend indicators, and reason tags
- TypeScript API client: `personalizedApi.recommendations`
- Types: `RecommendationItemResponse`, `RecommendationResponse`

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
| Multiple independent sources (>=3) | +4.0 |
| Recently updated (7 days) | +4.0 |
| Fresh coverage (24 hours) | +6.0 |
| Breaking story | +12.0 |
| Developing story | +8.0 |
| Ongoing story | +4.0 |
| Stale story | -6.0 |
| Trend momentum strong (>=70) | +8.0 |
| Trend momentum (>=50) | +4.0 |
| Recent event (48 hours) | +4.0 |
| Multiple recent events | +2.0 |

### Trend Signals

| Signal | Weight |
|--------|--------|
| Base score | 30.0 |
| Followed company | +12.0 |
| Followed topic | +10.0 |
| Followed category | +8.0 |
| Strong trend signal (>=70) | +8.0 |
| Trending (>=50) | +4.0 |
| Strong accelerating trend (momentum >=70) | +8.0 |
| Trend with momentum (momentum >=50) | +4.0 |

### Diversity Selection

- Max same company: 2
- Max same topic: 2
- Max same category: 2
- Max same source: 3
- Diversity penalty: -15.0 per over-concentration
- Adjusted scores bounded to 0-100

## Data Model Changes

No new database migrations required. Existing repository ports extended with batch lookup methods:

- `StoryClusterRepository.get_by_ids(ids)`
- `StoryActivityRepository.get_by_cluster_ids(cluster_ids)`
- `StoryEventRepository.list_by_cluster_ids(cluster_ids, limit)`

## Privacy & Security

- No behavioral tracking
- No collaborative filtering
- No embeddings
- No cross-user data leakage
- All `/me/*` routes protected by `get_current_active_user`
- Mute precedence enforced before scoring
- Cold start produces valid fallback recommendations

## Performance

- Candidate queries bounded at database layer
- Batch ID lookups avoid N+1 patterns
- Diversity selection runs in O(n * d) where n = candidates, d = diversity dimensions
- Trend matching uses set intersection for efficiency

## Quality Gates

| Gate | Result |
|------|--------|
| M87 tests | 23/23 pass |
| Backend unit tests | 1613/1613 pass |
| MyPy (changed files) | Clean |
| Ruff (changed files) | Clean |
| Frontend typecheck | Pass |
| Frontend lint | Pass |

## Committed Files

13 modified, 12 new untracked (excluding pre-existing documentation files).

## Conclusion

**M87 ACCEPTED.** Advanced recommendation intelligence is complete, tested, and ready for integration.
