# Product Overview

## What this is

A zoning regulation lookup tool for Los Angeles residential parcels. A user searches for a property by address or APN, and the system returns a comprehensive assessment: what zone the parcel is in, what can be built there (height, FAR, setbacks, density, ADU eligibility), what overlays apply, and a confidence score indicating how reliable the answer is. An LLM generates a natural-language summary, but every number comes from a deterministic rules engine — the LLM explains facts, it doesn't decide them.

The target audience is homeowners, developers, and planners who need quick zoning answers without reading the LAMC. The system covers ~15 residential zone classes representing ~95% of LA City residential parcels.

## Stack

- **Backend:** Python 3.12, FastAPI, async SQLAlchemy + GeoAlchemy2, Pydantic 2
- **Frontend:** TypeScript 5.9, React 19, Vite 8, Tailwind CSS 4
- **Map:** MapLibre GL JS + react-map-gl, Protomaps PMTiles base, Martin vector tile server
- **Database:** PostgreSQL 17 + PostGIS (spatial queries)
- **LLM:** OpenAI (gpt-5.4-mini via `OPENAI_MODEL` env var), structured output with deterministic fallback
- **Package managers:** uv (backend), pnpm (frontend)
- **Linting/formatting:** Ruff (backend), ESLint + Prettier (frontend)
- **Testing:** pytest + pytest-asyncio (backend), Vitest + Testing Library (frontend, infra ready but no tests yet)
- **Deployment:** Railway Hobby (all services), AWS deferred to post-MVP

## Architecture

```
User → Frontend (React SPA) → Backend API (FastAPI) → PostgreSQL + PostGIS
                                    ↓
                              Rules Engine (pure functions)
                                    ↓
                              LLM Service (OpenAI, optional)

Map tiles: Frontend → Martin tile server → PostGIS (zoning, parcels, buildings)
Base map:  Frontend → Protomaps PMTiles CDN
```

**Request flow for parcel detail:**

1. User searches by address or APN → frontend calls `GET /api/parcels/search`
2. Backend runs ILIKE address search or exact AIN match with a lateral join to get dominant zone
3. User selects a result → frontend calls `GET /api/parcels/{ain}`
4. Backend executes a large spatial join query: fetches parcel facts, dominant zoning, specific plan, HPOZ, community plan, general plan land use, LA City boundary check — all via PostGIS `ST_Intersects` with lateral joins ordered by intersection area
5. Rules engine (pure functions, no I/O) parses the zone string, looks up the hardcoded rule, computes effective FAR, ADU eligibility, and confidence level
6. LLM service builds a grounded prompt from all deterministic facts, calls OpenAI with structured output, filters citations to a whitelist. On any failure → deterministic fallback assessment
7. Response assembled as `ParcelDetail` with 9 nested sections, returned to frontend
8. Frontend renders the assessment panel (facts, zoning, standards, overlays, ADU, confidence badge, summary, citations, caveats)

**Key architectural decision:** All spatial data is bulk-seeded from LA County/City ArcGIS endpoints into PostGIS. Lookups are sub-100ms spatial joins, not live API calls. Data freshness comes from periodic re-ingestion.

## Directory structure

