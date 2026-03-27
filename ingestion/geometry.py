"""Geometry preprocessing: GeoJSON → valid 2D WKB for PostGIS.

Not implemented in M1. Will be built in M2.
"""

from shapely import Geometry


def preprocess_geometry(geojson: dict[str, object]) -> bytes:
    """Convert GeoJSON geometry to valid 2D WKB.

    Steps: from_geojson → make_valid → force_2d → to_wkb.
    """
    raise NotImplementedError


def make_valid_2d(geom: Geometry) -> Geometry:
    """Ensure geometry is valid and 2D."""
    raise NotImplementedError
