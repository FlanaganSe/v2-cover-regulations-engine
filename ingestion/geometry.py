"""Geometry preprocessing: GeoJSON → valid 2D WKB hex for PostGIS COPY."""

import json
import logging

import shapely
import shapely.geometry

logger = logging.getLogger(__name__)


def preprocess_geometry(
    geojson: dict[str, object] | None,
    *,
    target_type: str = "MultiPolygon",
) -> str | None:
    """Convert GeoJSON geometry dict to valid 2D WKB hex with SRID 4326.

    Returns None if geometry is null or cannot be processed.
    target_type controls coercion: "MultiPolygon" wraps Polygon → MultiPolygon,
    "Polygon" extracts single polygon from MultiPolygon if possible.
    """
    if not geojson:
        return None

    try:
        geom = shapely.from_geojson(json.dumps(geojson))
    except Exception:
        logger.warning("Failed to parse GeoJSON geometry")
        return None

    if geom is None or geom.is_empty:
        return None

    geom = shapely.make_valid(geom)
    geom = shapely.force_2d(geom)

    # Coerce to target geometry type
    if target_type == "MultiPolygon" and geom.geom_type == "Polygon":
        geom = shapely.geometry.MultiPolygon([geom])
    elif target_type == "MultiPolygon" and geom.geom_type == "GeometryCollection":
        # Extract polygons from geometry collection (make_valid can produce these)
        polygons = [
            g for g in geom.geoms if g.geom_type in ("Polygon", "MultiPolygon")
        ]
        if not polygons:
            return None
        parts = []
        for p in polygons:
            if p.geom_type == "MultiPolygon":
                parts.extend(p.geoms)
            else:
                parts.append(p)
        geom = shapely.geometry.MultiPolygon(parts)
    elif target_type == "Polygon" and geom.geom_type == "MultiPolygon":
        # Take the largest polygon
        if len(geom.geoms) == 0:
            return None
        geom = max(geom.geoms, key=lambda g: g.area)
    elif target_type == "Polygon" and geom.geom_type == "GeometryCollection":
        polygons = [g for g in geom.geoms if g.geom_type == "Polygon"]
        if not polygons:
            return None
        geom = max(polygons, key=lambda g: g.area)

    geom = shapely.set_srid(geom, 4326)
    wkb_hex: str = shapely.to_wkb(geom, hex=True, include_srid=True)
    return wkb_hex