```
├── backend/                 # FastAPI application
│   ├── app/
│   │   ├── main.py          # App factory, health endpoint, CORS, router registration
│   │   ├── config.py        # Pydantic BaseSettings (DATABASE_URL, OPENAI_API_KEY, etc.)
│   │   ├── database.py      # Async SQLAlchemy engine + session dependency
│   │   ├── routers/         # FastAPI route handlers (parcels, home)
│   │   ├── models/          # SQLAlchemy ORM models (Parcel with PostGIS geometry)
│   │   ├── schemas/         # Pydantic response models (ParcelDetail, HomeMetadata)
│   │   ├── services/        # Business logic (parcel_service, rules_engine, llm_service, home_service)
│   │   └── data/            # Hardcoded zone rules (zone_rules.py)
│   └── tests/               # pytest tests (rules engine, LLM service)
├── frontend/                # React SPA
│   └── src/
│       ├── components/      # App, Map, SearchBar, AssessmentPanel, HomePanel, ConfidenceBadge
│       ├── hooks/           # useParcelSearch (debounced search with abort)
│       ├── lib/             # api.ts (fetch client), mapStyle.ts (MapLibre style builder)
│       └── types/           # TypeScript interfaces mirroring backend schemas
├── ingestion/               # Standalone data pipeline
│   ├── config.py            # ArcGIS endpoint URLs, demo bboxes
│   ├── create_tables.py     # DDL + spatial index creation
│   ├── ingest.py            # Resumable ArcGIS pagination with checkpointing
│   ├── verify_data.py       # Row count + geometry validation
│   ├── arcgis_client.py     # HTTP client with retry (tenacity)
│   └── geometry.py          # Shapely normalization to EPSG:4326
├── docs/                    # ADRs, data source spec, deployment research
├── .plans/                  # Implementation plans and research notes
└── docker-compose.yml       # Local dev: db (PostGIS), martin, backend
```

## Core concepts

**Parcel** — A real property identified by AIN (Assessor Identification Number). Has geometry (MultiPolygon), address, property facts (year built, sqft, bedrooms), and valuation. The central entity everything revolves around.

**Zone string** — The raw `ZONE_CMPLT` value from LA City zoning data (e.g., `(T)(Q)RD1.5-1D-CDO-RIO`). A compressed encoding of zone class, height district, prefix flags, D limitation, and overlay suffixes. The rules engine regex-parses this into structured components.

**Zone class** — The base zoning designation (R1, RD1.5, R3, etc.). Maps to a `ZoneRule` containing development standards: height, stories, FAR/RFA, setbacks, density, allowed uses, LAMC section.

**Height district** — A modifier (1, 1L, 1VL, 1XL, 2, 3, 4) that overrides FAR for FAR-type zones. RFA zones ignore it.

**FAR vs RFA** — Two density control mechanisms. FAR (Floor Area Ratio) applies to multifamily zones and is modified by height district. RFA (Residential Floor Area) applies to single-family zones and is fixed per zone class regardless of height district.

**Overlays** — Specific Plans, HPOZs, community plans, and general plan land use designations that layer additional rules on top of base zoning. Detected via spatial intersection and reduce confidence.

**Confidence** — A deterministic assessment (High/Medium/Low) of how reliable the zoning analysis is. Computed from zone support status, overlay presence, flag count, and Chapter 1A status. Not an LLM judgment.

**Chapter 1A** — Downtown LA's alternative zoning framework. Detected by bracket-format zone strings or Central City/Central City North community plans. Explicitly unsupported — confidence drops to Low.

**Assessment** — The LLM-generated (or fallback) summary combining all deterministic facts into readable text with filtered citations and legal caveats.

## Key patterns and conventions

**Deterministic-first architecture.** Every factual claim (height, FAR, setbacks, density) comes from the hardcoded rules engine. The LLM receives all facts as grounding context and generates explanatory text. If the LLM fails, a template-based fallback produces the same facts without natural language polish.

**Pure function rules engine.** `rules_engine.py` has zero I/O — all functions are pure, taking parsed data and returning structured results. This makes it trivially testable and the most thoroughly tested part of the codebase.

**Spatial join pattern.** All geographic lookups use `LEFT JOIN LATERAL ... ST_Intersects ... ORDER BY ST_Area(ST_Intersection) DESC LIMIT 1` to find the dominant overlay by intersection area. This handles parcels that span multiple zones/overlays.

**Graceful LLM degradation.** Missing API key, API errors, model refusal, hallucinated citations — all produce a deterministic fallback with `llm_available: false`. The system never fails because the LLM is unavailable.

**Citation whitelist.** LLM citations are filtered to known-safe patterns (LAMC sections, source URLs, planning.lacity.gov). Hallucinated URLs are stripped.

**Request deduplication.** Frontend uses a request ID ref + AbortController pattern to prevent stale responses from overwriting current results during rapid searches.

