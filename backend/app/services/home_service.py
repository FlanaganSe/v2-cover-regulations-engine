"""Homepage metadata service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Final

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.zone_rules import CHAPTER_1A_CPA, ZONE_RULES
from app.schemas.home import FeaturedParcel, HomeMetadata, HomeSource

_SOURCE_ORDER: Final[tuple[str, ...]] = (
    "parcels",
    "zoning",
    "specific_plans",
    "hpoz",
    "community_plan_areas",
    "general_plan_lu",
    "city_boundaries",
    "buildings",
)


@dataclass(frozen=True)
class _SourceDescriptor:
    label: str
    coverage_note: str


_SOURCE_DESCRIPTORS: Final[dict[str, _SourceDescriptor]] = {
    "parcels": _SourceDescriptor(
        label="LA County Parcels",
        coverage_note=(
            "Parcel geometry, addresses, and property facts "
            "filtered to LA City parcels."
        ),
    ),
    "zoning": _SourceDescriptor(
        label="NavigateLA Zoning",
        coverage_note=(
            "Primary zoning layer used to determine base zone class and zone string."
        ),
    ),
    "specific_plans": _SourceDescriptor(
        label="Specific Plans",
        coverage_note=(
            "Specific plan intersections are flagged because "
            "additional standards may apply."
        ),
    ),
    "hpoz": _SourceDescriptor(
        label="HPOZ",
        coverage_note=(
            "Historic preservation overlay intersections are flagged for design review."
        ),
    ),
    "community_plan_areas": _SourceDescriptor(
        label="Community Plan Areas",
        coverage_note="Used for community-plan context and Chapter 1A detection.",
    ),
    "general_plan_lu": _SourceDescriptor(
        label="General Plan Land Use",
        coverage_note="Used as policy context alongside the zoning assessment.",
    ),
    "city_boundaries": _SourceDescriptor(
        label="City Boundaries",
        coverage_note=(
            "Used to confirm whether the parcel is inside the City of Los Angeles."
        ),
    ),
    "buildings": _SourceDescriptor(
        label="LARIAC Buildings",
        coverage_note=(
            "Building footprints are seeded only for demo neighborhoods: "
            "Silver Lake, Venice, and Eagle Rock."
        ),
    ),
}

_FEATURED_COPY: Final[dict[str, tuple[str, str]]] = {
    "clean_supported": (
        "Clean supported parcel",
        "A straightforward parcel in the curated rule set "
        "with no specific plan or HPOZ overlay.",
    ),
    "multifamily": (
        "Multi-family example",
        "A parcel in a multi-family residential zone to compare denser-use standards.",
    ),
    "specific_plan": (
        "Specific plan example",
        "A parcel where the base zoning must be read with a specific plan overlay.",
    ),
    "hpoz": (
        "HPOZ example",
        "A parcel with historic preservation review requirements.",
    ),
}

_METADATA_QUERY = text(
    """
    SELECT MAX(retrieved_at) AS data_as_of
    FROM ingest_metadata
    """
)

_LATEST_SOURCES_QUERY = text(
    """
    SELECT DISTINCT ON (table_name)
        table_name,
        source_url
    FROM ingest_metadata
    WHERE table_name IN :table_names
    ORDER BY table_name, retrieved_at DESC
    """
).bindparams(bindparam("table_names", expanding=True))

_ZONING_LATERAL_SQL = """
    LEFT JOIN LATERAL (
        SELECT zone_class
        FROM zoning z
        WHERE ST_Intersects(z.geom, p.geom)
        ORDER BY ST_Area(
            ST_Intersection(z.geom, p.geom)::geography
        ) DESC
        LIMIT 1
    ) z ON true
