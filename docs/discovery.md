# Discovery: LA Regulation Engine v2

**Date:** 2026-03-26
**Timeline:** ~1 week
**Audience:** Internal/team demo
**Status:** CONFIRMED

---

## Problem Statement

A developer searching for what can be built on a residential parcel in LA City must manually cross-reference multiple public GIS layers, parse zoning code strings, look up development standards in PDFs, and mentally reconcile overlays — a process that takes hours and requires domain expertise. This project builds a PoC that automates that pipeline: search by address/APN, get an evidence-backed buildability assessment with map visualization, confidence scoring, and LLM-generated plain-English explanations.

## Who's Affected

- **Primary:** The internal team evaluating whether this product concept is viable
- **Secondary:** Future users — homeowners, developers, architects checking buildability before engaging professionals

## Acceptance Criteria

1. User can search by address or APN and get back the correct parcel
2. Map shows the parcel polygon, surrounding buildings, and zoning overlay
3. Assessment panel displays: zone class, development standards (height, FAR, setbacks, density), allowed uses, overlay warnings, confidence level
4. LLM generates a plain-English summary with LAMC citations
5. Handles edge cases gracefully: out-of-scope parcels, split zones, Downtown/Chapter 1A, HPOZ/specific plan overlays
6. Deployed and accessible via URL (Railway backend, Vercel frontend)

## Constraints

- 1-week timeline — demo quality, not production
- Residential LA City parcels only (Original Code / Chapter 1 zones)
- Data seeded into PostGIS, not live API queries at runtime
- Developer must understand every layer (no black-box code generation)

## Non-Goals

- Commercial use analysis, full building code, conditional use permits
- Full LAMC parsing or ICC Building Code
- Downtown / Chapter 1A zone support
- Implementing specific plan or HPOZ rules (flag-and-cite only)
- Production-grade infrastructure, auth, rate limiting
- Mobile-optimized UI

---

## Recommended Stack (with rationale)

### Backend

| Component | Choice | Why |
|-----------|--------|-----|
| Language | Python 3.12+ | Already decided |
| Framework | FastAPI | Already decided |
| Package manager | uv | Already decided |
| DB driver (query layer) | SQLAlchemy 2.x + GeoAlchemy2 0.18.x | ORM for FastAPI route handlers; PostGIS column type mapping |
| DB driver (ingest) | psycopg 3.2.x (COPY protocol) | 280x faster than ORM inserts for 2.4M records |
| HTTP client (ingest) | aiohttp 3.11.x | More stable than httpx under sustained concurrency (httpx has documented PoolTimeout failures) |
| Geometry | Shapely 2.1.x | GeoJSON → WKB serialization bridge to PostGIS COPY |
| Retry | tenacity 9.x | Exponential backoff on ArcGIS endpoint failures |
| LLM SDK | openai (AsyncOpenAI) | User has existing API key; structured outputs via JSON schema |
| LLM model | GPT 5.4-mini (`gpt-5.4-mini`) | ~$4/1K lookups with caching; structured output via json_schema; 400K context |
| Linter/formatter | Ruff | Already decided |
| Type checker | mypy | Already decided |
| Tests | pytest | Already decided |

### Frontend

| Component | Choice | Why |
|-----------|--------|-----|
| Language | TypeScript 5.x | Already decided |
| Framework | React + Vite (SPA) | No SSR needed; minimal config; legible stack. Next.js adds complexity with zero benefit here |
| Map library | MapLibre GL JS v5.x | WebGL, native MVT, free, same org as Martin |
| Base map tiles | Protomaps PMTiles (free, no API key) | Zero-dependency base map; upgrade to Mapbox free tier later if visual polish needed |
| Map wrapper | react-map-gl/maplibre | Battle-tested React bindings, large ecosystem |
| UI components | shadcn/ui (Radix + Tailwind) | Owned source code, not a dependency. Card, Badge, Accordion, Combobox |
| Styling | Tailwind CSS | Already decided |
| Search | shadcn/ui Combobox + 300ms debounce | Server-side filtering, APN pattern detection for direct lookup |
| Package manager | pnpm | Already decided |
| Tests | Vitest | Already decided |
| Linter/formatter | ESLint + Prettier | Already decided |

### Infrastructure

| Component | Choice | Why |
|-----------|--------|-----|
| Database | PostgreSQL + PostGIS on Railway | Already decided; use PostGIS Docker template |
| Tile server | Martin (Rust, maplibre/martin) | Auto-discovers PostGIS tables, serves MVT tiles. Same org as MapLibre = first-party integration |
| Backend deploy | Railway (Dockerfile) | Dockerfile gives control over GDAL/GEOS system libs for Shapely; Railpack is too new and has bugs |
| Frontend deploy | Vercel | Already decided; pure static SPA, no serverless functions needed |
| Local dev | Docker Compose | FastAPI + PostGIS + Martin, matching production topology |
| Build system | Railway: Dockerfile; Vercel: Vite build | Dev/prod parity via Docker |

