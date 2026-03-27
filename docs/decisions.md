# Architecture Decision Records

## ADR-001: Python + TypeScript Split Architecture
**Date:** 2026-03-22
**Status:** accepted
**Context:** Project requires a regulation/zoning rules engine (computation-heavy, data-pipeline-friendly) alongside a user-facing interface.
**Decision:** Python backend (FastAPI) for regulation logic and data processing; TypeScript frontend (React + Vite) for the UI layer.
**Consequences:** Two separate runtimes to maintain; API contract defined via Pydantic models (backend) mirrored as TypeScript interfaces (frontend).

## ADR-002: Bulk PostGIS Seed + Spatial Joins (Not Live API Queries)
**Date:** 2026-03-26
**Status:** accepted
**Context:** GIS data (parcels, zoning, overlays) is needed at query time. Options: call ArcGIS APIs at runtime, or seed everything into PostGIS and query locally.
**Decision:** Seed all 8 GIS layers into PostGIS via a batch ingestion pipeline. Spatial joins at query time via LATERAL subqueries.
**Consequences:** Sub-100ms lookups with no runtime dependency on external GIS APIs. Martin auto-serves vector tiles from the same database. Tradeoff: data freshness depends on re-running ingestion.

## ADR-003: Deterministic Rules Engine + LLM Explanation Layer
**Date:** 2026-03-27
**Status:** accepted
**Context:** Zoning assessments need to be reliable. LLMs hallucinate numbers and citations.
**Decision:** Deterministic pipeline computes all facts (standards, confidence, ADU). LLM explains those facts in plain English with grounded citations. LLM does not decide confidence, calculate FAR, or invent numbers.
**Consequences:** Assessments are reproducible. LLM failure degrades gracefully to a template-based fallback. Citation whitelist prevents hallucinated references.

## ADR-004: Railway for All Services (Not AWS + Vercel)
**Date:** 2026-03-27
**Status:** accepted
**Context:** Need to deploy PostGIS, Martin, FastAPI backend, and static frontend for a demo. Original plan was Railway (backend) + Vercel (frontend).
**Decision:** Deploy all 4 services on Railway. Frontend served via nginx in a Docker container. No Vercel needed.
**Consequences:** Single platform, single bill. Frontend is a static SPA served by nginx — no SSR, no edge functions needed. For production, AWS migration path is straightforward (see future enhancements).

## ADR-005: Curated Rule Pack (Not LAMC Parsing)
**Date:** 2026-03-26
**Status:** accepted
**Context:** LA zoning code is complex. Options: parse the full LAMC, or hand-curate a rule table for the ~15 most common residential zones.
**Decision:** Curated rule pack covering ~95% of residential parcels. Unsupported zones return "review manually" with Low confidence.
**Consequences:** Fast to build, easy to verify. Covers the demo use case. Adding zones requires manual curation, not code changes. The Zoning Summary PDF is the source of truth for the rule pack.

---

## Future Enhancements

- **Chapter 1A (Downtown) support** — Currently returns "not yet supported." Different development standards structure.
- **Hillside/fire overlays** — Additional overlay layers that affect buildability in hillside areas.
- **AWS migration** — Railway → AWS path: ECS/Fargate for FastAPI + Martin, RDS PostgreSQL + PostGIS, CloudFront + S3 for frontend. Application code stays the same.
- **Protomaps base map** — Current PMTiles build URL is stale. Use Protomaps API with a free key for a stable base map.
- **GitHub auto-deploy** — Railway native GitHub integration, no Actions needed. See `docs/github-actions-deployment-research.md`.
- **Chat interface** — Conversational AI layer on top of the assessment (bonus, not MVP).
