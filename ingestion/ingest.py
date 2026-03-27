"""Main ingestion pipeline: ArcGIS REST → PostGIS for all 8 GIS layers.

Usage:
    uv run python ingest.py [--database-url URL]

If --database-url is not provided, reads from DATABASE_URL env var.
"""

import argparse
import asyncio
import logging
import os
import sys
from typing import Any

import psycopg

from arcgis_client import (
    clear_checkpoint,
    fetch_layer,
    is_layer_complete,
    mark_layer_complete,
    reset_layer_checkpoint,
)
from config import DEMO_BBOXES, ENDPOINTS, PAGE_SIZES
from geometry import preprocess_geometry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# -- Field extraction helpers --


def _safe_int(val: Any) -> int | None:
    """Cast to int, returning None for empty/invalid values."""
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def _safe_float(val: Any) -> float | None:
    """Cast to float, returning None for empty/invalid values."""
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _safe_str(val: Any) -> str | None:
    """Return stripped string or None for empty values."""
    if val is None:
        return None
    s = str(val).strip()
    return s if s else None


def _prefix_nla_url(val: Any) -> str | None:
    """Prefix relative NLA_URL with base domain."""
    s = _safe_str(val)
    if s is None:
        return None
    if s.startswith("http"):
        return s
    return f"https://maps.lacity.org/{s.lstrip('/')}"


# -- Row extractors per layer --


def _extract_parcels(feature: dict[str, Any]) -> tuple[Any, ...] | None:
    """Extract parcel row from GeoJSON feature."""
    props = feature.get("properties", {})
    geom_json = feature.get("geometry")

    ain = _safe_str(props.get("AIN"))
    if not ain or ain == " ":
        return None

    wkb = preprocess_geometry(geom_json, target_type="MultiPolygon")
    if wkb is None:
        return None

    return (
        ain,
        _safe_str(props.get("APN")),
        _safe_str(props.get("SitusFullAddress")),
        _safe_str(props.get("SitusCity")),
        _safe_str(props.get("SitusZIP")),
        _safe_str(props.get("UseCode")),
        _safe_str(props.get("UseDescription")),
        _safe_int(props.get("YearBuilt1")),
        _safe_int(props.get("Bedrooms1")),
        _safe_int(props.get("SQFTmain1")),
        _safe_float(props.get("Roll_LandValue")),
        _safe_float(props.get("Roll_ImpValue")),
        _safe_float(props.get("CENTER_LAT")),
        _safe_float(props.get("CENTER_LON")),
        wkb,
    )


def _extract_zoning(feature: dict[str, Any]) -> tuple[Any, ...] | None:
    props = feature.get("properties", {})
    geom_json = feature.get("geometry")
    wkb = preprocess_geometry(geom_json, target_type="MultiPolygon")
    if wkb is None:
        return None
    return (
        _safe_str(props.get("ZONE_CMPLT")),
        _safe_str(props.get("ZONE_CLASS")),
        _safe_str(props.get("ZONE_CODE")),
        _safe_str(props.get("ZONE_UNDER")),
        _safe_str(props.get("ZONING_DESCRIPTION")),
        _safe_str(props.get("TOOLTIP")),
        wkb,
    )


def _extract_specific_plans(feature: dict[str, Any]) -> tuple[Any, ...] | None:
    props = feature.get("properties", {})
    geom_json = feature.get("geometry")
    name = _safe_str(props.get("NAME"))
    if not name:
        return None
    wkb = preprocess_geometry(geom_json, target_type="MultiPolygon")
    if wkb is None:
        return None
    return (name, _prefix_nla_url(props.get("NLA_URL")), wkb)


def _extract_hpoz(feature: dict[str, Any]) -> tuple[Any, ...] | None:
    props = feature.get("properties", {})
    geom_json = feature.get("geometry")
    name = _safe_str(props.get("NAME"))
    if not name:
        return None
    wkb = preprocess_geometry(geom_json, target_type="MultiPolygon")
    if wkb is None:
        return None
    return (name, _prefix_nla_url(props.get("NLA_URL")), wkb)


def _extract_community_plan_areas(
    feature: dict[str, Any],
) -> tuple[Any, ...] | None:
    props = feature.get("properties", {})
    geom_json = feature.get("geometry")
    name = _safe_str(props.get("NAME_ALF"))
    if not name:
        return None
    wkb = preprocess_geometry(geom_json, target_type="MultiPolygon")
    if wkb is None:
        return None
    return (_safe_str(props.get("CPA_NUM")), name, wkb)


def _extract_general_plan_lu(feature: dict[str, Any]) -> tuple[Any, ...] | None:
    props = feature.get("properties", {})
    geom_json = feature.get("geometry")
    wkb = preprocess_geometry(geom_json, target_type="MultiPolygon")
    if wkb is None:
        return None
    return (
        _safe_str(props.get("GPLU_DESC")),
        _safe_str(props.get("LU_LABEL")),
        _safe_str(props.get("GENERALIZE")),
        _safe_str(props.get("CPA")),
        wkb,
    )


