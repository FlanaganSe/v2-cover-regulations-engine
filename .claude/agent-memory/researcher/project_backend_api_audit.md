---
name: backend_api_audit
description: Complete audit of all backend API endpoints, schemas, services, and data layer as of March 2026. Use this to avoid re-reading every file when doing frontend or integration work.
type: project
---

Full audit written to `.claude/plans/research-backend-api.md`.

Key facts to carry forward:

**Endpoints (4 total):**
- `GET /health` — DB ping, always 200
- `GET /api/home` — HomeMetadata: supported zones (14), sources (8 fixed), featured parcels (0–4 by category)
- `GET /api/parcels/search?q=` — list[ParcelSearchResult]; empty q returns []; APN regex or address ILIKE
- `GET /api/parcels/{ain}` — ParcelDetail; 404 if AIN missing

**Why:** Used to drive the frontend redesign — no guessing at field names or null handling.

**How to apply:** When building frontend components, reference this audit for exact field types, nullable fields, and formula-string setbacks. Setback fields are `str | None` (not numbers) because some contain formulas like "5+1/st".

**Critical type notes:**
- `height_ft` / `stories` are `null` for R4 / R5 (unlimited)
- `lot_sqft` is `float` (not int)
- All setback fields are `str | None` — may contain formulas
- `data_as_of` can be null if ingest_metadata is empty
- `assessment.llm_available` distinguishes LLM vs fallback text
- `confidence.level` is one of "High" | "Medium" | "Low" (not an enum, just a string)

**MARTIN_URL** is configured but never called by the backend. Frontend hits Martin directly at localhost:3001.

**No auth.** CORS is open (*).

**Zone rule data is hardcoded** in `backend/app/data/zone_rules.py`. 14 zones. Changes require code deploys.
