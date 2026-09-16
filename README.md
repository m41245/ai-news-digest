# AI News Intelligence Platform

A production-oriented AI-powered news intelligence platform built with **Python**, **FastAPI**, **Clean Architecture**, and modern engineering practices.

The platform collects articles from trusted RSS sources, extracts and validates content, performs structured AI analysis, clusters related stories, detects contradictions and trends, and delivers personalized intelligence briefs through a scalable architecture.

> **Project Status:** v1.0 — Feature Development Complete.

## What This Platform Does

This is an **AI News Intelligence Platform**, not merely an RSS + LLM summarizer. It provides:

### Trusted-Source Ingestion

- Curated source model with verification status (`VERIFIED`, `PENDING_REVIEW`, `REJECTED`, `INACTIVE`)
- Production digests only include articles from verified, active sources
- Per-source error isolation — a broken feed cannot crash the ingestion run
- SSRF protection with URL normalization, DNS validation, and per-hop redirect checks
- Article extraction with quality validation and RSS fallback

### Story Intelligence

- **Story clustering** — groups related articles into story clusters using deterministic signals
- **Story activity detection** — identifies breaking and developing stories
- **StoryEvent timelines** — chronological evolution of each story
- **Trend detection** — identifies emerging stories and topics
- **Story ranking** — multi-signal ranking (source trust, corroboration, recency, company relevance, etc.)
- **Top Story selection** — ranked best story across the platform
- **Intelligent digests** — AI-generated daily intelligence briefs with summaries, key takeaways, and source attribution
- **Story Intelligence Briefs** — deep-dive briefs for individual story clusters with evidence, conflicts, timeline, trends, and graph connections

### Evidence-Backed Intelligence

- **Claims extraction** — structured claims from article content
- **Evidence anchors** — links claims to specific article passages
- **Support status** — supported, partially supported, unsupported, unverified
- **Contradiction detection** — identifies conflicting claims across sources
- **Provenance tracking** — complete lineage for every intelligence output

### Graph & Temporal Intelligence

- **Knowledge graph** — entity relationships (companies, topics, categories, stories)
- **Temporal intelligence** — entity evolution over time
- **Bounded graph traversal** — related stories and entities with candidate limits
- **Story graph connections** — how stories relate to each other

### Search & Discovery

- Lexical, semantic, and hybrid search
- Related-story discovery
- Company and topic discovery
- Filtering by category, source, company, topic, date range, importance

### Personalization & Workspace

- User preferences (companies, topics, categories, sources)
- Mute behavior
- Followed stories and entities
- Recommendations
- Saved stories and personal collections
- Personalized intelligence workspace at `/me`

### Quality & Operations

- **Evaluation metrics** — platform-wide quality measurement
- **Drift detection** — identifies quality degradation over time
- **Quality gates** — PASS / WARN / FAIL / INSUFFICIENT_DATA for each component
- **Operational alerts** — automatic alerting on quality gate failures
- **Component health** — health snapshots with recovery tracking

### Production Architecture

- FastAPI backend with async SQLAlchemy + PostgreSQL
- Celery workers + Celery Beat for scheduled tasks
- Redis for caching, rate limiting, circuit breaker state, and quota tracking
- React/TypeScript/Vite frontend
- Docker multi-stage builds
- Render deployment (web, worker, beat)
- Cloudflare Pages frontend
- Neon PostgreSQL / Upstash Redis
- CI/CD with GitHub Actions (lint, typecheck, tests, security scans, Docker build, deployment)

See `docs/V1.0_RELEASE_READINESS.md` for the complete release assessment and `docs/PROJECT_STATUS.md` for milestone history.

---

## Getting Started

### Prerequisites

- Python 3.12+
- PostgreSQL 16+
- Redis 7+
- Node.js 20+ (for frontend)

### Backend Setup

```bash
cp .env.example .env
# Configure DATABASE_URL, REDIS_URL, JWT_SECRET_KEY in .env
poetry install
alembic upgrade head
uvicorn ai_news_digest.main:app --reload
```

### Frontend Setup

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

### Run Tests

```bash
# Backend unit + integration tests
poetry run pytest tests/unit tests/integration --ignore=tests/e2e

# Frontend
cd frontend && npm run lint && npm run typecheck && npm run build
```

## Documentation

- `docs/V1.0_RELEASE_READINESS.md` — v1.0 release readiness assessment
- `docs/FINAL_ENGINEERING_AUDIT.md` — Complete engineering audit report
- `docs/PROJECT_STATUS.md` — Milestone history and current status
- `docs/RUNBOOK.md` — Operational procedures
- `docs/DEPLOYMENT.md` — Deployment guide

## License

This project is licensed under the MIT License.