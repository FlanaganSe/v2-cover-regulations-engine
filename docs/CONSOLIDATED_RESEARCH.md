# Consolidated Research: LA Regulation Engine v2

**Date:** 2026-03-26
**Consolidated from:** 7 research files, discovery.md, DATA_SOURCES.md, requirements.md, decisions.md
**Purpose:** Single reference for planning and initial buildout

---

## 1. What This Product Does

A residential parcel lookup tool for LA City. User enters an address or APN, gets back:

- The correct parcel on a map
- Zoning designation and parsed development standards (height, FAR/RFA, setbacks, density, allowed uses)
- Overlay warnings (specific plans, HPOZ) with document links
- A confidence score (High/Medium/Low) with reasons
- An LLM-generated plain-English explanation with LAMC citations

**Core principle:** Deterministic facts-to-rules-to-assessment pipeline. The LLM explains; it does not decide.

**Product posture:** Evidence-backed demo tool, not legal advice and not a full entitlement system. If a parcel is unsupported or ambiguous, the system should say that explicitly rather than infer beyond the evidence.

### Scope

- City of Los Angeles residential parcels only
- Original Code (Chapter 1) zones only — Chapter 1A (Downtown) returns "not yet supported"
- ~15 residential zone classes covering ~95% of residential parcels
- Overlays are flag-and-cite, not deeply modeled
- Demo quality, not production

### Non-Goals

- Commercial use analysis, full building code, conditional use permits
- Full LAMC parsing or ICC Building Code
- Implementing specific plan or HPOZ rules
- Production auth, rate limiting, mobile UI
- RAG (rule pack fits in ~1,500 tokens)

### Approach Anti-Patterns

These architectural patterns were evaluated during research and explicitly rejected:

- This is a parcel resolution + rules engine, not a chatbot or conversational AI tool
- No automated legal-code parsing — use a curated, versioned rule pack instead
- No multi-schema data pipeline (raw/stage/core/publish) — flat tables with provenance
- No dual geometry columns — store EPSG:4326, transform on the fly when needed
- No separately deployed ingestion platform — CLI/scripts, not a data pipeline service
- No nationwide or multi-jurisdiction abstractions until the LA City demo works

---

## 2. Architecture

```
┌────────────────────────────────────────────────────────────┐
│                      VERCEL (CDN)                          │
│  React + Vite SPA                                          │
│  Search (Combobox) │ MapLibre GL JS │ Assessment Panel     │
└──────┬─────────────┴───────┬────────┴──────────┬───────────┘
       │ /api/parcels        │ /{table}/{z}/{x}/{y}  │ /api/assess
       ▼                     ▼                       ▼
┌────────────────────────────────────────────────────────────┐
│                      RAILWAY                               │
│  FastAPI (Dockerfile)  │  Martin (Docker)  │  PostGIS      │
│  • Parcel search       │  • Auto-discovers │  • parcels    │
│  • Spatial joins       │    PostGIS tables │  • zoning     │
│  • Rules lookup        │  • MVT tiles      │  • overlays   │
│  • LLM assessment      │                   │  • buildings  │
│  • OpenAI API          │                   │  • boundaries │
└────────────────────────────────────────────────────────────┘
         (private networking between Railway services)
```

**Runtime dependencies:** PostGIS, Martin, OpenAI API (with deterministic fallback).
**Ingestion dependencies:** ArcGIS REST endpoints (batch, not runtime).

### AWS Migration Path (Future)

| PoC (Railway + Vercel) | Production (AWS) |
|------------------------|------------------|
| Vercel SPA | CloudFront + S3 or Amplify |
| Railway FastAPI | ECS/Fargate |
| Railway Martin | ECS/Fargate |
| Railway PostGIS | RDS PostgreSQL + PostGIS |

Application code stays the same. Migration is infrastructure replacement.

**Planning caveat:** Railway + Vercel is the lowest-risk demo posture, but if AWS is mandatory for the demo, keep the same application design and change only deployment targets. Hillside/fire overlays remain stretch scope unless test parcels prove they are necessary for the first build.

---

## 3. Stack

All choices confirmed through research. Rationale included only where non-obvious.

### Backend

| Component | Choice | Notes |
|-----------|--------|-------|
| Language | Python 3.12+ | |
| Framework | FastAPI | |
| Package manager | uv | |
| DB driver (queries) | SQLAlchemy 2.x + GeoAlchemy2 | `postgresql+psycopg://` dialect |
| DB driver (ingest) | psycopg 3.x (COPY protocol) | 280x faster than ORM inserts for bulk |
| HTTP client (ingest) | aiohttp 3.11.x | httpx has PoolTimeout issues under sustained concurrency |
| Geometry | Shapely 2.x | GeoJSON → WKB bridge; same GEOS engine as PostGIS |
| Retry | tenacity 9.x | Exponential backoff on ArcGIS failures |
| LLM | openai SDK (Responses API) → current GPT-5 mini model | Structured outputs; exact model ID should be verified at implementation time |
| Linter/formatter | Ruff | |
| Type checker | mypy | |
| Tests | pytest | |

### Frontend

| Component | Choice | Notes |
|-----------|--------|-------|
| Language | TypeScript 5.x | |
| Framework | React + Vite (SPA) | No SSR benefit for this app |
| Map | MapLibre GL JS v5.x + react-map-gl/maplibre | WebGL; handles millions of polygons |
| Base map | Protomaps PMTiles | Free, no API key |
| UI components | shadcn/ui (Radix + Tailwind) | Owned source, not a dependency |
| Styling | Tailwind CSS | |
| Tests | Vitest | |
| Linter/formatter | ESLint + Prettier | |

