# Product Overview

## What This Is

A zoning regulation lookup tool for Los Angeles residential parcels. A user searches by address or APN, and the system returns a comprehensive assessment: zone class, development standards (height, FAR, setbacks, density), ADU eligibility, overlay warnings, and a confidence score. An LLM generates a plain-language summary, but every number comes from a deterministic rules engine.

The target audience is homeowners, developers, and planners who need quick zoning answers without reading the LAMC. Covers ~15 residential zone classes representing ~95% of LA City residential parcels.

## Request Flow

**Two-phase loading** splits parcel lookup into a fast deterministic phase and a slow LLM phase:

1. User searches by address or APN → `GET /api/parcels/search`
2. Backend runs ILIKE address search or exact AIN match with a lateral join to get dominant zone
3. User selects a result → frontend initiates two phases:
   - **Phase 1 (~200ms):** `GET /api/parcels/{ain}/facts` — spatial joins fetch parcel facts, zoning, overlays. Rules engine computes standards, FAR, ADU, confidence. Returns `ParcelDetail` immediately.
   - **Phase 2 (2-5s, non-critical):** `GET /api/parcels/{ain}/assessment` — LLM builds grounded prompt from deterministic facts, calls OpenAI with structured output, filters citations. On failure → deterministic fallback remains.
4. Frontend renders assessment panel (facts, zoning, standards, overlays, ADU, confidence, summary, citations)

## Directory Structure

```
├── backend/                 # FastAPI application
│   ├── app/
│   │   ├── main.py          # App factory, health, CORS, router registration
│   │   ├── config.py        # Pydantic BaseSettings
│   │   ├── database.py      # Async SQLAlchemy engine + session
│   │   ├── routers/         # Route handlers (parcels, home)
│   │   ├── models/          # SQLAlchemy ORM models
│   │   ├── schemas/         # Pydantic response models
│   │   ├── services/        # Business logic (parcel, rules, llm, home)
│   │   └── data/            # Hardcoded zone rules
│   └── tests/
├── frontend/                # React SPA
│   └── src/
│       ├── components/      # AssessmentPanel, HomePanel, Map, SearchBar
│       ├── hooks/           # useParcelSearch (debounced, AbortController)
│       ├── lib/             # api.ts, mapStyle.ts, recentSearches.ts
│       └── types/           # TypeScript interfaces mirroring backend schemas
├── ingestion/               # Standalone data pipeline
│   ├── config.py            # ArcGIS endpoint URLs, demo bboxes
│   ├── create_tables.py     # DDL + spatial index creation
│   ├── ingest.py            # Resumable ArcGIS pagination with checkpointing
│   ├── verify_data.py       # Row count + geometry validation
│   ├── arcgis_client.py     # HTTP client with retry (tenacity)
│   └── geometry.py          # Shapely normalization to EPSG:4326
├── martin/                  # Vector tile server (Dockerfile only)
├── docs/                    # ADRs, data source spec, deployment guide
├── architecture/            # D2 diagram source + rendered PNG
└── docker-compose.yml       # Local dev: db, martin, backend
```

## Core Concepts

**Parcel** — A real property identified by AIN (Assessor Identification Number). Has geometry, address, property facts, and valuation. The central entity.

**Zone string** — The raw `ZONE_CMPLT` value from LA City zoning data (e.g., `(T)(Q)RD1.5-1D-CDO-RIO`). Encodes zone class, height district, prefix flags, D limitation, and overlay suffixes. The rules engine regex-parses this into structured components.

**Zone class** — The base zoning designation (R1, RD1.5, R3, etc.). Maps to a `ZoneRule` with development standards: height, stories, FAR/RFA, setbacks, density, allowed uses.

**Height district** — A modifier (1, 1L, 1VL, 1XL, 2, 3, 4) that overrides FAR for FAR-type zones. RFA zones ignore it.

**FAR vs RFA** — Two density control mechanisms. FAR (Floor Area Ratio) applies to multifamily zones and is modified by height district. RFA (Residential Floor Area) applies to single-family zones and is fixed per zone class.

**Overlays** — Specific Plans, HPOZs, community plans, and general plan land use designations. Detected via spatial intersection and reduce confidence.

**Confidence** — A deterministic assessment (High/Medium/Low) computed from zone support status, overlay presence, flag count, and Chapter 1A status.

**Chapter 1A** — Downtown LA's alternative zoning framework. Detected by bracket-format zone strings or Central City community plans. Unsupported — confidence drops to Low.

## Key Patterns

**Deterministic-first.** Every factual claim comes from the hardcoded rules engine. The LLM receives all facts as grounding context and generates explanatory text. If the LLM fails, a template-based fallback produces the same facts.

