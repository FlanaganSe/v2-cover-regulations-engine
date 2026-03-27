"""Async paginated ArcGIS REST API client with retry and checkpoint.

Not implemented in M1. Will be built in M2.
"""

from typing import Any


async def fetch_layer(
    endpoint: str,
    page_size: int = 1000,
    where: str = "1=1",
) -> list[dict[str, Any]]:
    """Fetch all features from an ArcGIS REST endpoint with pagination."""
    raise NotImplementedError