### Infrastructure

| Component | Choice | Notes |
|-----------|--------|-------|
| Database | PostgreSQL 16 + PostGIS 3.4 on Railway | PG17 template may also be available |
| Tile server | Martin (Rust, ghcr.io/maplibre/martin) | Auto-discovers PostGIS tables → MVT tiles |
| Backend deploy | Railway (Dockerfile) | Needs GDAL/GEOS system libs for Shapely |
| Frontend deploy | Vercel | Static SPA |
| Local dev | Docker Compose | PostGIS + Martin + FastAPI |

### Libraries NOT Used (and why)

| Library | Why not |
|---------|---------|
| geopandas | `to_postgis()` is 20-40x slower than COPY |
| ogr2ogr/GDAL CLI | Known pagination bug on FeatureServer |
| Next.js | SSR adds complexity with no benefit |
| LangChain/instructor/LiteLLM | Abstraction over a bounded use case |
| Leaflet | DOM rendering collapses at 10K+ polygons |
| deck.gl | MapLibre handles MVT natively; deck.gl solves problems we don't have yet |
| RAG | Rule pack is ~1,500 tokens total |

---

## 4. Data Sources

Full endpoint details, field lists, and gotchas are in `DATA_SOURCES.md`. This section covers only what the planning phase needs beyond that reference.

### Verified Record Counts (2026-03-26)

| Layer | Records | Per Page | Pages | Ingest Time (est.) |
|-------|---------|----------|-------|-------------------|
| LA County Parcels | ~794K (SitusCity filter) → ~500-600K after boundary clip | 1,000 | ~794 | ~3-5 min |
| NavigateLA Zoning (71) | 58,976 | 20,000 | 3 | <10s |
| General Plan Land Use | 52,833 | 2,000 | ~27 | ~30s |
| Specific Plans (93) | 60 | — | 1 | <1s |
| HPOZ (75) | 35 | — | 1 | <1s |
| Community Plan Areas | 36 | — | 1 | <1s |
| City Boundaries (19) | 3 (multipolygon) | — | 1 | <1s |
| LARIAC Buildings | ~3.3M total | 1,000 | Demo bbox only (~10K) | ~15s |

**Total estimated ingest time: ~5-8 minutes** (dominated by parcel download).

### Key Source Findings

1. **Parcel filtering:** `SitusCity LIKE '%LOS ANGELES%'` returns 794K (includes LA County areas with LA mailing addresses). Must post-filter with `ST_Intersects` against city boundary polygon.

2. **NavigateLA > GeoHub:** NavigateLA exposes `ZONE_CMPLT`, `ZONE_CLASS`, `ZONE_CODE`, `ZONE_UNDER` (rich). GeoHub exposes only `Zoning` + `CATEGORY` (thin). NavigateLA also provides `NLA_URL` for overlay document links. Use NavigateLA for zoning and overlays.

3. **No API keys required** for any GIS endpoint. Only credentialed dependency is OpenAI.

4. **Dead endpoints:** LA City GeoHub Parcels FeatureServer (dead). LA City geocoder (offline). Use County parcels and CAMS geocoder.

5. **NLA_URL is relative:** Prefix with `https://maps.lacity.org/` for full URL.

6. **Data types to watch:** `YearBuilt1` is a string (not int). `AIN` can be `" "` (space) — filter: `AIN IS NOT NULL AND AIN <> ' '`. Building `HEIGHT` is in meters.

7. **Licensing risk:** LA Planning ArcGIS metadata includes disclaimer language. For demo, show "Data as of [date]" and source citations. Licensing review required before any non-demo/commercial use.

8. **CAMS geocoder returns SRID 2229** (NAD83 State Plane Zone V, US feet), not WGS84. Failure to transform produces points thousands of miles from LA. Always apply `ST_Transform(ST_SetSRID(ST_Point(x, y), 2229), 4326)` on geocoder results before any spatial operation.

---

## 5. Ingestion Pipeline

### Pattern: ArcGIS REST → aiohttp → Shapely → psycopg3 COPY → PostGIS

```
ArcGIS REST endpoints
  │
  ▼
aiohttp (async, semaphore=6, tenacity retry)
  │ paginate: resultOffset + resultRecordCount + orderByFields=OBJECTID
  │ f=geojson, outSR=4326
  │ stop condition: exceededTransferLimit=false AND empty/short features
  ▼
Shapely 2.x: from_geojson() → make_valid() → set_srid(4326) → to_wkb(hex=True, include_srid=True)
  │ Filter null geometries
  ▼
psycopg3 COPY protocol → PostGIS tables
  │ ~70K rows/sec write speed
  ▼
CREATE INDEX (GIST on geometry, B-tree on AIN, GIN trigram on address)
  │
  ▼
ANALYZE
  │
  ▼
Post-filter parcels: DELETE WHERE NOT ST_Intersects(geom, city_boundary)
```

### Critical Pagination Rules

- **Always check `exceededTransferLimit`** — the only reliable signal for more pages.
- ESRI can return **zero features with `exceededTransferLimit: true`**. Handle this: increment offset and continue.
- **Dual end condition:** Stop when `exceededTransferLimit` is absent/false AND features array is empty or short.
- Include `orderByFields=OBJECTID` for deterministic page ordering.
- Always request `outSR=4326`. Source CRS varies (102645, 102100). Never store native CRS.