def _extract_city_boundaries(feature: dict[str, Any]) -> tuple[Any, ...] | None:
    props = feature.get("properties", {})
    geom_json = feature.get("geometry")
    city_name = _safe_str(props.get("CITY_NAME"))
    if not city_name:
        return None
    wkb = preprocess_geometry(geom_json, target_type="MultiPolygon")
    if wkb is None:
        return None
    return (city_name, _safe_str(props.get("FEAT_TYPE")), wkb)


def _extract_buildings(feature: dict[str, Any]) -> tuple[Any, ...] | None:
    props = feature.get("properties", {})
    geom_json = feature.get("geometry")
    wkb = preprocess_geometry(geom_json, target_type="Polygon")
    if wkb is None:
        return None
    return (
        _safe_str(props.get("CODE")),
        _safe_float(props.get("HEIGHT")),
        _safe_float(props.get("AREA")),
        _safe_str(props.get("STATUS")),
        wkb,
    )


# -- COPY column specs per table --

LAYER_CONFIG: dict[str, dict[str, Any]] = {
    "city_boundaries": {
        "columns": "(city_name, feat_type, geom)",
        "extract": _extract_city_boundaries,
        "where": "FEAT_TYPE='Land'",
        "endpoint": ENDPOINTS["city_boundaries"],
        "page_size": PAGE_SIZES["city_boundaries"],
    },
    "parcels": {
        "columns": (
            "(ain, apn, address, situs_city, situs_zip, use_code, use_description,"
            " year_built, bedrooms, sqft_main, land_value, improvement_value,"
            " center_lat, center_lon, geom)"
        ),
        "extract": _extract_parcels,
        "where": "SitusCity LIKE '%LOS ANGELES%' AND AIN IS NOT NULL AND AIN <> ' '",
        "endpoint": ENDPOINTS["parcels"],
        "page_size": PAGE_SIZES["parcels"],
    },
    "zoning": {
        "columns": (
            "(zone_cmplt, zone_class, zone_code, zone_under,"
            " zoning_description, tooltip, geom)"
        ),
        "extract": _extract_zoning,
        "where": "1=1",
        "endpoint": ENDPOINTS["zoning"],
        "page_size": PAGE_SIZES["zoning"],
    },
    "specific_plans": {
        "columns": "(name, nla_url, geom)",
        "extract": _extract_specific_plans,
        "where": "1=1",
        "endpoint": ENDPOINTS["specific_plans"],
        "page_size": PAGE_SIZES["specific_plans"],
    },
    "hpoz": {
        "columns": "(name, nla_url, geom)",
        "extract": _extract_hpoz,
        "where": "1=1",
        "endpoint": ENDPOINTS["hpoz"],
        "page_size": PAGE_SIZES["hpoz"],
    },
    "community_plan_areas": {
        "columns": "(cpa_num, name, geom)",
        "extract": _extract_community_plan_areas,
        "where": "1=1",
        "endpoint": ENDPOINTS["community_plan_areas"],
        "page_size": PAGE_SIZES["community_plan_areas"],
    },
    "general_plan_lu": {
        "columns": "(gplu_desc, lu_label, generalize, cpa, geom)",
        "extract": _extract_general_plan_lu,
        "where": "1=1",
        "endpoint": ENDPOINTS["general_plan_lu"],
        "page_size": PAGE_SIZES["general_plan_lu"],
    },
    "buildings": {
        "columns": "(code, height, area, status, geom)",
        "extract": _extract_buildings,
        "where": "CODE='Building'",
        "endpoint": ENDPOINTS["buildings"],
        "page_size": PAGE_SIZES["buildings"],
    },
}

# Ingestion order: city_boundaries first (needed for parcel post-filter)
LAYER_ORDER = [
    "city_boundaries",
    "parcels",
    "zoning",
    "specific_plans",
    "hpoz",
    "community_plan_areas",
    "general_plan_lu",
    "buildings",
]


def _copy_rows(
    conn: psycopg.Connection[Any],
    table: str,
    columns: str,
    rows: list[tuple[Any, ...]],
) -> int:
    """Bulk-load rows into a table using psycopg3 COPY protocol."""
    sql = f"COPY {table} {columns} FROM STDIN"
    with conn.cursor() as cur:
        with cur.copy(sql) as copy:
            for row in rows:
                copy.write_row(row)
    conn.commit()
    return len(rows)


def _post_filter_parcels(conn: psycopg.Connection[Any]) -> int:
    """Remove parcels outside LA City via spatial intersection."""
    logger.info("Post-filtering parcels to LA City only...")
    with conn.cursor() as cur:
        cur.execute(
            """
            DELETE FROM parcels
            WHERE id NOT IN (
                SELECT p.id
                FROM parcels p
                JOIN city_boundaries cb ON ST_Intersects(p.geom, cb.geom)
                WHERE cb.city_name = 'Los Angeles'
            )
            """
        )
        deleted = cur.rowcount
    conn.commit()
    logger.info("Removed %d parcels outside LA City", deleted)
    return deleted


