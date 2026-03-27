# Data Sources: LA Regulation Engine

Merged from two independent research passes, March 2026. All endpoints verified live.

## Scope

- **City of Los Angeles** residential parcels only
- **Original Code / Chapter 1** zones only (Chapter 1A / Downtown excluded from v1)
- Focus: single-family, ADU, and closely related residential building types
- Overlays are flag-and-cite, not deeply modeled

## What We Need

| # | Source | Role | Ingestion |
|---|--------|------|-----------|
| 1 | LA County Parcels | Parcel geometry, APN/AIN, address, property facts | Seed to PostGIS |
| 2 | LA City Zoning (NavigateLA) | Zoning designation per parcel | Seed to PostGIS |
| 3 | Curated Rule Pack | Development standards per zone class | JSON/table, hand-built |
| 4 | LA County City Boundaries | Jurisdiction check: is this parcel in LA City? | Seed to PostGIS |
| 5 | Specific Plan Areas (NavigateLA) | Flag: specific plan may override base zoning | Seed to PostGIS |
| 6 | HPOZ (NavigateLA) | Flag: historic overlay requires design review | Seed to PostGIS |
| 7 | Community Plan Areas | Context label for planning area | Seed to PostGIS |
| 8 | General Plan Land Use | Policy context, zoning consistency check | Seed to PostGIS |
| 9 | LARIAC Buildings 2020 | Map viz, existing structure context | Seed demo neighborhoods to PostGIS |

