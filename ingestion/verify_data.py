"""Post-ingestion verification: row counts, geometry checks, spatial queries.

Usage:
    uv run python verify_data.py [--database-url URL]

Returns exit code 0 on all checks passing, 1 on any failure.
"""

import argparse
import os
import sys
from typing import Any

import psycopg

EXPECTED_COUNTS: dict[str, tuple[int, int]] = {
    "city_boundaries": (1, 400),
    "parcels": (450_000, 800_000),
    "zoning": (56_000, 62_000),
    "specific_plans": (25, 70),
    "hpoz": (25, 45),
    "community_plan_areas": (30, 45),
    "general_plan_lu": (47_000, 58_000),
    "buildings": (1_000, 60_000),
}

SPATIAL_TABLES = [
    "parcels",
    "zoning",
    "specific_plans",
    "hpoz",
    "community_plan_areas",
    "general_plan_lu",
    "city_boundaries",
    "buildings",
]

EXPECTED_INDEXES = [
    "idx_parcels_geom",
    "idx_zoning_geom",
    "idx_specific_plans_geom",
    "idx_hpoz_geom",
    "idx_community_plan_areas_geom",
    "idx_general_plan_lu_geom",
    "idx_city_boundaries_geom",
    "idx_buildings_geom",
    "idx_parcels_ain",
    "idx_parcels_address_trgm",
    "idx_zoning_zone_class",
    "idx_city_boundaries_name",
]


def _check(
    name: str,
    passed: bool,
    detail: str = "",
) -> bool:
    status = "PASS" if passed else "FAIL"
    msg = f"  [{status}] {name}"
    if detail:
        msg += f" — {detail}"
    print(msg)
    return passed


def check_row_counts(conn: psycopg.Connection[Any]) -> bool:
    """Check each table has rows within expected range."""
    print("\n--- Row Counts ---")
    all_ok = True
    with conn.cursor() as cur:
        for table, (lo, hi) in EXPECTED_COUNTS.items():
            cur.execute(f"SELECT COUNT(*) FROM {table}")  # noqa: S608
            result = cur.fetchone()
            count = result[0] if result else 0
            ok = lo <= count <= hi
            all_ok = _check(
                f"{table}: {count} rows",
                ok,
                f"expected {lo}–{hi}",
            ) and all_ok
    return all_ok


def check_geometry_validity(conn: psycopg.Connection[Any]) -> bool:
    """Check all geometries are valid."""
    print("\n--- Geometry Validity ---")
    all_ok = True
    with conn.cursor() as cur:
        for table in SPATIAL_TABLES:
            cur.execute(
                f"SELECT COUNT(*) FROM {table}"  # noqa: S608
                " WHERE NOT ST_IsValid(geom)"
            )
            result = cur.fetchone()
            invalid = result[0] if result else 0
            all_ok = _check(
                f"{table}: {invalid} invalid",
                invalid == 0,
            ) and all_ok
    return all_ok


def check_geometry_srid(conn: psycopg.Connection[Any]) -> bool:
    """Check all geometries have SRID 4326."""
    print("\n--- Geometry SRID ---")
    all_ok = True
    with conn.cursor() as cur:
        for table in SPATIAL_TABLES:
            cur.execute(
                f"SELECT DISTINCT ST_SRID(geom) FROM {table}"  # noqa: S608
            )
            srids = [row[0] for row in cur.fetchall()]
            ok = srids == [4326]
            all_ok = _check(
                f"{table}: SRID {srids}",
                ok,
                "expected [4326]",
            ) and all_ok
    return all_ok


def check_no_3d(conn: psycopg.Connection[Any]) -> bool:
    """Check no 3D geometries exist."""
    print("\n--- No 3D Geometries ---")
    all_ok = True
    with conn.cursor() as cur:
        for table in SPATIAL_TABLES:
            cur.execute(
                f"SELECT COUNT(*) FROM {table}"  # noqa: S608
                " WHERE ST_NDims(geom) > 2"
            )
            result = cur.fetchone()
            count_3d = result[0] if result else 0
            all_ok = _check(
                f"{table}: {count_3d} 3D geometries",
                count_3d == 0,
            ) and all_ok
    return all_ok


