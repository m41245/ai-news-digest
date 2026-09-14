# Milestone 80 — AI Quality Benchmarking

## Status: COMPLETE

M80 adds a deterministic, provider-neutral quality benchmarking subsystem to the M77/M78/M79 AI routing stack. No real AI providers are activated. All work preserves the existing FastAPI + PostgreSQL + SQLAlchemy + Alembic + Redis + Celery architecture.

## What Changed

### Benchmark Domain Models

- **`application/ai/benchmark/models.py`** — Added core benchmark domain models:
  - `BenchmarkCase` — deterministic benchmark input with expected characteristics
  - `BenchmarkTask` — supported task types (summary, key_takeaways, why_it_matters, categories, companies, topics, structured_output_validity)
  - `QualityScore` — normalized 0-1 score with bounded clamping
  - `TaskScore` — aggregated per-task statistics
  - `OverallQualityScore` — weighted overall quality score
  - `BenchmarkResult` — single provider/model result
  - `BenchmarkFailureInfo` — failure classification
  - `BenchmarkRun` — complete benchmark run
  - `BenchmarkComparison` — provider/model comparison data
  - `BenchmarkDataset` — collection of benchmark cases
  - `FailureCategory` — benchmark failure classification

### Benchmark Dataset

- **`application/ai/benchmark/dataset.py`** — Added `load_dataset()` returning a deterministic `BenchmarkDataset` with 8 synthetic AI-news articles covering:
  - model/research release
  - funding/business announcement
  - product launch
  - policy/regulation story
  - infrastructure/chip story
  - open-source release
  - partnership/acquisition
  - safety/research story

  Each article generates 7 benchmark cases (one per task type). All content is original synthetic text. No copyrighted material is included.

### Deterministic Evaluator

- **`application/ai/benchmark/evaluator.py`** — Added `BenchmarkEvaluator` with task-specific deterministic evaluation:
  - **Structured Output Validity**: JSON parse + Pydantic schema validation
  - **Summary**: length bounds, reference overlap, input-copy ratio, repetition detection
  - **Key Takeaways**: count bounds, deduplication, reference coverage, summary overlap, item length
  - **Why It Matters**: non-empty check, length bounds, reference overlap, repetition detection
  - **Categories**: precision/recall/F1 using existing `normalize_category`
  - **Companies**: precision/recall/F1 using existing `normalize_company`
  - **Topics**: precision/recall/F1 using existing `normalize_topic`

### Benchmark Runner

- **`application/ai/benchmark/runner.py`** — Added `BenchmarkRunner` with:
  - `BenchmarkExecutionConfig` — bounded execution limits
  - Respects `AI_ENABLED` gate
  - Uses existing `ProviderManager` for provider selection and safety controls
  - Respects circuit breakers, quotas, and global budget
  - Latency measurement using `time.monotonic()`
  - Failure classification using existing error abstractions
  - Deterministic provider/model/case/task selection

### Benchmark Reports

- **`application/ai/benchmark/report.py`** — Added:
  - `BenchmarkReport` — machine-readable JSON report with provider stats, task scores, failure breakdown
  - `ComparisonReport` — deterministic provider/model comparison with quality, latency, and cost metrics

### Quality Thresholds

- **`application/ai/benchmark/thresholds.py`** — Added configurable `QualityThresholds` and `evaluate_thresholds()` for benchmark acceptance criteria only. Does not affect normal application operation.

### Benchmark Service Facade

- **`application/ai/benchmark/service.py`** — Added `BenchmarkService` facade.

### Tests

- **`tests/unit/application/ai/benchmark/`** — Added 72 unit tests covering:
  - BenchmarkCase creation and validation
  - Dataset loading, determinism, task filtering
  - Structured output validity (valid JSON, malformed JSON, missing fields, invalid enums)
  - Summary evaluation (good summary, empty, input copy penalty)
  - Key takeaways evaluation (good, empty, duplicates)
  - Why-it-matters evaluation (good, empty)
  - Category normalization and F1 scoring
  - Company normalization and F1 scoring
  - Topic normalization and F1 scoring
  - Repetition detection
  - BenchmarkExecutionConfig validation
  - AI_ENABLED=false behavior
  - Bounded execution
  - Report serialization
  - Comparison report generation
  - Threshold evaluation (passing, failing, no requests)

## Evaluation Metrics

### Structured Output Validity
Binary pass/fail against existing `StructuredIntelligence` Pydantic schema. Malformed JSON or missing required fields = 0.0. Valid schema = 1.0.

### Summary
- Base score: 1.0
- Penalties:
  - -0.3 for exceeding 2000 characters
  - -0.4 for low reference word overlap (<20%)
  - -0.1 for moderate reference overlap (20-50%)
  - -0.5 for high input-copy ratio (>80%)
  - -0.2 for repetition detection

