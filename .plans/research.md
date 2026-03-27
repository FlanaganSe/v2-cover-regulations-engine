# Research: MVP Milestone Planning

Date: 2026-03-26
Scope: Ground the MVP implementation plan in the current repo, documented research, and only the minimum external verification needed for unstable dependencies.

## Inputs Reviewed

- `docs/requirements.md`
- `docs/DATA_SOURCES.md`
- `docs/CONSOLIDATED_RESEARCH.md`
- `docs/decisions.md`
- `.claude/rules/conventions.md`
- `.claude/rules/stack.md`
- `.claude/rules/immutable.md`
- `CLAUDE.md`

## Current Repository State

- The repository is still effectively greenfield.
- There is no application source tree yet for backend, frontend, infrastructure, or ingestion code.
- There are no tests, CI workflows, schema migrations, deployment definitions, or seed scripts yet.
- The useful project assets today are requirements, research, and a small set of stack conventions.

Implication:
- The plan must be framed as an initial build plan, not an incremental refactor.
- Milestones should create the project skeleton, contracts, and operational guardrails before feature implementation.

## Problem Framing

The MVP is a demo product that answers: "what can be confidently built on this LA City residential parcel?" The system needs to:

- resolve a parcel by address or APN
- determine supported zoning facts and development standards deterministically
- flag overlays and unsupported ambiguity clearly
- optionally use an LLM to explain, not decide
- present the result clearly in a map-first UI
- remain simple enough to implement safely as an MVP

The strongest theme across the docs is risk reduction through a narrow scope:

- LA City only
- residential only
- Original Code / Chapter 1 only
- overlay rules are flag-and-cite, not deeply modeled
- deterministic rules engine first, LLM second

## Code Path Tracing

Not applicable yet because no runtime code exists.

The intended runtime path is well-defined in `docs/CONSOLIDATED_RESEARCH.md`:

1. User searches by APN or address.
2. Backend resolves parcel from seeded parcel data.
3. Backend confirms parcel is inside LA City.
4. Backend runs spatial joins for zoning and overlay context.
5. Backend parses zone strings and applies curated rules.
6. Backend computes confidence deterministically.
7. LLM optionally produces explanation with constrained output and citations.
8. Frontend renders map, parcel facts, standards, warnings, and explanation.

The intended ingestion path is also well-defined:

1. Pull ArcGIS REST pages.
2. Normalize geometry to EPSG:4326.
3. Load to PostGIS with provenance.
4. Index and validate.
5. Run sample parcel QA against ZIMAS/manual references.

## Dependency Mapping

### Product Dependencies

- Backend: Python 3.12+, FastAPI, SQLAlchemy 2.x, GeoAlchemy2, psycopg 3, Shapely 2.x, aiohttp, tenacity, mypy, Ruff, pytest
- Frontend: TypeScript 5.x, React + Vite, Tailwind CSS, MapLibre GL JS, react-map-gl/maplibre, Vitest, ESLint, Prettier
- Database: PostgreSQL + PostGIS + `pg_trgm`
- Tile serving: Martin
- Infrastructure target from repo rules: AWS deployment
- Local dev baseline: Docker Compose

### External Runtime Dependencies

- OpenAI API for explanation generation
- Martin tile service for parcel/zoning/building map layers
- AWS infra services once deployed

### External Ingestion Dependencies

- LA County parcel layer
- NavigateLA zoning layer
- City boundaries layer
- Specific plans layer
- HPOZ layer
- Community plan areas layer
- General plan land use layer
- LARIAC buildings layer
- CAMS geocoder fallback
- Curated local rule pack derived from zoning summary, ZA Memo 143, and selective code manual references

## Pattern Catalog

Patterns already supported by the research and worth preserving in the plan:

- Deterministic engine first, LLM explanation second
- Narrow combined API response for the parcel details screen
- Flat PostGIS tables with provenance instead of multi-stage warehouse schemas
- Dedicated ingestion scripts/CLI isolated from app runtime code
- Configurable model ID instead of hard-coded dated model slug
- Graceful unsupported states instead of speculative inference
- Data-source citations and "data as of" surfaced in API and UI
- Split-zoned parcel handling by largest polygon overlap, not centroid heuristics

Patterns explicitly rejected by the docs and therefore should stay out of the MVP plan:

- full code parsing of LAMC
- RAG/vector-search architecture
- nationwide abstraction layers
- separate ingestion platform/service
- over-modeled raw/stage/core/publish schemas
- LLM-driven decision making

## Test Landscape

There is no existing test suite.

The research docs imply four required testing layers:

- unit tests for zone parsing, rule lookup, confidence logic, and API serializers
- integration tests for parcel lookup and spatial join queries against seeded fixtures
- ingestion verification scripts for row counts, CRS validity, geometry validity, and sample joins
- end-to-end smoke tests for search -> parcel detail -> UI render -> deploy health

