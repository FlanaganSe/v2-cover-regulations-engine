"""Parcel search and spatial join service."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.parcel import (
    Adu,
    Assessment,
    ConfidenceResponse,
    Metadata,
    OverlayRef,
    Overlays,
    ParcelDetail,
    ParcelFacts,
    ParcelSearchResult,
    Scope,
    Standards,
    Zoning,
)
from app.services.llm_service import build_fallback_assessment, generate_assessment
from app.services.rules_engine import (
    compute_confidence,
    get_adu_assessment,
    get_effective_far,
    lookup_zone_rule,
    parse_zone_string,
)

if TYPE_CHECKING:
    from app.data.zone_rules import AduRules, ZoneRule
    from app.services.rules_engine import Confidence, ParsedZone

_APN_PATTERN = re.compile(r"^\d{4}-\d{3}-\d{3}$|^\d{10}$")

_SQM_TO_SQFT = 10.7639

# ── Search ───────────────────────────────────────────────────────

_SEARCH_BY_AIN = text("""
    SELECT p.ain, p.apn, p.address, z.zone_class
    FROM parcels p
    LEFT JOIN LATERAL (
        SELECT zone_class FROM zoning z
        WHERE ST_Intersects(z.geom, p.geom)
        ORDER BY ST_Area(
            ST_Intersection(z.geom, p.geom)::geography
        ) DESC
        LIMIT 1
    ) z ON true
    WHERE p.ain = :ain
    LIMIT 1
""")

_SEARCH_BY_ADDRESS = text("""
    SELECT p.ain, p.apn, p.address, z.zone_class
    FROM parcels p
    LEFT JOIN LATERAL (
        SELECT zone_class FROM zoning z
        WHERE ST_Intersects(z.geom, p.geom)
        ORDER BY ST_Area(
            ST_Intersection(z.geom, p.geom)::geography
        ) DESC
        LIMIT 1
    ) z ON true
    WHERE p.address ILIKE '%' || :q || '%'
    ORDER BY p.address
    LIMIT 10
""")


async def search_parcels(
    session: AsyncSession,
    query: str,
) -> list[ParcelSearchResult]:
    """Search parcels by address text or APN/AIN."""
    q = query.strip()
    if not q:
        return []

    if _APN_PATTERN.match(q):
        ain = q.replace("-", "")
        result = await session.execute(_SEARCH_BY_AIN, {"ain": ain})
    else:
        result = await session.execute(_SEARCH_BY_ADDRESS, {"q": q})

    return [
        ParcelSearchResult(
            ain=row.ain,
            apn=row.apn,
            address=row.address,
            zone_class=row.zone_class,
        )
        for row in result
    ]


# ── Spatial join detail ──────────────────────────────────────────

_DETAIL_QUERY = text("""
    SELECT
        p.ain, p.apn, p.address, p.situs_city,
        p.use_code, p.use_description,
        p.year_built, p.bedrooms, p.sqft_main,
        p.land_value, p.improvement_value,
        p.center_lat, p.center_lon,
        ST_Area(p.geom::geography) AS lot_area_sqm,
        z.zone_cmplt, z.zone_class,
        sp.name AS specific_plan_name,
        sp.nla_url AS specific_plan_url,
        h.name AS hpoz_name,
        h.nla_url AS hpoz_url,
        cpa.name AS community_plan,
        gplu.gplu_desc AS general_plan_lu,
        EXISTS(
            SELECT 1 FROM city_boundaries cb
            WHERE cb.city_name = 'Los Angeles'
            AND ST_Intersects(cb.geom, p.geom)
        ) AS in_la_city
    FROM parcels p
    LEFT JOIN LATERAL (
        SELECT zone_cmplt, zone_class
        FROM zoning z
        WHERE ST_Intersects(z.geom, p.geom)
        ORDER BY ST_Area(
            ST_Intersection(z.geom, p.geom)::geography
        ) DESC
        LIMIT 1
    ) z ON true
    LEFT JOIN LATERAL (
        SELECT sp.name, sp.nla_url
        FROM specific_plans sp
        WHERE ST_Intersects(sp.geom, p.geom)
        ORDER BY ST_Area(
            ST_Intersection(sp.geom, p.geom)::geography
        ) DESC
        LIMIT 1
    ) sp ON true
    LEFT JOIN LATERAL (
        SELECT h.name, h.nla_url
        FROM hpoz h
        WHERE ST_Intersects(h.geom, p.geom)
        ORDER BY ST_Area(
            ST_Intersection(h.geom, p.geom)::geography
        ) DESC
        LIMIT 1
    ) h ON true
    LEFT JOIN LATERAL (
        SELECT cpa.name
        FROM community_plan_areas cpa
        WHERE ST_Intersects(cpa.geom, p.geom)
        ORDER BY ST_Area(
            ST_Intersection(cpa.geom, p.geom)::geography
        ) DESC
        LIMIT 1
    ) cpa ON true
    LEFT JOIN LATERAL (
        SELECT gplu.gplu_desc
        FROM general_plan_lu gplu
        WHERE ST_Intersects(gplu.geom, p.geom)
        ORDER BY ST_Area(
            ST_Intersection(gplu.geom, p.geom)::geography
        ) DESC
        LIMIT 1
    ) gplu ON true
    WHERE p.ain = :ain
    LIMIT 1
