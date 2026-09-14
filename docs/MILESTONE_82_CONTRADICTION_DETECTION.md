# M82 — Cross-Source Contradiction & Conflict Detection

## Purpose

M82 introduces **cross-source contradiction and conflict detection** to the platform. The system now identifies when multiple sources make contradictory claims about the same subject and surfaces these conflicts for human review.

This milestone builds on the M81 Claim/Evidence infrastructure and:

- Detects numeric, date, and event-state conflicts between claims
- Generates bounded candidate pairs based on entity overlap and temporal proximity
- Computes deterministic confidence scores for potential conflicts
- Optionally invokes LLM analysis for uncertain high-value pairs
- Persists conflicts with deduplication and canonical pair ordering
- Exposes conflicts via public API and frontend
- Runs as a scheduled Celery task

## Architecture

M82 follows the existing hexagonal architecture:

```
Application
  ├── use_cases/claim/detect_conflicts.py (orchestration)
  └── evaluation/
        ├── conflict_candidates.py (candidate generation)
        ├── conflict_detector.py (deterministic detection)
        ├── conflict_confidence.py (confidence heuristic)
        ├── conflict_explanation.py (explanations)
        └── conflict_llm.py (optional LLM analysis)

Domain
  ├── models/conflict.py
  ├── enums/conflict_type.py
  ├── enums/conflict_status.py
  └── ports/conflict_repository.py

Infrastructure
  ├── database/models/conflict_model.py
  ├── database/mappers/conflict_mapper.py
  └── database/repositories/conflict_repository.py

Workers
  └── tasks/conflict.py (Celery task)
```

## Conflict Model

### Conflict Domain Model

`src/ai_news_digest/domain/models/conflict.py`

A `Conflict` represents a potential contradiction between two claims:

- `id`: UUID
- `claim_a_id`: UUID
- `claim_b_id`: UUID
- `article_a_id`: UUID
- `article_b_id`: UUID
- `source_a_id`: UUID
- `source_b_id`: UUID
- `conflict_type`: ConflictType enum
- `status`: ConflictStatus enum
- `confidence`: float (0.0 to 1.0)
- `explanation`: str
- `detection_version`: str
- `story_cluster_id`: UUID | None
- `same_source`: bool
- `metadata`: dict[str, str]
- `created_at`: datetime
- `updated_at`: datetime

### Conflict Types

`src/ai_news_digest/domain/enums/conflict_type.py`

- `NUMERIC` — differing quantitative values (e.g., "70B parameters" vs "120B parameters")
- `DATE` — incompatible dates or timelines
- `EVENT_STATUS` — incompatible event states (e.g., "launched" vs "cancelled")

### Conflict Status

`src/ai_news_digest/domain/enums/conflict_status.py`

- `POTENTIAL` — detected by deterministic or LLM analysis, awaiting review

## Detection Pipeline

The `DetectClaimConflictsUseCase` orchestrates the following steps:

1. **Retrieve recent claims** — bounded by `conflict_detection_max_claims`
2. **Build claim contexts** — enrich claims with article, source, company, and topic metadata
3. **Generate candidates** — bounded pair generation based on:
   - Claim type compatibility
   - Entity overlap (company or topic)
   - Token overlap
   - Temporal proximity
4. **Run deterministic detection** — rule-based numeric, date, and event-state detectors
5. **Optional LLM analysis** — for uncertain pairs when AI is enabled and confidence < 0.8
6. **Compute confidence** — weighted heuristic combining entity match, temporal compatibility, and evidence support
7. **Deduplicate and persist** — canonical pair ordering prevents duplicates

## Deterministic Detection

Deterministic detectors are conservative and prefer false negatives over false positives:

### Numeric Conflict Detection

Extracts numeric values with units from claim text and compares them:

- Single-value comparison: exact mismatch required
- Multi-value comparison: overlapping ranges are not flagged
- Unit normalization handles common suffixes (billion, million, percent, etc.)

### Date Conflict Detection

Extracts date patterns and compares them:

- Supports ISO dates, relative dates, and date ranges
- Flags incompatible date ranges
- Ignores dates without explicit conflict

### Event State Conflict Detection

Compares event states using an incompatibility matrix:

- `announced` conflicts with `cancelled`, `denied`
- `planned` conflicts with `cancelled`, `completed`
- `launched` conflicts with `cancelled`, `delayed`, `denied`
- `completed` conflicts with `planned`, `cancelled`, `denied`

## Confidence Computation

`src/ai_news_digest/application/evaluation/conflict_confidence.py`

Confidence is computed as a weighted combination of factors:

- Entity match (company or topic overlap): +0.15
- Temporal compatibility: +0.10
- Numeric mismatch: +0.20
- Date mismatch: +0.20
- Event state mismatch: +0.25
- Evidence support (average of both claims): +0.15 per 0.5 score
- Source independence (different sources): +0.10

Confidence is clamped to [0.0, 1.0].

## LLM Analysis (Optional)

`src/ai_news_digest/application/evaluation/conflict_llm.py`

LLM analysis is invoked only when:

- `AI_ENABLED=true`
- Provider manager is available
- LLM call budget not exceeded
- Deterministic confidence < 0.8

The LLM prompt includes:

- Both claim texts with their types
- Deterministic detection note (if any)
- Instructions to respond with structured JSON

**Security**: Prompt injection defense ensures article content cannot override system instructions.