### Alternative Pagination Strategy (for largest layers)

Use `returnIdsOnly=true` to get all object IDs, then batch by OBJECTID subsets. This avoids the normal feature-count response limit and gives deterministic checkpoints. Consider this for parcels if offset-based pagination proves flaky.

### Checkpoint/Resume

Track last successful offset per layer in a JSON checkpoint file. On restart, resume from checkpoint. This prevents re-downloading after a crash mid-ingest.

### Geometry Preprocessing

Run `ST_MakeValid(geom)` on loaded data — government GIS data often has self-intersecting polygons that break intersection queries. Also run `ST_Force2D(geom)` to strip Z/M coordinates — ArcGIS endpoints commonly export 3D/4D geometries that break Martin tile serving.

---

## 6. Database Schema

### Extensions

```sql
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

### Tables

```sql
-- Parcels (from LA County)
CREATE TABLE parcels (
    id SERIAL PRIMARY KEY,
    ain VARCHAR(10) NOT NULL,
    apn VARCHAR(12),
    address TEXT,
    situs_city VARCHAR(50),
    situs_zip VARCHAR(10),
    use_code VARCHAR(10),
    use_description TEXT,
    year_built INTEGER,
    bedrooms INTEGER,
    sqft_main INTEGER,
    land_value NUMERIC,
    improvement_value NUMERIC,
    center_lat DOUBLE PRECISION,
    center_lon DOUBLE PRECISION,
    geom GEOMETRY(MULTIPOLYGON, 4326) NOT NULL
);

-- Zoning (NavigateLA layer 71)
CREATE TABLE zoning (
    id SERIAL PRIMARY KEY,
    zone_cmplt VARCHAR(100),
    zone_class VARCHAR(20),
    zone_code VARCHAR(20),
    zone_under VARCHAR(100),
    zoning_description TEXT,
    tooltip TEXT,
    geom GEOMETRY(MULTIPOLYGON, 4326) NOT NULL
);

-- Specific Plans (NavigateLA layer 93)
CREATE TABLE specific_plans (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    nla_url TEXT,
    geom GEOMETRY(MULTIPOLYGON, 4326) NOT NULL
);

-- HPOZ (NavigateLA layer 75)
CREATE TABLE hpoz (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    nla_url TEXT,
    geom GEOMETRY(MULTIPOLYGON, 4326) NOT NULL
);

-- Community Plan Areas
CREATE TABLE community_plan_areas (
    id SERIAL PRIMARY KEY,
    cpa_num VARCHAR(10),
    name TEXT NOT NULL,
    geom GEOMETRY(MULTIPOLYGON, 4326) NOT NULL
);

-- General Plan Land Use
CREATE TABLE general_plan_lu (
    id SERIAL PRIMARY KEY,
    gplu_desc TEXT,
    lu_label VARCHAR(50),
    generalize VARCHAR(50),
    cpa VARCHAR(10),
    geom GEOMETRY(MULTIPOLYGON, 4326) NOT NULL
);

-- City Boundaries
CREATE TABLE city_boundaries (
    id SERIAL PRIMARY KEY,
    city_name VARCHAR(100) NOT NULL,
    feat_type VARCHAR(20),
    geom GEOMETRY(MULTIPOLYGON, 4326) NOT NULL
);

-- Building Footprints (demo neighborhoods only)
CREATE TABLE buildings (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20),
    height DOUBLE PRECISION,
    area DOUBLE PRECISION,
    status VARCHAR(20),
    geom GEOMETRY(POLYGON, 4326) NOT NULL
);

-- Provenance tracking
CREATE TABLE ingest_metadata (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL,
    source_url TEXT NOT NULL,
    filter_used TEXT,
    retrieved_at TIMESTAMPTZ DEFAULT NOW(),
    row_count INTEGER
);
```

### Indexes

```sql
-- Spatial (GIST on every geometry column)
CREATE INDEX idx_parcels_geom ON parcels USING GIST (geom);
CREATE INDEX idx_zoning_geom ON zoning USING GIST (geom);
CREATE INDEX idx_specific_plans_geom ON specific_plans USING GIST (geom);
CREATE INDEX idx_hpoz_geom ON hpoz USING GIST (geom);
CREATE INDEX idx_community_plan_areas_geom ON community_plan_areas USING GIST (geom);
CREATE INDEX idx_general_plan_lu_geom ON general_plan_lu USING GIST (geom);
CREATE INDEX idx_city_boundaries_geom ON city_boundaries USING GIST (geom);
CREATE INDEX idx_buildings_geom ON buildings USING GIST (geom);