""")

_METADATA_QUERY = text("""
    SELECT
        MIN(retrieved_at) AS oldest,
        MAX(retrieved_at) AS newest
    FROM ingest_metadata
""")


def _row_to_dict(row: Any) -> dict[str, Any]:
    """Convert a SQLAlchemy Row to a dict."""
    return dict(row._mapping)


@dataclass(frozen=True)
class _ParcelContext:
    """Intermediate context needed for both fast and LLM paths."""

    detail: ParcelDetail
    parsed_zone: ParsedZone
    zone_rule: ZoneRule | None
    confidence: Confidence
    overlays: Overlays
    adu_rules: AduRules
    effective_far: float | None
    parcel_facts: ParcelFacts


async def _build_parcel_context(
    session: AsyncSession,
    ain: str,
) -> _ParcelContext | None:
    """Build parcel detail with deterministic fallback assessment."""
    result = await session.execute(_DETAIL_QUERY, {"ain": ain})
    row = result.first()
    if row is None:
        return None

    d = _row_to_dict(row)

    lot_sqm: float | None = d["lot_area_sqm"]
    lot_sqft = lot_sqm * _SQM_TO_SQFT if lot_sqm else None

    # Parse zone string
    parsed = parse_zone_string(
        d["zone_cmplt"],
        community_plan=d["community_plan"],
    )

    # Rule lookup
    zone_rule = lookup_zone_rule(parsed.zone_class)
    effective_far = get_effective_far(
        parsed.zone_class, parsed.height_district, zone_rule
    )

    # Confidence
    conf = compute_confidence(
        parsed,
        zone_rule,
        specific_plan_name=d["specific_plan_name"],
        hpoz_name=d["hpoz_name"],
    )

    # ADU
    adu_rules = get_adu_assessment(parsed.zone_class)

    # Scope
    in_la = bool(d["in_la_city"])
    supported = zone_rule is not None
    chapter_1a = parsed.is_chapter_1a

    # Overlays
    sp_overlay = None
    if d["specific_plan_name"]:
        sp_overlay = OverlayRef(
            name=d["specific_plan_name"],
            url=d["specific_plan_url"],
        )
    hpoz_overlay = None
    if d["hpoz_name"]:
        hpoz_overlay = OverlayRef(
            name=d["hpoz_name"],
            url=d["hpoz_url"],
        )

    overlays = Overlays(
        specific_plan=sp_overlay,
        hpoz=hpoz_overlay,
        community_plan=d["community_plan"],
        general_plan_lu=d["general_plan_lu"],
    )

    parcel_facts = ParcelFacts(
        ain=d["ain"],
        apn=d["apn"],
        address=d["address"],
        center_lat=d["center_lat"],
        center_lon=d["center_lon"],
        lot_sqft=round(lot_sqft, 1) if lot_sqft else None,
        year_built=d["year_built"],
        use_description=d["use_description"],
        bedrooms=d["bedrooms"],
        sqft_main=d["sqft_main"],
    )

    # Deterministic fallback assessment (fast)
    assessment = build_fallback_assessment(
        parsed, zone_rule, conf, adu_rules, effective_far
    )

    # Metadata
    meta_result = await session.execute(_METADATA_QUERY)
    meta_row = meta_result.first()
    data_as_of: datetime | None = None
    if meta_row and meta_row.newest:
        data_as_of = meta_row.newest

    source_urls: list[str] = []
    if zone_rule and zone_rule.source_url:
        source_urls.append(zone_rule.source_url)

    detail = ParcelDetail(
        parcel=parcel_facts,
        scope=Scope(
            in_la_city=in_la,
            supported_zone=supported,
            chapter_1a=chapter_1a,
        ),
        zoning=Zoning(
            zone_string=d["zone_cmplt"],
            zone_class=parsed.zone_class,
            height_district=parsed.height_district or None,
            q_flag=parsed.q_flag,
            d_flag=parsed.d_flag,
            t_flag=parsed.t_flag,
            suffixes=list(parsed.suffixes),
        ),
        overlays=overlays,
        standards=Standards(
            height_ft=zone_rule.max_height_ft if zone_rule else None,
            stories=zone_rule.max_stories if zone_rule else None,
            far_or_rfa=effective_far,
            far_type=zone_rule.far_type if zone_rule else None,
            front_setback_ft=(zone_rule.front_setback_ft if zone_rule else None),
            side_setback_ft=(zone_rule.side_setback_ft if zone_rule else None),
            rear_setback_ft=(zone_rule.rear_setback_ft if zone_rule else None),
            density_description=(zone_rule.density_description if zone_rule else None),
            allowed_uses=(list(zone_rule.allowed_uses) if zone_rule else []),
        ),
        adu=Adu(
            allowed=adu_rules.allowed,
            max_sqft=adu_rules.max_sqft,
            setbacks_ft=adu_rules.setbacks_ft,
            notes=adu_rules.notes,
        ),
        confidence=ConfidenceResponse(
            level=conf.level,
            reasons=list(conf.reasons),
        ),
        assessment=assessment,
        metadata=Metadata(
            data_as_of=data_as_of,
            source_urls=source_urls,
        ),
    )

    return _ParcelContext(
        detail=detail,
        parsed_zone=parsed,
        zone_rule=zone_rule,
        confidence=conf,
        overlays=overlays,
        adu_rules=adu_rules,
        effective_far=effective_far,
        parcel_facts=parcel_facts,
    )


async def get_parcel_facts(
    session: AsyncSession,
    ain: str,
) -> ParcelDetail | None:
    """Fast parcel detail with deterministic assessment (no LLM)."""
    ctx = await _build_parcel_context(session, ain)
    return ctx.detail if ctx else None


async def get_parcel_assessment(
    session: AsyncSession,
    ain: str,
) -> Assessment | None:
    """LLM assessment for a parcel (slow). Returns None if parcel not found."""
    ctx = await _build_parcel_context(session, ain)
    if ctx is None:
        return None
    return await generate_assessment(
        parcel=ctx.parcel_facts,
        parsed_zone=ctx.parsed_zone,
        zone_rule=ctx.zone_rule,
        confidence=ctx.confidence,
        overlays=ctx.overlays,
        adu=ctx.adu_rules,
        effective_far=ctx.effective_far,
    )


async def get_parcel_detail(
    session: AsyncSession,
    ain: str,
) -> ParcelDetail | None:
    """Full parcel detail with LLM assessment (backward compatible)."""
    ctx = await _build_parcel_context(session, ain)
    if ctx is None:
        return None
    assessment = await generate_assessment(
        parcel=ctx.parcel_facts,
        parsed_zone=ctx.parsed_zone,
        zone_rule=ctx.zone_rule,
        confidence=ctx.confidence,
        overlays=ctx.overlays,
        adu=ctx.adu_rules,
        effective_far=ctx.effective_far,
    )
    return ctx.detail.model_copy(update={"assessment": assessment})


__all__ = [
    "get_parcel_assessment",
    "get_parcel_detail",
    "get_parcel_facts",
    "search_parcels",
]