def check_indexes(conn: psycopg.Connection[Any]) -> bool:
    """Check all expected indexes exist."""
    print("\n--- Indexes ---")
    all_ok = True
    with conn.cursor() as cur:
        cur.execute(
            "SELECT indexname FROM pg_indexes"
            " WHERE schemaname = 'public'"
        )
        existing = {row[0] for row in cur.fetchall()}
    for idx in EXPECTED_INDEXES:
        all_ok = _check(
            f"index {idx}",
            idx in existing,
        ) and all_ok
    return all_ok


def check_spatial_query(conn: psycopg.Connection[Any]) -> bool:
    """Spot-check: pick a parcel and verify it joins to a zoning polygon."""
    print("\n--- Sample Spatial Query ---")
    with conn.cursor() as cur:
        # Pick a parcel with a known address
        cur.execute(
            "SELECT ain, address FROM parcels"
            " WHERE address IS NOT NULL LIMIT 1"
        )
        result = cur.fetchone()
        if not result:
            return _check("sample parcel exists", False)
        ain, address = result[0], result[1]
        _check("sample parcel", True, f"AIN={ain}, {address}")

        # Join to zoning
        cur.execute(
            """
            SELECT z.zone_class
            FROM parcels p
            JOIN zoning z ON ST_Intersects(p.geom, z.geom)
            WHERE p.ain = %s
            LIMIT 1
            """,
            (ain,),
        )
        zone_result = cur.fetchone()
        zone_class = zone_result[0] if zone_result else None
        return _check(
            "parcel → zoning join",
            zone_class is not None,
            f"zone_class={zone_class}",
        )


def check_provenance(conn: psycopg.Connection[Any]) -> bool:
    """Check ingest_metadata has a row for every loaded table."""
    print("\n--- Provenance ---")
    with conn.cursor() as cur:
        cur.execute("SELECT table_name, row_count FROM ingest_metadata")
        metadata = {row[0]: row[1] for row in cur.fetchall()}
    all_ok = True
    for table in SPATIAL_TABLES:
        ok = table in metadata
        all_ok = _check(
            f"provenance for {table}",
            ok,
            f"row_count={metadata.get(table)}",
        ) and all_ok
    return all_ok


def check_parcels_in_la(conn: psycopg.Connection[Any]) -> bool:
    """Spot-check: verify no parcels exist outside LA City."""
    print("\n--- Parcels in LA City ---")
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(*) FROM parcels p
            WHERE NOT EXISTS (
                SELECT 1 FROM city_boundaries cb
                WHERE cb.city_name = 'Los Angeles'
                AND ST_Intersects(p.geom, cb.geom)
            )
            """
        )
        result = cur.fetchone()
        outside = result[0] if result else 0
    return _check(
        f"parcels outside LA City: {outside}",
        outside == 0,
    )


def verify_all(database_url: str) -> bool:
    """Run all verification checks. Returns True if all pass."""
    conn = psycopg.connect(database_url)
    try:
        results = [
            check_row_counts(conn),
            check_geometry_validity(conn),
            check_geometry_srid(conn),
            check_no_3d(conn),
            check_indexes(conn),
            check_spatial_query(conn),
            check_provenance(conn),
            check_parcels_in_la(conn),
        ]
        all_passed = all(results)
        print(
            f"\n{'=' * 40}\n"
            f"{'ALL CHECKS PASSED' if all_passed else 'SOME CHECKS FAILED'}\n"
            f"{'=' * 40}"
        )
        return all_passed
    finally:
        conn.close()


def _parse_args() -> str:
    parser = argparse.ArgumentParser(
        description="Verify ingested GIS data",
    )
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL", ""),
    )
    args = parser.parse_args()
    url: str = args.database_url
    if not url:
        print("Provide --database-url or set DATABASE_URL env var")
        sys.exit(1)
    return url


def main() -> None:
    url = _parse_args()
    ok = verify_all(url)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