-- Attribute lookups
CREATE INDEX idx_parcels_ain ON parcels (ain);
CREATE INDEX idx_parcels_address_trgm ON parcels USING GIN (address gin_trgm_ops);
CREATE INDEX idx_zoning_zone_class ON zoning (zone_class);
CREATE INDEX idx_city_boundaries_name ON city_boundaries (city_name);
```

### Storage Estimate

| Component | Estimated Size |
|-----------|---------------|
| parcels (~600K rows + indexes) | ~1.2 GB |
| zoning (59K + indexes) | ~230 MB |
| general_plan_lu (53K + indexes) | ~180 MB |
| Overlay tables (<200 rows total) | <5 MB |
| buildings (10K demo + indexes) | ~25 MB |
| PostgreSQL overhead | ~200 MB |
| **Total** | **~1.8-2.5 GB** |

Well within Railway Hobby plan (5 GB). Even with larger building scope, stays under 4 GB.

### Spatial Area Note

`ST_Area()` on EPSG:4326 geometry returns square degrees (meaningless). For split-zone overlap ranking, cast to geography: `ST_Area(ST_Intersection(p.geom, z.geom)::geography)`. This computes area in square meters on the spheroid. No need to store a second SRID column for a demo.

---

## 7. Zone String Parsing

### ZONE_CMPLT Format

```
[prefix]<base_zone>-<height_district>[D][suffix1][-suffix2...]
```

**Examples from live data (50+ R1 variants observed):**

| Example | Base Zone | HD | Prefix | Notes |
|---------|-----------|-----|--------|-------|
| `R1-1` | R1 | 1 | — | Clean, high confidence |
| `(Q)R1-1` or `[Q]R1-1` | R1 | 1 | Q | "Additional restrictions may apply" |
| `(T)R1-1` or `[T]R1-1` | R1 | 1 | T | "Zone classification may change" |
| `(T)(Q)R1-1` | R1 | 1 | T+Q | Both flags |
| `R1-1D` | R1 | 1 | — | D limitation: "Reduced FAR may apply" |
| `R1-1-HPOZ` | R1 | 1 | — | Historic overlay |
| `R1-1-CDO` | R1 | 1 | — | Community Design Overlay |
| `R1-1-RFA` | R1 | 1 | — | Residential Floor Area District |
| `[Q]R1-2D-CDO-RIO` | R1 | 2 | Q | Multiple suffixes |

### Parsing Logic

```python
import re

ZONE_PATTERN = re.compile(
    r'^'
    r'(?:\(F\))?'                    # (F) prefix (rare)
    r'(?:\[?[(\[]?([QTqt]+)\]?\)?)*' # Q, T prefixes in () or []
    r'([A-Z][A-Z0-9.]+?)'           # Base zone class (R1, RD1.5, RE9, etc.)
    r'-(\d+)'                        # Height district number
    r'(D)?'                          # D limitation (after HD)
    r'((?:-[A-Z][A-Z0-9]*)*)'       # Dash-separated suffixes
    r'$'
)
```

### Chapter 1A Detection

Chapter 1A zones use bracket format: `[MB3-SH1-1][CX3-4][CPIO]`. Probing `ZONE_CMPLT LIKE '[%'` returned 0 results in layer 71. **Detection strategy:** Check Community Plan Area for "Central City" / "Central City North", or check `ZONE_CLASS` against a known Chapter 1 zone list.

### Condition Flags

| Flag | User-Facing Message | Confidence Impact |
|------|-------------------|-------------------|
| `(Q)` or `[Q]` | "Additional restrictions may apply (see qualifying ordinance)" | → Medium |
| `(T)` or `[T]` | "Zone classification may change" | → Medium |
| `D` (after HD) | "Reduced FAR may apply under D limitation" | → Medium |
| `-HPOZ` suffix | "Design review required by HPOZ Board" | → Low |
| `-CDO` suffix | "Additional design standards may apply" | → Medium |
| `-RFA` suffix | "Floor area may be further restricted" | → Medium |
| `-CPIO` suffix | "Community plan overlay may modify standards" | → Medium |

---

## 8. Residential Development Standards (Rule Pack)

Hand-curated from LA City Zoning Code Summary PDF and ZA Memo 143. This is the source of truth for the deterministic rules engine.

### Zone Rules

| Zone | LAMC § | Min Lot (sqft) | Height HD1 | Stories | RFA/FAR | Front | Side | Rear | Density | Uses |
|------|--------|---------------|------------|---------|---------|-------|------|------|---------|------|
| RA | 12.07 | 17,500 | 36 ft | 2 | 0.25 RFA | 20%≤25 | 10 | 25%≤25 | 1/lot | SF, agri |
| RE20 | 12.07.01 | 20,000 | 36 ft | 2 | 0.35 RFA | 20%≤25 | 10 | 25%≤25 | 1/lot | SF |
| RE15 | 12.07.01 | 15,000 | 36 ft | 2 | 0.35 RFA | 20%≤25 | 10%w | 25%≤25 | 1/lot | SF |
| RE11 | 12.07.01 | 11,000 | 33 ft | 2 | 0.40 RFA | 20%≤25 | 5 | 20%≤25 | 1/lot | SF |
| RE9 | 12.07.01 | 9,000 | 33 ft | 2 | 0.40 RFA | 20%≤25 | 5 | 20%≤25 | 1/lot | SF |
| RS | 12.07.1 | 7,500 | 33 ft | 2 | 0.45 RFA | 20%≤25 | 5 | 20 | 1/lot | SF |
| R1 | 12.08 | 5,000 | 33 ft | 2 | 0.45 RFA (BMO) | 20%≤20 | 5 | 15 | 1/lot | SF+ADU |
| R2 | 12.09 | 5,000 | 33 ft | 2 | inherits R1 | 20%≤20 | 5 | 15 | 2,500/u | Two-family |
| RD3 | 12.09.1 | 3,000 | 45 ft | — | 3:1 FAR | 15 | 5 | 15 | 3,000/u | Multi |
| RD2 | 12.09.1 | 2,000 | 45 ft | — | 3:1 FAR | 15 | 5 | 15 | 2,000/u | Multi |
| RD1.5 | 12.09.1 | 1,500 | 45 ft | — | 3:1 FAR | 15 | 5 | 15 | 1,500/u | Multi |
| R3 | 12.10 | 5,000 | 45 ft | 3 | 3:1 FAR | 15 | 5+1/st | 15+1/st | 800/u | Multi |
| R4 | 12.11 | 5,000 | unlimited | — | 3:1+ FAR | 15 | 5+1/st | 15+1/st | 400/u | Multi, hotel |
| R5 | 12.12 | 5,000 | unlimited | — | 3:1+ FAR | 15 | =R4 | =R4 | 200/u | Multi, hotel |

**Key rules:**
- R1/RS/RE/RA use **RFA** (Residential Floor Area), not standard FAR. RFA overrides height district FAR.
- RD/R3/R4/R5 use standard **FAR** from the height district.
- R1 BMO (flat lots): `RFA = 0.45 × lot area`. Guaranteed minimum 800 sqft. Garage exempt: 200 sqft/space.
- R1 hillside uses slope-banded FAR (0.50 at 0% slope → 0.00 at 100%+). If hillside data unavailable, default to flat-lot RFA and flag.
- R1 variation zones (R1V1, R1R, etc.): treat as R1 base with "reduced RFA may apply" flag.
- Side yard for R3/R4/R5: `5 ft + 1 ft per story above 2nd` (max 16 ft).
- Rear yard for R3/R4/R5: `15 ft + 1 ft per story above 3rd` (max 20 ft).

### Height District → FAR

| Height District | FAR | Height (R1/RS/R2/RD) | Height (R3) | Height (R4/R5) |
|----------------|-----|----------------------|-------------|----------------|
| 1 | 3.0 | 33 ft / 2 stories | 45 ft / 3 stories | 75 ft (R4) / unlimited (R5) |
| 1L | 3.0 | 33 ft / 3 stories | 45 ft / 3 stories | 45 ft |
| 1VL | 3.0 | 30 ft / 2 stories | 36 ft / 2 stories | 30 ft |
| 1XL | 3.0 | 30 ft / 2 stories | 30 ft / 2 stories | 30 ft |
| 2 | 6.0 | 33 ft | 45 ft | unlimited |
| 3 | 10.0 | 33 ft | 45 ft | unlimited |
| 4 | 13.0 | 33 ft | 45 ft | unlimited |

**Note:** For R1/RS/RE/RA, height district FAR is theoretical — RFA is the binding constraint.

### ADU/JADU Rules (ZA Memo 143)

- 1 ADU + 1 JADU allowed per single-family lot (3 total units)
- ADU max: 1,200 sqft detached; 50% of primary if attached (max 1,200 sqft); guaranteed min 800 sqft
- JADU max: 500 sqft (interior conversion only)
- ADU setbacks: 4 ft min (side/rear)
- ADU height: up to 2 stories (~16-18 ft)
- No parking within 0.5 mi of transit or for garage conversion
- State law (AB 68, SB 13) preempts local zoning

---

## 9. Runtime Flow

```
User enters address or APN
  │
  ├── APN detected (regex: \d{4}-?\d{3}-?\d{3})
  │     → SELECT * FROM parcels WHERE ain = $1
  │
  ├── Address
  │     → Text search: address ILIKE '%..%' (pg_trgm indexed)
  │     │
  │     └── No match? → CAMS geocode → ST_DWithin(parcel.geom, point, 50m)
  │
  ▼