def _log_provenance(
    conn: psycopg.Connection[Any],
    table_name: str,
    source_url: str,
    filter_used: str,
    row_count: int,
) -> None:
    """Insert provenance record into ingest_metadata."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ingest_metadata (table_name, source_url, filter_used, row_count)
            VALUES (%s, %s, %s, %s)
            """,
            (table_name, source_url, filter_used, row_count),
        )
    conn.commit()


def _analyze_tables(conn: psycopg.Connection[Any]) -> None:
    """Run ANALYZE on all tables to update query planner stats."""
    old_autocommit = conn.autocommit
    conn.autocommit = True
    with conn.cursor() as cur:
        for table in LAYER_ORDER:
            cur.execute(f"ANALYZE {table}")  # noqa: S608
            logger.info("ANALYZE %s", table)
    conn.autocommit = old_autocommit


async def _fetch_buildings() -> list[dict[str, Any]]:
    """Fetch buildings from all 3 demo bounding boxes."""
    all_features: list[dict[str, Any]] = []
    for bbox_name, bbox in DEMO_BBOXES.items():
        envelope = {
            "xmin": bbox["xmin"],
            "ymin": bbox["ymin"],
            "xmax": bbox["xmax"],
            "ymax": bbox["ymax"],
            "spatialReference": {"wkid": 4326},
        }
        logger.info("Fetching buildings for %s...", bbox_name)
        features = await fetch_layer(
            ENDPOINTS["buildings"],
            page_size=PAGE_SIZES["buildings"],
            where="CODE='Building'",
            geometry_filter=envelope,
            layer_name=f"buildings_{bbox_name}",
        )
        all_features.extend(features)
    # Mark buildings as complete (per-bbox keys are separate)
    mark_layer_complete("buildings")
    return all_features


async def run_ingestion(database_url: str) -> None:
    """Ingest all GIS layers into PostGIS."""
    conn = psycopg.connect(database_url)

    try:
        # Clear ingest_metadata only for layers we'll re-ingest
        for tbl in LAYER_ORDER:
            if not is_layer_complete(tbl):
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM ingest_metadata WHERE table_name = %s",
                        (tbl,),
                    )
        conn.commit()

        for table_name in LAYER_ORDER:
            config = LAYER_CONFIG[table_name]

            # Skip layers already completed (checkpoint/resume)
            if is_layer_complete(table_name):
                logger.info("=== Skipping %s (already complete) ===", table_name)
                continue

            logger.info("=== Ingesting %s ===", table_name)

            # Truncate table + reset checkpoint for idempotent re-runs
            with conn.cursor() as cur:
                cur.execute(f"TRUNCATE {table_name} RESTART IDENTITY CASCADE")  # noqa: S608
            conn.commit()
            reset_layer_checkpoint(table_name)

            # Fetch features
            if table_name == "buildings":
                features = await _fetch_buildings()
            else:
                features = await fetch_layer(
                    config["endpoint"],
                    page_size=config["page_size"],
                    where=config["where"],
                    layer_name=table_name,
                )

            # Extract and transform rows
            extract_fn = config["extract"]
            rows: list[tuple[Any, ...]] = []
            skipped = 0
            for f in features:
                row = extract_fn(f)
                if row is not None:
                    rows.append(row)
                else:
                    skipped += 1

            if skipped > 0:
                logger.info(
                    "%s: skipped %d features (null geometry or filtered)",
                    table_name,
                    skipped,
                )

            # Bulk COPY
            if rows:
                loaded = _copy_rows(conn, table_name, config["columns"], rows)
                logger.info("%s: loaded %d rows", table_name, loaded)
            else:
                logger.warning("%s: no rows to load!", table_name)

            # Log provenance
            _log_provenance(
                conn,
                table_name,
                config["endpoint"]
                if table_name != "buildings"
                else ENDPOINTS["buildings"],
                config["where"],
                len(rows),
            )

        # Post-processing
        _post_filter_parcels(conn)

        # Update parcel count in provenance
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM parcels")
            result = cur.fetchone()
            parcel_count = result[0] if result else 0
            cur.execute(
                "UPDATE ingest_metadata SET row_count = %s"
                " WHERE table_name = 'parcels'",
                (parcel_count,),
            )
        conn.commit()

        # ANALYZE all tables
        _analyze_tables(conn)

        # Clear checkpoint on success
        clear_checkpoint()

        logger.info("=== Ingestion complete ===")

    finally:
        conn.close()


def _parse_args() -> str:
    parser = argparse.ArgumentParser(description="Ingest GIS data into PostGIS")
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL", ""))
    args = parser.parse_args()
    url: str = args.database_url
    if not url:
        print("Provide --database-url or set DATABASE_URL env var")
        sys.exit(1)
    return url


def main() -> None:
    url = _parse_args()
    asyncio.run(run_ingestion(url))


if __name__ == "__main__":
    main()
