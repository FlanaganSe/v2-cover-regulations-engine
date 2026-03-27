"""Create PostGIS schema for the LA regulation engine.

Idempotent: drops and recreates all tables, extensions, and indexes.
Can run against any PostgreSQL connection string (local Docker or Railway).

Usage:
    uv run python create_tables.py [DATABASE_URL]

If DATABASE_URL is not provided as an argument, reads from the
DATABASE_URL environment variable (psycopg format: postgres://...).
"""

import os
import sys

import psycopg

EXTENSIONS_SQL = """
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
"""

TABLES_SQL = """
DROP TABLE IF EXISTS ingest_metadata CASCADE;
DROP TABLE IF EXISTS buildings CASCADE;
DROP TABLE IF EXISTS city_boundaries CASCADE;
DROP TABLE IF EXISTS general_plan_lu CASCADE;
DROP TABLE IF EXISTS community_plan_areas CASCADE;
DROP TABLE IF EXISTS hpoz CASCADE;
DROP TABLE IF EXISTS specific_plans CASCADE;
DROP TABLE IF EXISTS zoning CASCADE;
DROP TABLE IF EXISTS parcels CASCADE;

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

CREATE TABLE specific_plans (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    nla_url TEXT,
    geom GEOMETRY(MULTIPOLYGON, 4326) NOT NULL
);

CREATE TABLE hpoz (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    nla_url TEXT,
    geom GEOMETRY(MULTIPOLYGON, 4326) NOT NULL
);

CREATE TABLE community_plan_areas (
    id SERIAL PRIMARY KEY,
    cpa_num VARCHAR(10),
    name TEXT NOT NULL,
    geom GEOMETRY(MULTIPOLYGON, 4326) NOT NULL
);

CREATE TABLE general_plan_lu (
    id SERIAL PRIMARY KEY,
    gplu_desc TEXT,
    lu_label VARCHAR(50),
    generalize VARCHAR(50),
    cpa VARCHAR(10),
    geom GEOMETRY(MULTIPOLYGON, 4326) NOT NULL
);

CREATE TABLE city_boundaries (
    id SERIAL PRIMARY KEY,
    city_name VARCHAR(100) NOT NULL,
    feat_type VARCHAR(20),
    geom GEOMETRY(MULTIPOLYGON, 4326) NOT NULL
);

CREATE TABLE buildings (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20),
    height DOUBLE PRECISION,
    area DOUBLE PRECISION,
    status VARCHAR(20),
    geom GEOMETRY(POLYGON, 4326) NOT NULL
);

CREATE TABLE ingest_metadata (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL,
    source_url TEXT NOT NULL,
    filter_used TEXT,
    retrieved_at TIMESTAMPTZ DEFAULT NOW(),
    row_count INTEGER
);
"""

INDEXES_SQL = """
CREATE INDEX idx_parcels_geom ON parcels USING GIST (geom);
CREATE INDEX idx_zoning_geom ON zoning USING GIST (geom);
CREATE INDEX idx_specific_plans_geom ON specific_plans USING GIST (geom);
CREATE INDEX idx_hpoz_geom ON hpoz USING GIST (geom);
CREATE INDEX idx_community_plan_areas_geom ON community_plan_areas USING GIST (geom);
CREATE INDEX idx_general_plan_lu_geom ON general_plan_lu USING GIST (geom);
CREATE INDEX idx_city_boundaries_geom ON city_boundaries USING GIST (geom);
CREATE INDEX idx_buildings_geom ON buildings USING GIST (geom);

CREATE INDEX idx_parcels_ain ON parcels (ain);
CREATE INDEX idx_parcels_address_trgm ON parcels USING GIN (address gin_trgm_ops);
CREATE INDEX idx_zoning_zone_class ON zoning (zone_class);
CREATE INDEX idx_city_boundaries_name ON city_boundaries (city_name);
"""


def get_database_url() -> str:
    """Resolve database URL from CLI arg or environment."""
    if len(sys.argv) > 1:
        return sys.argv[1]
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        print("Usage: python create_tables.py [DATABASE_URL]")
        print("Or set DATABASE_URL environment variable.")
        sys.exit(1)
    return url


def main() -> None:
    """Create all extensions, tables, and indexes."""
    database_url = get_database_url()
    # Normalize SQLAlchemy dialect to libpq format for psycopg
    conn_str = database_url.replace("postgresql+psycopg://", "postgres://")

    with psycopg.connect(conn_str) as conn:
        conn.execute(EXTENSIONS_SQL)
        conn.execute(TABLES_SQL)
        conn.execute(INDEXES_SQL)
        conn.commit()

    print("Schema created successfully.")


if __name__ == "__main__":
    main()