Confirm LA City: ST_Intersects(parcel.geom, city_boundary WHERE city_name='Los Angeles')
  │
  ▼
Spatial joins (single PostGIS query with LATERAL for split-zone handling):
  - zoning polygon → zone_cmplt + zone_class (largest overlap wins)
  - specific plans → name + document URL
  - HPOZ → name + URL
  - community plan area → name
  - general plan land use → description
  │
  ▼
Parse zone string → base_zone, height_district, Q/D/T flags, suffixes
  │
  ▼
Rules lookup: zone_rules[base_zone] → setbacks, RFA/FAR, height, density, uses
Height district FAR: hd_far[height_district] → FAR (override by RFA if applicable)
  │
  ▼
Compute confidence:
  - High: supported residential zone, no overlays, deterministic rules complete
  - Medium: one overlay flag, or Q/D/T condition, or one interpretive branch
  - Low: Chapter 1A, unmodeled specific plan/HPOZ, conflicting signals
  │
  ▼
LLM assessment (Responses API + Structured Outputs):
  - System prompt: role + zone rules excerpt + citation table + few-shot examples (~1,500 tokens)
  - User message: structured parcel facts as JSON (~300-500 tokens)
  - Output: schema-constrained assessment object
  - Exact current GPT-5 mini model selected at implementation time
  - Fallback: if LLM fails, return deterministic output only with llm_available=false
  │
  ▼
Response → frontend: map (parcel + buildings + zoning) + assessment panel
```

### Core Spatial Join Query

```sql
SELECT
    p.ain, p.address,
    z.zone_cmplt, z.zone_class,
    sp.name AS specific_plan_name, sp.nla_url AS specific_plan_url,
    h.name AS hpoz_name, h.nla_url AS hpoz_url,
    cpa.name AS community_plan,
    gplu.gplu_desc AS general_plan_lu