**No routing library.** Frontend uses simple state-based view switching (`"home" | "loading" | "error" | "assessment"`) rather than a router — appropriate for a single-concern tool.

**Domain terminology.** Code uses "regulation", "zone", "parcel", "permit" — never generic names. Enums or const maps for zone types and regulation codes.

## Data layer

**PostgreSQL 17 + PostGIS.** All spatial data bulk-seeded from LA County/City ArcGIS REST endpoints.

**Tables** (created by `ingestion/create_tables.py`):

| Table | Purpose | Key columns |
|-------|---------|-------------|
| `parcels` | Property records | ain, apn, address, geom (MultiPolygon 4326), property facts |
| `zoning` | LA City zone polygons | zone_class, zone_cmplt, geom |
| `specific_plans` | Specific plan boundaries | name, url, geom |
| `hpoz` | Historic preservation zones | name, geom |
| `community_plan_areas` | Community plan boundaries | name, geom |
| `general_plan_lu` | General plan land use | designation, geom |
| `city_boundaries` | LA City municipal boundary | name, geom |
| `buildings` | Building footprints (demo areas only) | geom |
| `ingest_metadata` | Data freshness tracking | source, ingested_at, source_url |

**Spatial indexes** on all geometry columns. Demo building footprints limited to Silver Lake, Venice, and Eagle Rock neighborhoods.

**No ORM migrations.** Tables are created by the ingestion script's DDL. Schema changes require re-running `create_tables.py` and `ingest.py`.

**Martin** serves vector tiles directly from PostGIS tables (zoning, parcels, buildings) — no pre-generated tile cache.

## API surface

All endpoints are unauthenticated. No rate limiting.

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Returns `{"status": "ok"\|"degraded", "db": bool}` |
| `/api/home` | GET | Homepage metadata: supported zones, data sources, featured parcels |
| `/api/parcels/search?q=` | GET | Search parcels by address (ILIKE) or APN/AIN (exact match). Returns up to 10 results. |
| `/api/parcels/{ain}` | GET | Full parcel detail: facts, scope, zoning, overlays, standards, ADU, confidence, assessment, metadata. Returns 404 if not found. |

**Response shape for `/api/parcels/{ain}`** — `ParcelDetail` with 9 nested sections:
- `parcel` — ParcelFacts (address, coordinates, lot sqft, year built, use, bedrooms)
- `scope` — Jurisdiction flags (in_la_city, supported_zone, chapter_1a)
- `zoning` — Zone string, class, height district, Q/T/D flags, suffixes
- `overlays` — Specific plan, HPOZ, community plan, general plan LU (each with optional URL)
- `standards` — Height, stories, FAR/RFA, setbacks, density, allowed uses
- `adu` — Allowed, max sqft, setbacks, notes
- `confidence` — Level + reasons list
- `assessment` — Summary, citations, caveats, llm_available flag
- `metadata` — data_as_of timestamp, source URLs

## Environment and config

**Backend** (Pydantic BaseSettings, all optional with defaults):

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | `postgresql+psycopg://postgres:postgres@db/regulation_engine` | SQLAlchemy async connection |
| `OPENAI_API_KEY` | `""` (empty = fallback mode) | OpenAI API credentials |
| `OPENAI_MODEL` | `gpt-4.1-mini` | LLM model slug |
| `MARTIN_URL` | `http://martin:3000` | Martin tile server (used by backend, not currently queried) |

**Frontend** (Vite build-time):

| Variable | Default | Purpose |
|----------|---------|---------|
| `VITE_API_URL` | `http://localhost:8000` | Backend API base URL |
| `VITE_MARTIN_URL` | `http://localhost:3001` | Martin tile server for map layers |

**Local dev:** `docker-compose up` starts db (PostGIS on 54320), martin (on 3001), and backend (on 8000). Frontend runs separately via `pnpm dev`.

## Testing