The planned test parcel categories are already documented:

- clean R1 parcel
- RE/RS parcel
- RD/R3 parcel
- HPOZ parcel
- specific plan parcel
- Downtown / Chapter 1A parcel
- split-zoned parcel
- outside-LA-City parcel

## Data and State Impacts

The plan should explicitly isolate ingestion from the application:

- app runtime depends on already-seeded PostGIS tables
- ingestion should live in a dedicated directory and be runnable independently
- provenance should be stored in `ingest_metadata`
- checkpoints should allow resume for large layer downloads
- seed output should be reproducible enough for demo resets and redeploys

State that must be represented in the schema/API:

- parcel identity and geometry
- zoning string and parsed zoning facts
- overlay hits and source links
- rules-derived standards
- confidence level and deterministic reasons
- LLM summary, citations, and availability flag
- data freshness/provenance metadata

## Config and Environment Considerations

Required configuration areas:

- database URLs for backend and Martin
- OpenAI API key and model configuration
- AWS environment config and CDK bootstrap state
- frontend API/tile service URLs
- CORS origins
- ingestion checkpoint location and optional raw cache path

Manual and operational setup likely required:

- AWS account bootstrap and IAM setup
- GitHub Actions OIDC or deploy credentials
- OpenAI project/API key creation
- initial demo seed run
- manual curation of the rule pack from source documents
- identification and QA of demo/test parcels

## Risk Inventory

### High-value risks already visible

1. Deployment target conflict
- `docs/decisions.md` and `CLAUDE.md` say AWS deployment.
- `.claude/rules/stack.md` says PoC deploy is Railway + Vercel and AWS is future production.
- Planning should treat AWS as the required target while preserving portability because the repo-level ADR is stronger than an older research posture.

2. GIS data anomalies and drift
- ArcGIS layers can include null AINs, invalid geometries, 3D/4D coordinates, schema quirks, and endpoint instability.
- Mitigation: ingestion validation, provenance, checkpoints, raw caching where practical, and unsupported-state handling.

3. Rule-pack accuracy
- The curated rule pack is essential and partly manual.
- Mitigation: narrow zone coverage, explicit citations, deterministic calculations, and test parcels that exercise each supported class.

4. LLM misuse
- If the LLM becomes the decision-maker, the product becomes brittle and hard to trust.
- Mitigation: deterministic confidence/rules, schema-constrained outputs, citation whitelist, and deterministic fallback response when LLM fails.

5. Spatial edge cases
- split-zoned parcels, Chapter 1A, hillside/RFA branching, and street-centerline geocoder results can all produce misleading results if simplified too aggressively.
- Mitigation: largest-overlap joins, explicit unsupported handling, optional hillside stretch scope, and text search before geocoder fallback.

6. Unknown-unknowns in data coverage
- Even with strong research, some parcel categories will not fit supported patterns.
- Mitigation: add verification and unsupported-state criteria as first-class milestone deliverables, not polish.

## External Verification

Because model availability is time-sensitive, I verified only the OpenAI portion externally using official OpenAI docs on 2026-03-26.

Findings:

- The OpenAI docs continue to recommend the `Responses API` for GPT-5 series usage.
- Official docs and changelog confirm GPT-5 family mini models are available on the API, but exact dated model slugs are time-sensitive.
- Best planning posture is to keep the model name configurable and verify the exact model slug at implementation time rather than bake it into the architecture.

Sources:

- https://developers.openai.com/cookbook/examples/gpt-5/gpt-5_new_params_and_tools/
- https://developers.openai.com/api/docs/changelog

Inference from those sources:

- The architecture decision to use Responses API is stable.
- The exact GPT-5 mini variant should remain a config detail, not a hard dependency in the plan.

## Planning Implications

The lowest-risk MVP plan should:

- start with repository scaffolding, contracts, and local/dev infrastructure
- make ingestion a separate milestone with its own verification gate
- implement deterministic backend behavior before the frontend depends on it
- add the LLM only after deterministic outputs and citations exist
- target AWS deployment in the final milestone because that matches the repo ADR, while keeping the app portable
- include explicit manual setup tasks for rule-pack curation, secrets, seed execution, CI/CD setup, and demo parcel QA

## Recommended Planning Assumptions

Use these assumptions unless the user changes scope:

- AWS is the MVP deployment target.
- Railway/Vercel remain a fallback reference, not the default plan.
- Only the documented LA City residential scope is supported.
- Hillside and fire overlays remain optional stretch work unless early QA proves they are required for the demo.
- Ingestion code lives separately from backend runtime code to preserve separation of concerns.
- One combined parcel detail endpoint serves the frontend.