Address resolution is a runtime strategy, not a data source. See [Architecture > Runtime Flow](#runtime-flow).

## Supported Decisions (v1)

The rule pack and data sources together must answer these questions for a residential parcel:

1. **Primary dwelling allowed?** — Is the zone residential? What types (single-family, multi-family)?
2. **ADU/JADU likely allowed?** — Based on zone class + ZA Memo 143 standards
3. **Basic envelope constraints** — Max height, max stories, FAR/RFA, setbacks (front/side/rear), min lot area, density
4. **Overlay warnings** — Is the parcel in a specific plan, HPOZ, or other overlay that may alter or override base zoning?

Anything beyond this (commercial use analysis, full building code, conditional use permits) is out of scope for v1.

---

## Core Sources

### 1. LA County Parcels

The parcel system of record. Users search by address or APN; this layer resolves that to a parcel with geometry and property facts.

- **Endpoint:** `https://public.gis.lacounty.gov/public/rest/services/LACounty_Cache/LACounty_Parcel/MapServer/0`
- **Auth:** None
- **MaxRecordCount:** 1,000
- **Total records:** ~2.4M (all LA County; filter to LA City)
- **Key fields:** `AIN`, `APN`, `SitusFullAddress`, `SitusCity`, `SitusZIP`, `UseCode`, `UseDescription`, `YearBuilt1`, `Bedrooms1`, `SQFTmain1`, `Roll_LandValue`, `Roll_ImpValue`, `CENTER_LAT`, `CENTER_LON`

**Gotchas:**
- Use `AIN` as internal key (10-digit, no dashes). Display `APN` (formatted `XXXX-XXX-XXX`) to users.
- Some records have `AIN = " "` (space) and null attributes. Filter: `AIN IS NOT NULL AND AIN <> ' '`.
- `UseCode` 0100 = single-family. 0100-0999 = all residential.
- `where=1=1` without `outSR` or attribute filter returns 400. Always include a filter or `outSR=4326`.
- City GeoHub parcel FeatureServer is dead. County is the only working option.

### 2. LA City Zoning

The foundational zoning layer. `ZONE_CMPLT` encodes base zone + height district + overlays in one string (e.g., `R1-1-HPOZ`, `(F)CM-1-CUGU`). This is how we determine what rules apply.

- **Endpoint:** `https://maps.lacity.org/arcgis/rest/services/Mapping/NavigateLA/MapServer/71`
- **Auth:** None
- **MaxRecordCount:** 20,000 (10x better than alternatives)
- **Key fields:** `ZONE_CMPLT`, `ZONE_CLASS`, `ZONE_CODE`, `ZONE_UNDER`, `ZONING_DESCRIPTION`, `TOOLTIP`

**Why NavigateLA 71, not GeoHub FeatureServer/15:** GeoHub only gives `Zoning` + `CATEGORY` (simplified). NavigateLA gives the full zone string needed to parse height districts, detect Q/D/T conditions, and identify overlay markers. Also 20K records/page vs 2K.

**Gotchas:**
- Parse height district from `ZONE_CMPLT`: `R1-1` means base zone R1, height district 1. FAR comes from the height district, not the base zone.
- Detect condition prefixes in the zone string:
  - `[Q]` = qualified restrictions (parcel-specific ordinance). Flag: "additional restrictions may apply."
  - `D` = FAR limitation. Flag: "reduced FAR may apply."
  - `[T]` = tentative classification. Flag: "may change."
- Chapter 1A zones use a different format (`[MB3-SH1-1][CX3-4][CPIO]`). Detect and return "not yet supported."
- Split-zoned parcels: use polygon intersection + largest-overlap area to assign the primary zone.

### 3. Curated Rule Pack

GIS tells you which zone applies. The rule pack tells you what that zone allows. Without it, zoning designations are just labels.

**Source material:**

| Source | What to extract |
|--------|----------------|
| Zoning Code Summary PDF | Development standards per zone: setbacks, height, FAR, density, lot area, stories, allowed uses |
| ZA Memo 143 | ADU/JADU rules (if ADU is in scope) — cleanest interpretive memo available |
| Zoning Code Manual | Edge-case interpretation policies (selective reference) |

**Source URLs:**
- Summary PDF: `https://planning.lacity.gov/odocument/eadcb225-a16b-4ce6-bc94-c915408c2b04/Zoning_Code_Summary.pdf`
- ZA Memo 143: `https://planning.lacity.gov/odocument/184600d8-71d7-4d74-baf1-1f9cd2603320/ZA_Memo_No_143.pdf`
- Code Manual: `https://docs.ladbs.org/zoning-code-manual-and-commentary`
- LAMC Chapter 1 (reference only): `https://codelibrary.amlegal.com/codes/los_angeles/latest/lapz/0-0-0-57924`

**How to build it:**
- Hardcode a `zone_rules` dict/table for ~15 residential zones: `R1`, `R2`, `RD1.5`, `RE9`, `RE11`, `RE15`, `RE20`, `RS`, `RA`, `R3`, `R4`, `R5`. These cover ~95% of residential parcels.
- Per zone: `min_lot_area_sqft`, `max_height_ft`, `max_stories`, `far`, `front_yard_ft`, `side_yard_ft`, `rear_yard_ft`, `density`, `allowed_uses`.
- Keep source links per rule for citations in the product.
- Do not parse the full LAMC. Do not attempt ICC Building Code (paywalled, wrong abstraction).

**Gotchas:**
- R1 on flat lots uses RFA (0.45 x lot area) under the Baseline Mansionization Ordinance, not standard FAR. Check hillside flag to branch.
- ADU state law (AB 68, SB 13, etc.) preempts local zoning in many ways. ZA Memo 143 is current through Jan 2025 amendments.

### 4. LA County City Boundaries

Confirms the parcel is actually in LA City. Near-zero cost, prevents applying LA City zoning logic to unincorporated county or other cities.

- **Endpoint:** `https://public.gis.lacounty.gov/public/rest/services/LACounty_Dynamic/Political_Boundaries/MapServer/19`
- **Auth:** None
- **Total records:** 347 (load entire dataset in one request)
- **Key field:** `CITY_NAME`
- Filter `FEAT_TYPE='Land'`. Require `CITY_NAME = 'Los Angeles'`.

### 5. Address Resolution

**Strategy:** Parcel text search first. CAMS geocoder as fallback only.

1. **Text search** against `SitusFullAddress` in the parcel table. This is simpler, faster, avoids external API, and returns the actual parcel directly.
2. **CAMS fallback** if text search fails: `https://geocode.gis.lacounty.gov/geocode/rest/services/CAMS_Locator/GeocodeServer`
   - Operations: Geocode, ReverseGeocode, Suggest
   - Auth: None
   - Request `outSR=4326` (native CRS is State Plane feet)
   - After geocoding, find the nearest parcel within a small buffer — do not assume exact point-in-polygon. Geocoder points sometimes land on the street centerline, not the parcel.

The LA City geocoder (`maps.lacity.org`) is offline as of March 2026. Do not depend on it.

---

## Overlay & Context Sources

These are all flag-and-cite. Detect intersection, surface the name and a link, reduce confidence. Do not implement the full rules for any overlay.

### 6. Specific Plan Areas

~35 specific plans that can override base zoning entirely (Hollywood, Venice, Warner Center, etc.).

- **Endpoint:** `https://maps.lacity.org/arcgis/rest/services/Mapping/NavigateLA/MapServer/93`
- **Auth:** None
- **Key fields:** `NAME`, `NLA_URL` (link to plan document)
- On hit: show plan name, link to document, reduce confidence.

### 7. Historic Preservation Overlay Zones (HPOZ)

~34 HPOZs. All new construction and additions require HPOZ Board design review.

- **Endpoint:** `https://maps.lacity.org/arcgis/rest/services/Mapping/NavigateLA/MapServer/75`
- **Auth:** None
- **Key fields:** `NAME`, `NLA_URL`
- On hit: show HPOZ name, state design review required, reduce confidence.

### 8. Community Plan Areas

Cheap planning context. Names the Community Plan Area (e.g., "Silver Lake - Echo Park"). Useful for UI and for detecting Downtown (Chapter 1A exclusion).

- **Endpoint:** `https://services5.arcgis.com/7nsPwEMP38bSkCjy/arcgis/rest/services/Community_Plan_Areas/FeatureServer/0`
- **Key fields:** `CPA_NUM`, `NAME_ALF`

### 9. General Plan Land Use

Policy-level land use designation. Good for context ("Low I Residential") and detecting zoning/policy mismatches.

- **Endpoint:** `https://services5.arcgis.com/7nsPwEMP38bSkCjy/arcgis/rest/services/General_Plan_Land_Use/FeatureServer/1`
- **Key fields:** `GPLU_DESC`, `LU_LABEL`, `GENERALIZE`, `CPA`

### 10. LARIAC Buildings 2020

Building footprint polygons with height and area. Required for the map and useful for lot coverage context.

- **Endpoint:** `https://public.gis.lacounty.gov/public/rest/services/LACounty_Dynamic/LARIAC_Buildings_2020/MapServer/0`
- **Auth:** None
- **MaxRecordCount:** 1,000
- **Total records:** 3.3M (all LA County — do not download all)
- **Key fields:** `CODE`, `HEIGHT`, `AREA`, `STATUS`
- Filter `CODE='Building'` to exclude courtyards/pools.
- **Scoping decision:** Seed a few demo neighborhoods (bounding boxes) during initial ingestion. Full-city background seed can happen later if needed, but is not required for demo.

---

## Architecture

### Data Model

```
parcel_id           -- internal PK
ain                 -- 10-digit parcel key
address             -- SitusFullAddress
parcel_geometry     -- polygon
city_name           -- from boundary check
zoning_string       -- ZONE_CMPLT from NavigateLA
zoning_class        -- ZONE_CLASS (base zone)
zoning_height_dist  -- parsed from ZONE_CMPLT
community_plan_area -- from CPA layer
general_plan_lu     -- from GPLU layer
specific_plan_name  -- nullable
hpoz_name           -- nullable
building_summary    -- footprint count, total area, max height
confidence          -- High / Medium / Low
source_refs[]       -- URLs for citations
```

Optional (time-permitting):
```
hillside_flag
fire_hazard_flag
```

### Ingestion Pattern

All GIS layers follow the same ArcGIS REST pagination pattern: `resultOffset` + `resultRecordCount`, `f=geojson`, `outSR=4326`. Load into PostGIS. Create GIST indexes on all geometry columns.

**CRS:** Standardize on EPSG:4326 during ingestion. Always request `outSR=4326`. Source layers use various CRS (102645, 102100) — never store them natively.

**Provenance:** Each seeded layer should track its source URL, retrieval date, row count, and filter used. This is needed for "data as of" display in the UI and for reproducible re-seeding.

### Runtime Flow

```
User enters address or APN
  |
  +-- APN? --> SELECT * FROM parcels WHERE ain = $1
  |
  +-- Address? --> Text search: SitusFullAddress ILIKE '%..%'
        |
        +-- No match? --> CAMS geocode --> nearest parcel within buffer
  |
  v
Confirm LA City (city_name = 'Los Angeles')
  |
  v
Spatial joins (single query):
  - zoning (polygon intersection, largest overlap)
  - specific plans
  - HPOZ
  - community plan area
  - general plan land use
  - [optional: hillside, fire hazard]
  |
  v
Rules lookup: zone_rules[zone_class] --> setbacks, FAR, height, uses
  |
  v
LLM assessment:
  - Explain deterministic facts in plain language
  - Flag ambiguity when overlays apply or data conflicts
  - Cite specific LAMC sections
  - Score confidence
  |
  v
Frontend: map (parcel + buildings + zoning) + assessment panel
```

### Confidence Strategy

- **High:** Original Code residential zone, no specific plan, no HPOZ, use case directly covered by curated rules
- **Medium:** One overlay flag present, or interpretation requires memo/manual reference
- **Low:** Downtown / Chapter 1A, unmodeled specific plan, HPOZ, conflicting signals

## Test Parcels

The pipeline should be validated against representative parcels covering these categories. Specific addresses/APNs to be identified during ingestion.

| Category | Why it matters |
|----------|---------------|
| Clean R1 (flat lot, no overlays) | Happy path. Should produce High confidence. |
| RE or RS zone | Different lot size / density rules than R1. |
| RD or R3 (multi-family) | Tests density and multi-unit logic. |
| Parcel in HPOZ | Should trigger overlay flag and Medium/Low confidence. |
| Parcel in a Specific Plan | Should trigger overlay flag and reduce confidence. |
| Downtown parcel (Chapter 1A) | Should return "not yet supported." |
| Address that geocodes to street centerline | Tests the text-search-first + buffer fallback. |
| Split-zoned parcel | Tests largest-overlap logic. |
| Parcel outside LA City | Should return "out of scope — different jurisdiction." |

---

## Edge Cases That Matter

| Issue | Mitigation |
|-------|-----------|
| Split-zoned parcels (2+ zoning polygons) | Polygon intersection + largest overlap area. Do not use centroid-only. |
| Geocoder returns street centerline, not parcel | Parcel text search first. CAMS fallback uses nearest-parcel-in-buffer. |
| Downtown parcels (Chapter 1A) | Detect via Community Plan Area = "Downtown" or zone string format. Return "not yet supported." |
| Q/D/T conditions in zone string | Detect prefix, flag to user, do not attempt to resolve. |
| Height district determines FAR, not base zone | Parse from `ZONE_CMPLT` (number after dash). Map to FAR in rules table. |
| R1 Mansionization Ordinance | Flat R1 lots use 0.45 RFA, not standard FAR. Branch on hillside flag. |
| Parcel outside LA City | Check boundary table. Return "out of scope — different jurisdiction." |
| Stale GIS data | Show "data as of [date]" in UI. Acceptable for demo. |

---

## Key Decisions

| Decision | Why |
|----------|-----|
| Bulk PostGIS seed, not live API queries | Eliminates runtime dependency on external APIs. Faster queries. Enables spatial joins. |
| NavigateLA for zoning (layer 71), not GeoHub | Richer schema (ZONE_CMPLT vs just Zoning+CATEGORY). 20K records/page vs 2K. |
| NavigateLA for Specific Plans + HPOZ | Provides `NLA_URL` field linking directly to plan documents for product citations. |
| County parcels, not City parcels | City GeoHub FeatureServer is dead. County has richer attributes. |
| Polygon intersection + largest overlap for zoning | Centroid can fall in wrong polygon for irregularly shaped parcels. |
| Parcel text search before geocoding | Faster, no external API, returns the parcel directly. |
| CAMS geocoder, not LA City geocoder | LA City geocoder is offline. CAMS is verified working. |
| Curated rule pack, not full LAMC parsing | LAMC is enormous cross-referenced legal text with no API. Summary PDF + hardcoded dict covers 95%. |
| Flag overlays, don't implement their rules | ~35 specific plans + 34 HPOZs = too many rule sets. Detect + flag + reduce confidence. |
| Exclude Chapter 1A (Downtown) | Different code, different zone format, <5% of parcels. |

---

## Deferred / Consider Later

These were evaluated and deliberately excluded from v1. Notes for future reference.

**Hillside Ordinance + Grading Area** (NavigateLA layers 352, 353) — Flag-only if time permits. Matters because R1 FAR calculations differ for hillside vs flat lots, and hillside areas trigger grading limits. Low ingestion cost but adds branching to rule logic.

**Fire Hazard Severity Zones** (LA County Hazards MapServer 18/19, or CalFire state data) — Flag-only if time permits. Very High zones trigger Chapter 7A construction standards. Good demo signal post-2025 LA fires, but not core to the zoning/buildability question.

**Coastal Zone** — Would flag CDP requirement for Venice/Palisades/San Pedro parcels. ~1 hour effort. Low priority for residential demo.

**Transit Priority Areas** (SCAG) — Signals parking exemption (AB 2097) and density bonus eligibility. ~1 hour. Nice-to-have.

**Zoning Supplemental Use Districts** (17 separate layers including CPIO, Hillside Construction Regulation District, Residential Floor Area District) — Too many layers, mostly name-only. If Downtown becomes required, CPIO layer is needed. Otherwise skip.

**ZIMAS** — Great manual QA/reference tool. Not a backend data source. Use for validating test parcels and linking out from UI.

**Full LAMC / building code / ICC** — Wrong abstraction for demo. LAMC is enormous, ICC is paywalled. Frame as "additional review required."

**FEMA Flood Zones** — Meaningful but adds complexity without advancing the core zoning question. Defer to post-demo.

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
