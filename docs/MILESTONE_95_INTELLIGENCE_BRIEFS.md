# M95 Intelligence Briefs & Story Exploration

## Overview

M95 composes existing M67-M94 intelligence capabilities into a coherent, evidence-first Story Intelligence Brief product experience.

## New Public API Endpoint

`GET /api/v1/public/story-clusters/{slug}/brief`

Returns a fully assembled intelligence brief for a public story cluster.

### Response Model: `StoryIntelligenceBriefResponse`

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Story cluster ID |
| `title` | `str` | Story cluster title |
| `slug` | `str` | URL slug |
| `status` | `str` | Story status (ACTIVE, etc.) |
| `article_count` | `int` | Number of articles in the cluster |
| `source_count` | `int` | Number of unique sources |
| `independent_source_count` | `int` | Number of independent sources |
| `summary` | `str \| null` | Executive summary |
| `key_takeaways` | `str[]` | Bounded key takeaways (max 8) |
| `why_it_matters` | `str \| null` | Why the story matters |
| `activity_status` | `str \| null` | M83 story activity status |
| `activity_score` | `float \| null` | M83 activity score |
| `latest_activity_at` | `str \| null` | Latest activity timestamp |
| `sources` | `BriefSourceItem[]` | Contributing sources (max 20, max 5 articles each) |
| `claims` | `BriefClaimItem[]` | M81 claims |
| `conflicts` | `BriefConflictItem[]` | M82 conflicts |
| `timeline` | `BriefTimelineItem[]` | M84 timeline events (max 30) |
| `story_evolution` | `BriefStoryEvolution \| null` | Story evolution summary |
| `trends` | `BriefTrendContext[]` | M85 trends |
| `entities` | `BriefEntitiesContext` | M89-M91 entities |
| `related_stories` | `BriefRelatedStoryItem[]` | M88/M90 related stories |
| `provenance` | `BriefProvenanceInfo \| null` | M92 provenance |
| `quality` | `BriefQualityIndicators` | M92/M94 quality indicators |
| `updated_at` | `str \| null` | Brief generation timestamp |
| `personalization` | `BriefPersonalizationContext \| null` | M86 personalization |

### Quality Indicators

| Field | Description |
|-------|-------------|
| `health_status` | `healthy`, `degraded`, `insufficient_data`, or `blocked` |
| `degraded` | `true` if health is degraded |
| `degraded_message` | Human-readable degraded explanation |
| `quality_flags` | List of quality flags |
| `overall_quality_score` | 0.0-1.0 score |

### Health Status Semantics

- **`healthy`**: Normal intelligence, full brief exposed.
- **`degraded`**: Some intelligence unavailable; brief exposed with degraded indication.
- **`insufficient_data`**: Not enough articles/sources; brief exposed with empty fallback sections.
- **`blocked`**: M94 quality gates have FAIL results for story-relevant components; endpoint returns HTTP 403.

### Error Responses

- `404 Not Found`: Story cluster does not exist.
- `403 Forbidden`: Intelligence is blocked by quality gates.

## Frontend: StoryClusterPage

The public story page (`/stories/{slug}`) renders the intelligence brief with progressive-disclosure sections:

1. Story Header
2. Executive Brief
3. Key Takeaways
4. Why It Matters
5. Sources (with provenance badges)
6. Claims & Evidence (with provenance badges)
7. Conflicts
8. Timeline
9. Story Evolution
10. Trend Context
11. Entity Context
12. Related Stories
13. Quality & Provenance

### Evidence-First UX

- Source-backed information is visually distinguished from AI-generated interpretation via `ProvenanceBadge`.
- Each source shows `ai_extracted` or `deterministic` provenance.
- Each claim shows its `provenance_source` (e.g., `ai_extracted`, `deterministic`).
- Source links include "Read original" text and link directly to the publisher.

### Loading/Error/Empty States

- Loading: `BriefSkeleton` component with animated placeholders.
- Error: `ErrorState` component with retry button.
- Empty: Graceful empty states for each section (no claims, no conflicts, etc.).

## AI_DISABLED Compatibility

When `AI_ENABLED=false`:
- No new LLM calls are made by the brief service.
- The brief falls back to deterministic article metadata.
- Empty/missing sections are handled gracefully.

## Caching

Brief responses are cached using the existing Redis `cache_store` with a 300-second TTL. Cache failures are silently suppressed.

## No New Database Tables

M95 uses existing domain models and repositories. No new migrations were added. The brief is assembled at request time from existing data.
