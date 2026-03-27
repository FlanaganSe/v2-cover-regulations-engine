# LA Zoning Regulation Engine

A zoning lookup tool for Los Angeles residential parcels. Search by address or APN, get a comprehensive assessment: zone class, height/FAR/setback standards, ADU eligibility, overlay warnings, confidence score, and a plain-language summary.

Every number comes from a deterministic rules engine. The LLM explains facts — it doesn't decide them.

**Live demo:** https://frontend-production-349e.up.railway.app/

## How it works

```
User searches address/APN
  → Backend finds the parcel in PostGIS
  → Spatial joins determine zoning, overlays, jurisdiction
  → Rules engine (pure functions) computes standards, FAR, ADU, confidence
  → LLM summarizes the deterministic results (optional — graceful fallback)
  → Frontend renders assessment + interactive map
```

The key design decision: all GIS data is bulk-seeded into PostGIS from public ArcGIS endpoints. Lookups are sub-100ms spatial joins, not live API calls. An ingestion pipeline refreshes the data periodically.

## Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI, async SQLAlchemy, GeoAlchemy2 |
| Frontend | TypeScript 5.9, React 19, Vite 8, Tailwind CSS 4 |
| Map | MapLibre GL JS, Martin vector tile server, OSM raster base |
| Database | PostgreSQL 17 + PostGIS |
| LLM | OpenAI (gpt-5.4-mini), structured output, citation whitelist |
| Deployment | Railway (all 4 services) |

## Project structure

```
backend/           Python API + rules engine + LLM service
  app/
    routers/       HTTP endpoints (parcels, home)
    services/      Business logic (parcel_service, rules_engine, llm_service)
    data/          Hardcoded zone rules (~15 residential zone classes)
    models/        SQLAlchemy ORM (Parcel with PostGIS geometry)
    schemas/       Pydantic response models
  tests/           pytest suite (rules engine, LLM service)

frontend/          React SPA
  src/
    components/    App, Map, SearchBar, AssessmentPanel, HomePanel
    hooks/         useParcelSearch (debounced, abort-safe)
    lib/           API client, MapLibre style builder
    types/         TypeScript interfaces (mirrors backend schemas)

ingestion/         Standalone data pipeline
  config.py        ArcGIS endpoint URLs + demo bboxes
  create_tables.py PostGIS schema + indexes (idempotent)
  ingest.py        Resumable ArcGIS pagination
  verify_data.py   Row counts + geometry validation

martin/            Vector tile server (Dockerfile only)
```

## Getting started

### Prerequisites

- Docker + Docker Compose
- Node.js 22+ and pnpm
- Python 3.12+ and uv
- An OpenAI API key (optional — system works without it via fallback)

### Local development

```bash
# 1. Set up environment
cp .env.example .env
# Edit .env to add OPENAI_API_KEY if you have one

# 2. Start database, Martin, and backend
docker compose up

# 3. Seed the database (first time only)
cd ingestion
uv sync
uv run python create_tables.py
uv run python ingest.py
cd ..

# 4. Start the frontend
cd frontend
pnpm install
pnpm dev
```

The frontend runs at `http://localhost:5173`, backend at `http://localhost:8000`, Martin at `http://localhost:3001`.

### Environment variables

**Backend** (set in `.env`, consumed by Docker Compose):

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | `postgresql+psycopg://postgres:postgres@db/regulation_engine` | Database connection |
| `OPENAI_API_KEY` | *(empty)* | OpenAI credentials. Empty = deterministic fallback |
| `OPENAI_MODEL` | `gpt-4.1-mini` | Model slug. Production uses `gpt-5.4-mini-2026-03-17` |
| `MARTIN_URL` | `http://martin:3000` | Martin tile server |

**Frontend** (Vite build-time):

| Variable | Default | Purpose |
|----------|---------|---------|
| `VITE_API_URL` | `http://localhost:8000` | Backend API URL |
| `VITE_MARTIN_URL` | `http://localhost:3001` | Martin tile server URL |

## API

All endpoints are unauthenticated.

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Health check (`{"status": "ok", "db": true}`) |
| `GET /api/home` | Homepage metadata, featured parcels, supported zones |
| `GET /api/parcels/search?q=<query>` | Search by address (ILIKE) or APN (exact). Returns up to 10 results. |
| `GET /api/parcels/{ain}` | Full parcel assessment: zoning, standards, overlays, ADU, confidence, LLM summary |

The detail response (`/api/parcels/{ain}`) returns a `ParcelDetail` object with 9 sections: parcel facts, scope, zoning, overlays, development standards, ADU assessment, confidence, assessment summary, and metadata.

## Testing

```bash
# Backend (57 tests — rules engine, LLM service, home API)
cd backend && pytest

# Frontend (infrastructure configured, no tests yet)
cd frontend && pnpm test

# Lint + format check
cd backend && ruff check . && ruff format --check .
cd frontend && pnpm ci
```

## Deployment

All 4 services run on Railway:

| Service | Source | Notes |
|---------|--------|-------|
| **PostgreSQL + PostGIS** | Railway managed DB | Data persists across deploys |
| **Martin** | `martin/Dockerfile` | Auto-serves PostGIS tables as vector tiles |
| **Backend** | `backend/Dockerfile` | FastAPI on uvicorn |
| **Frontend** | `frontend/Dockerfile` | Vite build → nginx (SPA routing) |

GitHub auto-deploy is available via Railway's native integration — no CI pipeline needed. See [docs/deployment.md](docs/deployment.md).

## Coverage and limitations

**Supported:** ~15 residential zone classes (R1, R2, R3, R4, R5, RD1.5, RD2, RD3, RS, RA, RE9, RE11, RE15, RE20, RE40) covering ~95% of LA City residential parcels.

**Not supported:** Commercial/industrial zones, Chapter 1A (Downtown), hillside/fire overlays. These return a Low confidence assessment with a "review manually" note.

**Building footprints** are demo-only for Silver Lake, Venice, and Eagle Rock. Other neighborhoods show parcels and zoning layers but no building outlines.

## Docs

| Document | What it covers |
|----------|---------------|
| [Product overview](docs/product-overview.md) | Deep-dive: architecture, data flow, core concepts, key patterns, gotchas |
| [Architecture decisions](docs/decisions.md) | ADRs: why PostGIS bulk seed, deterministic-first, curated rules, Railway |
| [Data sources](docs/DATA_SOURCES.md) | All 8 ArcGIS endpoints, field mappings, ingestion strategy, edge cases |
| [Deployment](docs/deployment.md) | Railway GitHub auto-deploy setup (per-service configuration) |
