---
name: data_layer_overview
description: Complete data schema inventory — backend Pydantic models, frontend TS types, DB tables, zone rules, API endpoints
type: project
---

The data layer is fully mapped and tightly aligned (no mismatches between backend and frontend).

**3 REST endpoints:** `GET /api/home`, `GET /api/parcels/search?q=`, `GET /api/parcels/{ain}`

**Root response type:** `ParcelDetail` — assembles 9 sub-schemas: `ParcelFacts`, `Scope`, `Zoning`, `Overlays`, `Standards`, `Adu`, `ConfidenceResponse`, `Assessment`, `Metadata`

**All backend Pydantic models live in:**
- `backend/app/schemas/parcel.py` (ParcelDetail hierarchy)
- `backend/app/schemas/home.py` (HomeMetadata hierarchy)

**All frontend TS types live in:**
- `frontend/src/types/assessment.ts` (mirrors parcel.py exactly)
- `frontend/src/types/home.ts` (mirrors home.py, extends ParcelSearchResult)

**Static zone rule pack:** `backend/app/data/zone_rules.py` — 15 residential zones (RA through R5), hardcoded from LAMC PDF. `min_lot_area_sqft` is in ZoneRule but NOT surfaced in the API response.

**DB schema defined in:** `ingestion/create_tables.py` — no SQL migration files, drop-and-recreate only. 8 tables: parcels, zoning, specific_plans, hpoz, community_plan_areas, general_plan_lu, city_boundaries, buildings, ingest_metadata.

**OpenAPI snapshot:** `docs/openapi.json` — must regenerate after schema changes.

**Why:** Full schema research done 2026-03-27 to inform new UI work.
**How to apply:** When building new UI components, all consumable data fields are documented in `.claude/plans/research-data-schemas.md`. No schema changes needed for basic display work.