**Backend** — pytest with `asyncio_mode = "auto"`:
- `test_rules_engine.py` — 39 tests covering zone string parsing (20), rule lookup (5), height district FAR (5), effective FAR (3), confidence (9), ADU (3). All pure functions, no mocking needed.
- `test_llm_service.py` — 18 tests covering fallback assessment (9), prompt construction (8), API integration with mocks (18 total including whitelist filtering, refusal handling, error fallback).
- `conftest.py` — Minimal stub.
- Run: `cd backend && pytest`

**Frontend** — Vitest + Testing Library infrastructure is configured but no component tests exist yet.
- Run: `cd frontend && pnpm test`

**Ingestion** — No automated tests. Verification via `verify_data.py` (row counts, geometry checks).

## Important decisions and tradeoffs

**Bulk seed over live API queries (ADR-002).** All spatial data is pre-loaded into PostGIS rather than queried from LA County/City ArcGIS endpoints at request time. This gives sub-100ms lookups and eliminates external API dependency at runtime, but means data can be stale between re-ingestions. The tradeoff is acceptable because zoning data changes infrequently.

**Deterministic rules + LLM explanation (ADR-003).** The LLM never decides what the zoning facts are — it only summarizes them. This means the system produces correct answers even when the LLM is unavailable, hallucinates, or is replaced with a different model. The cost is that the LLM summary can't add information the rules engine doesn't already have.

**Curated rule pack over full LAMC encoding (ADR-005).** Only ~15 residential zone classes are hardcoded, covering ~95% of LA City residential parcels. Commercial, industrial, and Chapter 1A zones are explicitly unsupported (confidence drops to Low). This was chosen because encoding the full LAMC is a multi-month effort and 95% coverage is sufficient for MVP.

**Railway for everything (ADR-004).** Backend, frontend, Martin, and PostGIS all deploy on Railway rather than splitting across AWS + Vercel. This simplifies operations for a PoC. AWS migration path is documented for future production deployment.

**No authentication.** The API is fully open — appropriate for a demo/PoC but will need auth before production.

**FAR vs RFA split.** Single-family zones (R1, RE*, RS, RA) use RFA which ignores height district. Multifamily zones (RD*, R3, R4, R5) use FAR which is overridden by height district. This reflects how the LAMC actually works but is a common source of confusion — the `far_type` field in the response makes the distinction explicit.

## Gotchas

**Zone string parsing is regex-heavy.** The `parse_zone_string` function handles a surprising number of edge cases (parenthesized flags, bracket-format Chapter 1A zones, dash-separated suffixes, D limitation detection). If you modify the regex, run the full test suite — there are 20 parsing tests for a reason.

**Chapter 1A detection has two paths.** A zone is Chapter 1A if (a) the zone string uses bracket format like `[MB3-SH1-1]` OR (b) the community plan is "Central City" or "Central City North". Both must be checked because the data isn't always consistent.

**R1 variation zones (R1V1, R1V2, R1R3, R1H) fall back to base R1 rules.** The rule lookup strips suffixes after "R1" if the full variation isn't in the rule set. This is intentional — the variations don't change development standards enough to warrant separate entries.

**CORS is wide open.** `allow_origins=["*"]` — fine for PoC, must be locked down for production.

**Building footprints are demo-only.** The `buildings` table only has data for Silver Lake, Venice, and Eagle Rock (demo bboxes in ingestion config). Other neighborhoods show parcel and zoning layers but no building outlines.

**No database migrations.** Schema changes require re-running `create_tables.py` which drops and recreates tables. This means re-ingesting all data afterward. Fine for early development, will need proper migrations eventually.

**Frontend has no tests.** Vitest infrastructure is wired up but zero component tests exist. The test setup file (`src/test/setup.ts`) is referenced in config but present.

**LLM model env var.** The config default is `gpt-4.1-mini` but the confirmed production model is `gpt-5.4-mini-2026-03-17`, set via `OPENAI_MODEL` environment variable on Railway. Don't rely on the code default.

**Martin tile URLs differ between local and deployed.** Locally Martin is on port 3001 (mapped from container's 3000). On Railway it gets a public URL. The frontend's `VITE_MARTIN_URL` must match the deployment context.