"""

_CLEAN_SUPPORTED_QUERY = text(
    f"""
    SELECT p.ain, p.apn, p.address, z.zone_class
    FROM parcels p
    {_ZONING_LATERAL_SQL}
    WHERE p.address IS NOT NULL
      AND z.zone_class IN :supported_zones
      AND NOT EXISTS (
          SELECT 1
          FROM specific_plans sp
          WHERE ST_Intersects(sp.geom, p.geom)
      )
      AND NOT EXISTS (
          SELECT 1
          FROM hpoz h
          WHERE ST_Intersects(h.geom, p.geom)
      )
      AND NOT EXISTS (
          SELECT 1
          FROM community_plan_areas cpa
          WHERE cpa.name IN :chapter_1a_cpa
            AND ST_Intersects(cpa.geom, p.geom)
      )
    ORDER BY p.address
    LIMIT 5
    """
).bindparams(
    bindparam("supported_zones", expanding=True),
    bindparam("chapter_1a_cpa", expanding=True),
)

_MULTIFAMILY_QUERY = text(
    f"""
    SELECT p.ain, p.apn, p.address, z.zone_class
    FROM parcels p
    {_ZONING_LATERAL_SQL}
    WHERE p.address IS NOT NULL
      AND z.zone_class IN :multifamily_zones
    ORDER BY p.address
    LIMIT 5
    """
).bindparams(bindparam("multifamily_zones", expanding=True))

_SPECIFIC_PLAN_QUERY = text(
    f"""
    SELECT p.ain, p.apn, p.address, z.zone_class
    FROM parcels p
    {_ZONING_LATERAL_SQL}
    WHERE p.address IS NOT NULL
      AND EXISTS (
          SELECT 1
          FROM specific_plans sp
          WHERE ST_Intersects(sp.geom, p.geom)
      )
    ORDER BY p.address
    LIMIT 5
    """
)

_HPOZ_QUERY = text(
    f"""
    SELECT p.ain, p.apn, p.address, z.zone_class
    FROM parcels p
    {_ZONING_LATERAL_SQL}
    WHERE p.address IS NOT NULL
      AND EXISTS (
          SELECT 1
          FROM hpoz h
          WHERE ST_Intersects(h.geom, p.geom)
      )
    ORDER BY p.address
    LIMIT 5
    """
)


def _build_sources(
    latest_sources: dict[str, str | None],
) -> list[HomeSource]:
    return [
        HomeSource(
            id=source_id,
            label=_SOURCE_DESCRIPTORS[source_id].label,
            source_url=latest_sources.get(source_id),
            coverage_note=_SOURCE_DESCRIPTORS[source_id].coverage_note,
        )
        for source_id in _SOURCE_ORDER
    ]


async def _run_candidate_query(
    session: AsyncSession,
    query: Any,
    params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    result = await session.execute(query, params or {})
    return [dict(row._mapping) for row in result]


def _build_featured_parcel(
    category: str,
    row: dict[str, Any],
) -> FeaturedParcel:
    label, description = _FEATURED_COPY[category]
    return FeaturedParcel(
        category=category,
        label=label,
        description=description,
        ain=row["ain"],
        apn=row["apn"],
        address=row["address"],
        zone_class=row["zone_class"],
    )


async def _collect_featured_parcels(session: AsyncSession) -> list[FeaturedParcel]:
    supported_zones = sorted(ZONE_RULES)
    excluded_ains: set[str] = set()
    featured: list[FeaturedParcel] = []

    query_specs: tuple[tuple[str, Any, dict[str, Any]], ...] = (
        (
            "clean_supported",
            _CLEAN_SUPPORTED_QUERY,
            {
                "supported_zones": supported_zones,
                "chapter_1a_cpa": sorted(CHAPTER_1A_CPA),
            },
        ),
        (
            "multifamily",
            _MULTIFAMILY_QUERY,
            {
                "multifamily_zones": ["RD1.5", "RD2", "RD3", "R3", "R4", "R5"],
            },
        ),
        ("specific_plan", _SPECIFIC_PLAN_QUERY, {}),
        ("hpoz", _HPOZ_QUERY, {}),
    )

    for category, query, params in query_specs:
        rows = await _run_candidate_query(session, query, params)
        match = next((row for row in rows if row["ain"] not in excluded_ains), None)
        if match is None:
            continue
        featured.append(_build_featured_parcel(category, match))
        excluded_ains.add(match["ain"])

    return featured


async def get_home_metadata(session: AsyncSession) -> HomeMetadata:
    """Return homepage metadata, provenance, and featured parcels."""
    metadata_result = await session.execute(_METADATA_QUERY)
    data_as_of: datetime | None = metadata_result.scalar_one_or_none()

    latest_sources_result = await session.execute(
        _LATEST_SOURCES_QUERY,
        {"table_names": list(_SOURCE_ORDER)},
    )
    latest_sources = {row.table_name: row.source_url for row in latest_sources_result}

    featured_parcels = await _collect_featured_parcels(session)

    return HomeMetadata(
        data_as_of=data_as_of,
        supported_zone_classes=sorted(ZONE_RULES),
        sources=_build_sources(latest_sources),
        featured_parcels=featured_parcels,
    )


__all__ = ["get_home_metadata"]