FROM parcels p
LEFT JOIN LATERAL (
    SELECT zone_cmplt, zone_class
    FROM zoning z
    WHERE ST_Intersects(z.geom, p.geom)
    ORDER BY ST_Area(ST_Intersection(z.geom, p.geom)::geography) DESC
    LIMIT 1
) z ON true
LEFT JOIN specific_plans sp ON ST_Intersects(sp.geom, p.geom)
LEFT JOIN hpoz h ON ST_Intersects(h.geom, p.geom)
LEFT JOIN community_plan_areas cpa ON ST_Intersects(cpa.geom, p.geom)
LEFT JOIN general_plan_lu gplu ON ST_Intersects(gplu.geom, p.geom)
WHERE p.ain = $1;
```

With GIST indexes, this completes in <100ms for a single parcel.

---

## 10. LLM Integration

### Structured Output Pattern

Implementation should use the OpenAI **Responses API** with **Structured Outputs**. The planning constraint is the pattern, not a specific SDK helper or hard-coded model ID. At implementation time, verify the exact currently available GPT-5 mini model and use a schema-constrained output for the assessment shape.

```python
class ZoningAssessment(BaseModel):
    summary: str
    primary_dwelling_allowed: bool
    adu_likely_allowed: bool
    max_height_ft: float
    max_stories: int | None
    far_or_rfa: float
    front_setback_ft: float
    side_setback_ft: float
    rear_setback_ft: float
    density_description: str
    allowed_uses: list[str]
    overlay_warnings: list[str]
    confidence: str              # "High" | "Medium" | "Low"
    confidence_reason: str
    citations: list[str]
    caveats: list[str]
```

### Grounding Rules

- System prompt includes complete zone rules excerpt + citation table for the relevant zone
- Grounding instruction: "Only cite sections listed below. If unsure, say so."
- Confidence is computed **deterministically by the rules engine**, not by the LLM
- The LLM explains and narrates; it does not calculate FAR, setbacks, or height limits
- All citations come from a whitelist of known references

### Fallback

If OpenAI call fails (timeout, rate limit, error):
1. Return deterministic assessment only (rules engine output)
2. Set `llm_available: false` in response
3. Frontend shows deterministic facts without plain-English summary

### Cost

- Per assessment: ~2,500-3,300 tokens (system + user + output)
- ~$0.004-0.013 per assessment depending on caching
- 100 assessments/day: <$1.50/day

---

## 11. Frontend

### Map Layers (bottom to top)

1. **Protomaps PMTiles base map** — streets, labels, terrain
2. **Building footprints** — gray fill, low opacity (from Martin)
3. **Zoning polygons** — color-coded by zone class (from Martin)
4. **Selected parcel** — thick border, semi-transparent fill (GeoJSON from API)
5. **Overlay boundaries** — dashed outlines for specific plans, HPOZ (from Martin)

### Search Flow

1. User types in Combobox → 300ms debounce → `GET /api/parcels/search?q=...`
2. APN detection (regex `\d{4}-?\d{3}-?\d{3}`) routes to APN lookup
3. Results in dropdown (address, APN, zone class preview)
4. Select → map flyTo parcel centroid → load full assessment
5. Assessment panel: zone info, standards, LLM explanation, citations

### Assessment Panel Structure

- **Summary card** — plain-English LLM explanation
- **Parcel facts** — address, APN, lot size, year built
- **Zoning/standards** — zone class, height, FAR/RFA, setbacks, density, uses
- **Overlays/warnings** — specific plan, HPOZ, Q/D/T flags with document links
- **Confidence** — badge (Green/Yellow/Red) + reasons
- **Citations** — clickable LAMC section references

### Protomaps Setup

```tsx
import { Protocol } from 'pmtiles';
import maplibregl from 'maplibre-gl';

const protocol = new Protocol();
maplibregl.addProtocol("pmtiles", protocol.tile);
// Must be called ONCE before map mounts (root-level useEffect)
```

---

## 12. API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/parcels/search?q=<query>` | Search by address or APN |
| GET | `/api/parcels/{ain}` | Parcel detail + spatial joins + rules + assessment |
| GET | `/health` | Health check |

Keep the API narrow. The parcel detail endpoint should return everything needed for the frontend in a single call (parcel facts, zoning, overlays, rules, assessment).

### Response Shape

The assessment response should contain distinct sections:
- Parcel identity (ain, apn, address, geometry)
- Scope status (in LA City? supported zone?)
- Base zoning facts (zone string, zone class, height district, parsed flags)
- Overlay flags (specific plan, HPOZ, with document URLs)
- Development standards (height, FAR/RFA, setbacks, density, uses)
- Confidence (level + reasons)
- LLM explanation (summary + citations + caveats)
- Source metadata (data as of date, source URLs)

Rule citations, source URLs, retrieval timestamps, and confidence inputs should be stored explicitly and returned by the API. They should not live only inside prompts.

---

## 13. Deployment

### Docker Compose (Local Dev)

```yaml
services:
  db:
    image: postgis/postgis:16-3.4-alpine
    environment:
      POSTGRES_DB: regulation_engine
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports: ["5432:5432"]
    volumes: [pgdata:/var/lib/postgresql/data]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      retries: 5

  martin:
    image: ghcr.io/maplibre/martin:v0.15.0
    ports: ["3000:3000"]
    environment:
      DATABASE_URL: postgres://postgres:postgres@db/regulation_engine
    depends_on:
      db: { condition: service_healthy }

  backend:
    build: ./backend
    ports: ["8000:8000"]
    environment:
      DATABASE_URL: postgresql+psycopg://postgres:postgres@db/regulation_engine
      OPENAI_API_KEY: ${OPENAI_API_KEY}
    depends_on:
      db: { condition: service_healthy }
    command: uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

volumes:
  pgdata:
```