## Candidate Generation

`src/ai_news_digest/application/evaluation/conflict_candidates.py`

Candidates are generated with bounded computation:

- `max_candidates_per_claim`: maximum pairs per claim (default 10)
- `max_total_candidates`: global maximum (default 200)
- `temporal_window_hours`: maximum time difference for comparison (default 72)

Type compatibility groups:

- `quantitative` ↔ `quantitative`
- `event` ↔ `event`, `announcement`
- `product` ↔ `product`, `research`
- `company` ↔ `company`, `event`
- `policy` ↔ `policy`
- `general` ↔ `general`, `other`

## Persistence

`src/ai_news_digest/infrastructure/database/repositories/conflict_repository.py`

Conflicts are persisted with:

- Canonical pair ordering (`claim_a_id <= claim_b_id`) for deduplication
- Unique constraint on `(claim_a_id, claim_b_id, detection_version)`
- Eager loading of related articles and sources

Alembic migration `023_add_conflicts.py` creates the `conflicts` table.

## Celery Integration

`src/ai_news_digest/workers/tasks/conflict.py`

A new Celery task `detect_claim_conflicts`:

- Runs daily at 09:00 (configurable via beat schedule)
- Is idempotent (safe to retry)
- Records metrics (duration, success, failure)
- Returns summary dict with counts

## API Exposure

### Public API

`src/ai_news_digest/api/v1/schemas/public.py`

New schema `PublicConflictResponse`:

```typescript
{
  id: string;
  conflict_type: string;
  confidence: number;
  explanation: string;
  same_source: boolean;
  claim_a_text: string;
  claim_b_text: string;
  source_a_name: string;
  source_b_name: string;
  created_at: string;
}
```

`src/ai_news_digest/api/v1/routes/public.py`

`StoryClusterResponse` now includes a `conflicts` field with recent conflicts for cluster articles.

### Frontend

`frontend/src/types.ts`

New `Conflict` interface:

```typescript
interface Conflict {
  id: string;
  conflict_type: string;
  confidence: number;
  explanation: string;
  same_source: boolean;
  claim_a_text: string;
  claim_b_text: string;
  source_a_name: string;
  source_b_name: string;
  created_at: string;
}
```

`frontend/src/pages/public/StoryClusterPage.tsx`

Renders a "Conflicting Reports" section with:

- List of conflicts with source names
- Confidence indicators
- Uncertainty messaging for low-confidence conflicts

## Configuration

New settings in `src/ai_news_digest/core/config.py`:

- `conflict_detection_enabled`: bool (default true)
- `conflict_detection_max_claims`: int (default 200)
- `conflict_detection_max_candidates`: int (default 10)
- `conflict_detection_max_comparisons`: int (default 200)
- `conflict_detection_max_llm_comparisons`: int (default 20)
- `conflict_detection_temporal_window_hours`: float (default 72.0)
- `conflict_detection_confidence_threshold`: float (default 0.5)

`AI_ENABLED=false` does NOT prevent deterministic detection. LLM analysis is the only feature gated by `AI_ENABLED`.

## Security

### Prompt Injection

LLM prompts include system instructions that cannot be overridden by claim text. The prompt explicitly states: "Respond with JSON only."

### Resource Exhaustion

All operations are bounded:

- Claims retrieved: bounded by `max_claims`
- Candidates generated: bounded by `max_candidates` and `max_total_candidates`
- Comparisons run: bounded by `max_comparisons`
- LLM calls: bounded by `max_llm_comparisons`
- Evidence excerpts: bounded to 200 characters (inherited from M81)

### SQL Safety

- Uses existing SQLAlchemy patterns
- Canonical pair ordering prevents duplicate key violations
- No unsafe SQL string construction

## Testing

### Unit Tests Added

- `tests/unit/domain/test_conflict_model.py` — Conflict domain model, canonical pair, confidence clamping
- `tests/unit/application/evaluation/test_conflict_candidates.py` — Candidate generation, overlap, temporal bounds
- `tests/unit/application/evaluation/test_conflict_detector.py` — Numeric, date, event-state detection
- `tests/unit/application/evaluation/test_conflict_confidence.py` — Confidence factor combinations
- `tests/unit/application/evaluation/test_conflict_explanation.py` — Explanation templates
- `tests/unit/application/use_cases/claim/test_detect_conflicts.py` — Use case orchestration and deduplication

### Test Results

- All M82 unit tests pass (47 tests)
- All M81 regression tests pass (20 tests)
- Mypy type checking passes cleanly
- Ruff linting passes cleanly

## Known Limitations

1. **No external verification**: M82 does NOT verify claims against the internet. Conflicts are detected only between claims from ingested articles.
2. **Deterministic detection is conservative**: False negatives are preferred over false positives.
3. **No timeline analysis**: M82 does not track how conflicts evolve over time (deferred to M83+).
4. **No story ranking changes**: Conflicts do not affect story cluster rankings (deferred to M84+).
5. **LLM is optional**: If AI is disabled, only deterministic conflicts are detected.

## Future Extensions

- Multi-claim conflict clusters (3+ sources contradicting)
- Conflict resolution and consensus tracking
- Integration with story clusters for cluster-level conflict summaries
- User-facing conflict reporting and feedback
- M83+: Timeline analysis and story evolution tracking
- M84+: Conflict-aware story ranking