### Key Takeaways
- Base score: 1.0
- Penalties:
  - -0.3 for fewer than 2 takeaways
  - -0.3 for more than 8 takeaways
  - -0.2 for duplicate detection
  - -0.4 for low reference coverage (<25%)
  - -0.15 for moderate reference coverage (25-60%)
  - -0.1 for oversized items (>300 chars)
  - -0.1 for repetitive items
  - -0.15 for excessive summary overlap (>85%)

### Why It Matters
- Base score: 1.0
- Penalties:
  - -0.3 for too short (<20 chars)
  - -0.2 for too long (>2000 chars)
  - -0.4 for low reference overlap (<15%)
  - -0.1 for moderate reference overlap (15-40%)
  - -0.2 for repetition detection

### Categories / Companies / Topics
- Precision/recall/F1 scoring using existing normalizers
- Exact normalized matches count as true positives
- Unknown values fall back to safe defaults (not errors)

## Provider/Model Comparison

The `ComparisonReport` produces per-provider/model metrics:
- overall_quality
- structured_validity
- summary_score
- takeaways_score
- why_it_matters_score
- category_f1
- company_f1
- topic_f1
- success_rate
- median_latency_ms
- total_input_tokens
- total_output_tokens
- estimated_cost
- cost_known
- cases_evaluated

## Cost/Latency Measurement

- Latency: measured with `time.monotonic()` at the runner level
- Token usage: reused from `AIResponse.usage` (M79)
- Cost estimation: reused from `AIResponse.estimated_cost` and `cost_known` (M79)
- Unknown cost is recorded as 0.0 with `cost_known=False`

## Safety Controls

- **AI_ENABLED=false** remains the default
- No automatic benchmark scheduling
- No automatic production spend
- Benchmark execution is explicitly bounded:
  - `max_providers` (default: 4)
  - `max_cases` (default: 10)
  - `max_tasks` (default: 7)
  - `max_total_requests` (default: 50)
  - `timeout_seconds` (default: 60)
- No quality-based routing changes
- No M81+ functionality

## Files Changed

### Production Code
- `src/ai_news_digest/application/ai/benchmark/__init__.py` (new)
- `src/ai_news_digest/application/ai/benchmark/models.py` (new)
- `src/ai_news_digest/application/ai/benchmark/dataset.py` (new)
- `src/ai_news_digest/application/ai/benchmark/evaluator.py` (new)
- `src/ai_news_digest/application/ai/benchmark/runner.py` (new)
- `src/ai_news_digest/application/ai/benchmark/report.py` (new)
- `src/ai_news_digest/application/ai/benchmark/thresholds.py` (new)
- `src/ai_news_digest/application/ai/benchmark/service.py` (new)

### Tests
- `tests/unit/application/ai/benchmark/__init__.py` (new)
- `tests/unit/application/ai/benchmark/test_models.py` (new)
- `tests/unit/application/ai/benchmark/test_dataset.py` (new)
- `tests/unit/application/ai/benchmark/test_evaluator.py` (new)
- `tests/unit/application/ai/benchmark/test_runner.py` (new)
- `tests/unit/application/ai/benchmark/test_report.py` (new)
- `tests/unit/application/ai/benchmark/test_thresholds.py` (new)

### Documentation
- `docs/MILESTONE_80_AI_QUALITY_BENCHMARKING.md` (new)

## Database Changes

None. M80 uses report artifacts (JSON) for persistence. No Alembic migration was added.

## Dependencies Added

None. M80 uses only existing project dependencies.

## Tests Added

72 new unit tests in `tests/unit/application/ai/benchmark/`.

## Exact Tests Executed/Results

```
tests/unit/application/ai/benchmark/ - 72 passed
tests/unit/application/ai/ - 346 passed, 8 failed (pre-existing quota config failures unrelated to M80)
```

## Ruff Result

```
All checks passed!
```

## MyPy Result

```
Success: no issues found in 8 source files
```

## Security Verification

- No secrets committed
- No API keys in code or tests
- Benchmark inputs treated as untrusted (parsed through existing Pydantic validators)
- No prompt injection vectors in benchmark data
- Bounded concurrency and request limits
- No filesystem path traversal
- No unsafe serialization

## Known Limitations

1. Summary quality relies on deterministic heuristics (length, overlap, input-copy ratio) without semantic similarity scoring
2. No LLM-as-judge for semantic evaluation (explicitly avoided per M80 scope)
3. Benchmark results are not persisted to database (JSON artifacts only)
4. No real-provider execution in tests (all mocked)
5. 8 pre-existing quota config test failures remain (unrelated to M80)

## Real-Provider Execution

Not performed. No real AI provider credentials are available in this environment.

## AI_ENABLED Status

`AI_ENABLED=false` remains the default.

## M81+ Functionality

None implemented.

## Recommended Next Milestone

M81 — Evidence-backed intelligence and claim/evidence graphs.