**Note:** Martin uses `postgres://` (libpq). FastAPI uses `postgresql+psycopg://` (SQLAlchemy dialect). Different URL schemes, same database.

### Railway (3 Services on Hobby Plan)

| Service | Image | Public | Notes |
|---------|-------|--------|-------|
| PostgreSQL + PostGIS | `postgis/postgis:16-3.4` | No (internal) | Railway template |
| FastAPI | Custom Dockerfile | Yes (port 8000) | GDAL/GEOS system libs |
| Martin | `ghcr.io/maplibre/martin` | Yes (port 3000) | Auto-discovers PostGIS |

Private networking between services. Martin should use a read-only DB role.

**Estimated cost:** $5-10/month on Hobby plan (with $5 credit, actual ~$0-5).

**Volume warning:** Railway volumes default to 500 MB — manually resize to 5 GB in volume settings before loading data. If the volume fills to 100%, PostgreSQL enters a crash loop (`PANIC: no space left on device`) and cannot accept connections to delete data — recovery requires a plan upgrade. Monitor with `SELECT pg_database_size(current_database())`.

### Vercel (Free Tier)

- Vite SPA → static deploy
- `vercel.json`: `{"rewrites": [{"source": "/(.*)", "destination": "/index.html"}]}`
- Env vars: `VITE_API_URL`, `VITE_MARTIN_URL`

### CORS

FastAPI and Martin both need CORS headers for the Vercel frontend domain + localhost dev.

### Dockerfile (FastAPI)

```dockerfile
FROM python:3.12-slim
RUN apt-get update && apt-get install -y libgeos-dev libgdal-dev && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen --no-dev
COPY . .
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 14. Project Structure

```
backend/
├── pyproject.toml
├── Dockerfile
├── app/
│   ├── main.py              # FastAPI app + lifespan
│   ├── config.py            # pydantic-settings
│   ├── database.py          # async engine + session
│   ├── routers/
│   │   └── parcels.py       # /api/parcels/* endpoints
│   ├── models/
│   │   └── parcel.py        # SQLAlchemy + GeoAlchemy2
│   ├── schemas/
│   │   └── parcel.py        # Pydantic response models
│   ├── services/
│   │   ├── parcel_service.py  # search + spatial joins
│   │   ├── rules_engine.py    # deterministic zone rules
│   │   └── llm_service.py     # OpenAI assessment
│   └── data/
│       └── zone_rules.py      # hardcoded rule pack
├── tests/
│   ├── conftest.py
│   ├── test_parcels.py
│   └── test_rules_engine.py
└── scripts/
    ├── create_tables.py       # DDL + extensions + indexes
    ├── ingest.py              # ArcGIS → PostGIS pipeline
    └── verify_data.py         # row counts, geometry checks, sample queries

frontend/
├── package.json
├── vite.config.ts
├── vercel.json
├── src/
│   ├── App.tsx
│   ├── components/
│   │   ├── Map.tsx
│   │   ├── SearchBar.tsx
│   │   ├── AssessmentPanel.tsx
│   │   └── ConfidenceBadge.tsx
│   ├── hooks/
│   │   └── useParcelSearch.ts
│   ├── lib/
│   │   ├── api.ts
│   │   └── mapStyle.ts
│   └── types/
│       └── assessment.ts