**Pure function rules engine.** `rules_engine.py` has zero I/O — all functions are pure, taking parsed data and returning structured results.

**Spatial join pattern.** All geographic lookups use `LEFT JOIN LATERAL ... ST_Intersects ... ORDER BY ST_Area(ST_Intersection) DESC LIMIT 1` to find the dominant overlay by intersection area.

**Graceful LLM degradation.** Missing API key, API errors, model refusal, hallucinated citations — all produce a deterministic fallback with `llm_available: false`.

**Citation whitelist.** LLM citations are filtered to known-safe patterns (LAMC sections, planning.lacity.gov). Hallucinated URLs are stripped.

**Request deduplication.** Frontend uses a request ID ref + AbortController to prevent stale responses during rapid searches.

## Data Layer

PostgreSQL 17 + PostGIS. All spatial data bulk-seeded from LA County/City ArcGIS REST endpoints.

| Table | Purpose |
|-------|---------|
| `parcels` | Property records (ain, address, geom, property facts) |
| `zoning` | LA City zone polygons (zone_class, zone_cmplt, geom) |
| `specific_plans` | Specific plan boundaries (name, url, geom) |
| `hpoz` | Historic preservation zones (name, geom) |
| `community_plan_areas` | Community plan boundaries (name, geom) |
| `general_plan_lu` | General plan land use (designation, geom) |
| `city_boundaries` | LA City municipal boundary (name, geom) |
| `buildings` | Building footprints — demo areas only (geom) |
| `ingest_metadata` | Data freshness tracking (source, ingested_at) |

Spatial indexes on all geometry columns. Martin serves vector tiles directly from PostGIS — no pre-generated tile cache. See [Data Sources](DATA_SOURCES.md) for full endpoint details.

## API

All endpoints are unauthenticated.

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Status check (`ok` or `degraded`) |
| `/api/home` | GET | Homepage metadata: supported zones, data sources, featured parcels |
| `/api/parcels/search?q=` | GET | Search by address (ILIKE) or APN/AIN (exact). Up to 10 results. |
| `/api/parcels/{ain}/facts` | GET | Fast parcel detail: facts, zoning, overlays, standards, ADU, confidence. No LLM. |
| `/api/parcels/{ain}/assessment` | GET | LLM assessment only. Slower (2-5s). |
| `/api/parcels/{ain}` | GET | Full detail + LLM in a single call (backward-compatible). |

## Environment

**Backend** (Pydantic BaseSettings):

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | `postgresql+psycopg://postgres:postgres@db/regulation_engine` | SQLAlchemy async connection |
| `OPENAI_API_KEY` | `""` (fallback mode) | OpenAI credentials |
| `OPENAI_MODEL` | `gpt-4.1-mini` | LLM model slug |
| `MARTIN_URL` | `http://martin:3000` | Martin tile server |

**Frontend** (Vite build-time):

| Variable | Default | Purpose |
|----------|---------|---------|
| `VITE_API_URL` | `http://localhost:8000` | Backend API base URL |
| `VITE_MARTIN_URL` | `http://localhost:3001` | Martin tile server |
| `VITE_BASEMAP_TILE_URL` | OpenStreetMap | Raster basemap tile source |

## Testing

**Backend** — pytest with `asyncio_mode = "auto"`:
- `test_rules_engine.py` — Zone string parsing, rule lookup, height district FAR, confidence, ADU. All pure functions.
- `test_llm_service.py` — Fallback assessment, prompt construction, API integration with mocks.
- `test_home_service.py` / `test_home_api.py` — Home metadata service and API integration.

**Frontend** — Vitest + Testing Library:
- `App.test.tsx` — Integration tests: home panel, metadata fallback, assessment round-trip, recent searches.
- `recentSearches.test.ts` — Unit tests: deduplication and max cap.

**Ingestion** — No automated tests. Verification via `verify_data.py`.

## Gotchas

- **Zone string parsing is regex-heavy.** 20+ parsing tests exist for a reason — run the full suite if you modify `parse_zone_string`.
- **Chapter 1A detection has two paths:** bracket-format zone string OR community plan = "Central City" / "Central City North".
- **R1 variation zones** (R1V1, R1V2, R1R3, R1H) fall back to base R1 rules.
- **No database migrations.** Schema changes require re-running `create_tables.py` + `ingest.py`.
- **Martin tile URLs differ** between local (port 3001) and deployed (Railway public URL).
- **Two-phase loading race conditions.** The `requestIdRef` counter discards stale responses — preserve this pattern if changing the loading flow.