### Key Libraries NOT Used (and why)

| Library | Why not |
|---------|---------|
| geopandas | Heavy dependency; `to_postgis()` uses ORM inserts, 20-40x slower than COPY |
| ogr2ogr/GDAL CLI | Pagination bug on FeatureServer (OSGeo/gdal #10094); version drift on Railway |
| httpx | Documented PoolTimeout failures under sustained concurrency |
| Next.js | SSR adds complexity with no benefit for a tool app with no SEO needs |
| LangChain | Adds abstraction over a bounded use case; rule pack fits in a single prompt |
| instructor | Adds retry/validation layer over structured outputs that OpenAI handles natively |
| LiteLLM | Multi-provider abstraction unnecessary when committing to one provider |
| Leaflet | DOM rendering collapses at 10K polygons; we have millions |
| Mapbox GL JS | Proprietary license; MapLibre is the free fork with identical capability |
| Google Maps JS API | No native MVT support (can't consume Martin tiles); per-load pricing; limited polygon styling control |
| deck.gl (for now) | MapLibre handles MVT polygon rendering natively; deck.gl solves analytical viz (heatmaps, 3D) we don't need yet |
| OpenLayers | Different paradigm (desktop GIS toolkit); switching mid-project = full rewrite, not a "fallback" |
| RAG | Rule pack is ~15 zones x ~10 fields = ~1,500 tokens. Fits in context. RAG adds latency and retrieval error risk |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                          VERCEL (CDN)                           │
│  React + Vite SPA                                               │
│  ┌──────────┐  ┌───────────────────┐  ┌──────────────────────┐  │
│  │ Search   │  │ MapLibre GL JS    │  │ Assessment Panel     │  │
│  │ Combobox │  │ (MVT tiles from   │  │ (Card, Badge,        │  │
│  │          │  │  Martin)          │  │  Accordion)          │  │
│  └────┬─────┘  └────────┬──────────┘  └──────────┬───────────┘  │
│       │                 │                         │              │
└───────┼─────────────────┼─────────────────────────┼──────────────┘
        │ /api/parcels    │ /{table}/{z}/{x}/{y}    │ /api/assess
        ▼                 ▼                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                         RAILWAY                                 │
│                                                                 │
│  ┌──────────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ FastAPI Backend   │  │ Martin Tile  │  │ PostgreSQL +     │  │
│  │ (Dockerfile)     │  │ Server       │  │ PostGIS          │  │
│  │                  │  │ (Docker)     │  │                  │  │
│  │ • Parcel search  │  │ • Auto-      │  │ • parcels        │  │
│  │ • Spatial joins  │  │   discovers  │  │ • zoning         │  │
│  │ • Rules lookup   │  │   PostGIS    │  │ • overlays       │  │
│  │ • LLM assessment │  │   tables     │  │ • buildings      │  │
│  │ • OpenAI API     │  │ • MVT tiles  │  │ • boundaries     │  │
│  └────────┬─────────┘  └──────┬───────┘  └────────┬─────────┘  │
│           │                   │                    │             │
│           └───────────────────┴────────────────────┘             │
│                    (private networking)                          │
└─────────────────────────────────────────────────────────────────┘
```

### Runtime Flow

```
User enters address or APN
  │
  ├── APN? → SELECT * FROM parcels WHERE ain = $1
  │
  ├── Address? → Text search: SitusFullAddress ILIKE '%..%' (pg_trgm)
  │     │
  │     └── No match? → CAMS geocode → nearest parcel within buffer
  │
  ▼
Confirm LA City (city_name = 'Los Angeles')
  │
  ▼
Spatial joins (single PostGIS query):
  - zoning polygon → zone class + height district
  - specific plans → name + document URL
  - HPOZ → name + URL
  - community plan area → name
  - general plan land use → description
  │
  ▼
Deterministic rules engine:
  - zone_rules[zone_class] → setbacks, FAR, height, density, uses
  - Parse height district from ZONE_CMPLT
  - Detect Q/D/T condition prefixes → flag
  - Compute confidence (High/Medium/Low)
  │
  ▼
LLM assessment (GPT 5.4-mini):
  - System prompt: role + zone rules excerpt + LAMC citations + few-shot examples
  - User message: structured parcel facts as JSON
  - Output: ZoningAssessment (structured JSON, guaranteed schema)
  - Fallback: if LLM fails, return deterministic output only
  │
  ▼
Frontend: map (parcel + buildings + zoning) + assessment panel
```

### Data Ingestion (one-time seed)

```
ArcGIS REST endpoints
  │
  ▼
aiohttp (async, semaphore=6, tenacity retry)
  │ paginate: resultOffset + resultRecordCount
  │ f=geojson, outSR=4326
  │ dual end condition: exceededTransferLimit + empty features
  ▼
Shapely 2.x: from_geojson() → to_wkb(hex=True, include_srid=True)
  │
  ▼
psycopg3 COPY protocol → PostGIS tables
  │ ~70K rows/sec (2.4M parcels in ~34s of DB write time)
  ▼
CREATE INDEX CONCURRENTLY (GIST on geometry columns, after COPY)
  │
  ▼
ANALYZE
```

---

## Key Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Railway 5GB Hobby volume cap** | LA City parcels + indexes may hit 4-5 GB | Filter to LA City during ingest (~500K of 2.4M records). If tight, upgrade to Pro ($20/month, 50GB) or reduce building footprint scope |
| **Railway PostGIS template is PG16, not PG17** | Stack specifies PG17 | PG16 + PostGIS 3.4 is functionally equivalent for this use case. Accept PG16 for PoC |
| **NavigateLA endpoints go offline** | LA City GIS is less reliable than County | All data is seeded at ingest time, not queried at runtime. If endpoints die after seed, the demo still works |
| **ArcGIS pagination takes 30-60 min for parcels** | Slow iteration on ingest pipeline | Checkpoint/resume pattern; seed once, iterate on app code |
| **LLM hallucination on LAMC citations** | Shows wrong section numbers | System prompt includes explicit citation table; grounding instruction: "Only cite sections listed below" |
| **Mapbox token required?** | MapLibre is free but base map tiles need a source | Use free tile providers (OpenFreeMap, Stamen, Carto) or self-host with Martin |
| **Protomaps visual simplicity** | Base map is functional but not as polished as Mapbox/Google | Acceptable for internal demo; upgrade to Mapbox free tier if stakeholders want aerial imagery |

---

## Open Questions

1. **Storage monitoring:** Hobby plan has a 5GB cap. Full LA City parcels + indexes is estimated at 3.5-5 GB. If we hit the ceiling during ingest, fallback is: reduce building footprint scope first, then consider Pro upgrade ($20/mo) if needed.

---

## Proposed Build Order (1-week target)

This is a rough sequencing, not a detailed plan. The `/plan` phase will break this into concrete milestones.

| Day | Focus | What ships |
|-----|-------|-----------|
| 1 | **Foundation** | Docker Compose (PostGIS + Martin), project scaffolding (pyproject.toml, Vite+React), DB schema |
| 2 | **Ingest** | Parcel + zoning ingest pipeline, verify data in PostGIS, Martin serving tiles |
| 3 | **Ingest + API** | Overlay layers ingest, FastAPI parcel search + spatial join endpoint |
| 4 | **Rules + LLM** | Curated rule pack, LLM assessment endpoint, structured output |
| 5 | **Frontend** | Map with tiles, search bar, assessment panel wired to API |
| 6 | **Integration** | End-to-end flow, edge cases, deploy to Railway + Vercel |
| 7 | **Polish** | Test parcels, fix bugs, confidence display, citations |

---

## Resolved Decisions

| Decision | Rationale |
|----------|-----------|
| React + Vite over Next.js | No SSR benefit for a tool app; simpler config; understand every layer |
| MapLibre over Leaflet/Mapbox | Only option that handles millions of polygons (WebGL); free; same org as Martin |
| Martin over pg_tileserv/PMTiles | Live PostGIS connection = iterate on schema without re-export; auto-discovers tables |
| aiohttp over httpx for ingest | httpx has documented PoolTimeout under sustained concurrency |
| psycopg3 COPY over geopandas to_postgis | 280x faster for bulk loading |
| Dockerfile over Railpack | Railpack is beta (March 2026), has active bugs; Dockerfile gives GDAL/GEOS control |
| OpenAI GPT 5.4-mini | User has existing API key; structured output via json_schema; ~$4/1K lookups with caching; strong on multi-condition prompts |
| MapLibre + Protomaps PMTiles | Free renderer + free base map tiles = $0, no API key; deck.gl available as future add-on if needed |
| shadcn/ui over other component libs | Owned code, Radix primitives, native Tailwind |
| No RAG | Rule pack fits in ~1,500 tokens; RAG adds complexity with no benefit |

---

## Detailed Research Files

Full research with code patterns, gotchas, and source citations:

- `.claude/plans/research-gis-ingestion.md` — Ingest pipeline: aiohttp, pagination, COPY, PostGIS setup
- `.claude/plans/research.md` — Frontend stack + LLM integration research