docker-compose.yml
martin.yaml               # optional: control which tables Martin exposes
```

---

## 15. Risk Register

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|-----------|
| Zone string parsing complexity | Medium | High | 50+ R1 variants. Regex handles prefixes/suffixes. Unknown patterns → "unsupported, review manually." |
| LLM citation hallucination | Medium | Medium | Citation whitelist in system prompt. Deterministic fallback. Low temperature. |
| NavigateLA goes offline during ingest | High | Low | One-time seed. Demo works after seed. Cache raw GeoJSON as backup. |
| Railway storage cap | High | Low | Estimated 1.8-2.5 GB within 5 GB limit. Resize volume from 500 MB default before loading. 100% full = unrecoverable crash loop. |
| CAMS geocoder SRID mismatch | High | Medium | CAMS returns SRID 2229 (State Plane feet), not 4326. Always `ST_Transform` geocoder results or points land thousands of miles away. |
| Geocoder returns street centerline | Medium | Medium | Text search first. CAMS fallback uses ST_DWithin (50m buffer), not strict point-in-polygon. |
| Self-intersecting / 3D geometry from ESRI | Medium | Medium | `ST_MakeValid` + `ST_Force2D` after load. Filter null geometries during ingest. |
| Martin exposes all PostGIS tables | Low | Medium | Use martin.yaml to whitelist tables. Or use views that expose only needed columns. |
| Protomaps base map too plain | Low | Medium | Acceptable for demo. Swap to Stadia/Maptiler/Mapbox free tier if needed. |
| GPT 5.4-mini model ID changes | Low | Low | Verify model ID at build time. Model name is a config value. |
| Railway idle suspension | Low | Medium | Check if Hobby services auto-suspend. May need a keep-alive or accept cold start latency. |
| Licensing risk for non-demo use | High | N/A for demo | Show "data as of" in UI. Licensing review required before commercial use. |

---

## 16. Edge Cases

| Case | Handling |
|------|---------|
| Split-zoned parcels | Polygon intersection + largest overlap area (LATERAL subquery). Not centroid. |
| Downtown / Chapter 1A | Detect via CPA = "Central City" or bracket zone format. Return "not yet supported." |
| Q/D/T conditions | Detect prefix, flag to user, do not resolve. Reduce confidence. |
| Height district determines FAR | Parse from ZONE_CMPLT (number after dash). Map to FAR table. |
| R1 Mansionization (flat vs hillside) | Default to flat-lot RFA (0.45). Flag "may differ for hillside lots" if no hillside data. |
| Parcel outside LA City | Check boundary table. Return "out of scope — different jurisdiction." |
| Address not found | Text search → CAMS geocode → nearest parcel within 50m → no result = "address not found." |
| Stale GIS data | Show "data as of [date]" in UI. Acceptable for demo. |

---

## 17. Test Parcels

Validate pipeline against these categories. Specific APNs to be identified during ingestion.

| Category | Why |
|----------|-----|
| Clean R1 (flat, no overlays) | Happy path → High confidence |
| RE or RS zone | Different lot size / density rules |
| RD or R3 (multi-family) | Tests density and multi-unit logic |
| Parcel in HPOZ | Triggers overlay flag → Medium/Low confidence |
| Parcel in Specific Plan | Triggers overlay flag → reduced confidence |
| Downtown (Chapter 1A) | Returns "not yet supported" |
| Address → street centerline | Tests text-search + buffer fallback |
| Split-zoned parcel | Tests largest-overlap logic |
| Parcel outside LA City | Returns "out of scope" |

Use ZIMAS (https://zimas.lacity.org) as the QA reference for validating test parcels.

---

## 18. Build Order

| Phase | Focus | Ships |
|-------|-------|-------|
| 1 | **Foundation** | Docker Compose (PostGIS + Martin), project scaffolding, DB schema + indexes |
| 2 | **Ingest** | Parcel + zoning pipeline, verify data in PostGIS, Martin serving tiles |
| 3 | **Ingest + API** | Overlay layers, FastAPI parcel search + spatial join endpoint |
| 4 | **Rules + LLM** | Zone string parser, curated rule pack, LLM assessment endpoint |
| 5 | **Frontend** | Map with tiles, search bar, assessment panel wired to API |
| 6 | **Integration + Deploy** | End-to-end flow, edge cases, Railway + Vercel deploy |
| 7 | **Polish** | Test parcels, bug fixes, confidence display, citations |

This order proves the data and deterministic engine before UI polish or AI behavior.

---

## 19. Resolved Decisions

These were evaluated during research. Each is now resolved — do not re-litigate during planning.

| Decision | Resolution | Notes |
|----------|-----------|-------|
| Ingest as separate phase or part of main build? | Separate. Ingest + verify first, then build app against seeded data. | Reduces risk. Data issues found early. |
| Martin config file vs auto-discovery? | Auto-discovery. Add martin.yaml only if unwanted tables are exposed. | Simpler to start. |
| Separate `/assess` endpoint or combined with `/parcels/{ain}`? | Combined. Single call returns everything. | Fewer round trips. Simpler frontend. |
| Schema: simple flat tables vs raw/stage/core separation? | Flat tables. Provenance tracked in `ingest_metadata`. | raw/stage/core adds complexity without demo benefit. |
| Parcel data: filter during download or post-filter in PostGIS? | SitusCity filter during download, post-filter with ST_Intersects as safety net. | Reduces download time. Post-filter catches edge cases. |
| GPT 5.4-mini model ID | Use `gpt-5.4-mini`. Keep as a config value; verify at build time. | Model naming can change. |

---

## Verified Endpoint Reference

```
# PARCELS
https://public.gis.lacounty.gov/public/rest/services/LACounty_Cache/LACounty_Parcel/MapServer/0

# ZONING
https://maps.lacity.org/arcgis/rest/services/Mapping/NavigateLA/MapServer/71

# OVERLAYS
Specific Plans:  https://maps.lacity.org/arcgis/rest/services/Mapping/NavigateLA/MapServer/93
HPOZ:            https://maps.lacity.org/arcgis/rest/services/Mapping/NavigateLA/MapServer/75

# CONTEXT
Community Plans: https://services5.arcgis.com/7nsPwEMP38bSkCjy/arcgis/rest/services/Community_Plan_Areas/FeatureServer/0
General Plan LU: https://services5.arcgis.com/7nsPwEMP38bSkCjy/arcgis/rest/services/General_Plan_Land_Use/FeatureServer/1

# BUILDINGS
https://public.gis.lacounty.gov/public/rest/services/LACounty_Dynamic/LARIAC_Buildings_2020/MapServer/0

# BOUNDARIES
https://public.gis.lacounty.gov/public/rest/services/LACounty_Dynamic/Political_Boundaries/MapServer/19

# GEOCODING (fallback only)
https://geocode.gis.lacounty.gov/geocode/rest/services/CAMS_Locator/GeocodeServer

# REGULATORY TEXT
Zoning Summary PDF:  https://planning.lacity.gov/odocument/eadcb225-a16b-4ce6-bc94-c915408c2b04/Zoning_Code_Summary.pdf
ZA Memo 143 (ADU):   https://planning.lacity.gov/odocument/184600d8-71d7-4d74-baf1-1f9cd2603320/ZA_Memo_No_143.pdf
Code Manual:         https://docs.ladbs.org/zoning-code-manual-and-commentary
LAMC Chapter 1:      https://codelibrary.amlegal.com/codes/los_angeles/latest/lapz/0-0-0-57924

# QA REFERENCE (not a data source)
ZIMAS: https://zimas.lacity.org
```
