"""Async paginated ArcGIS REST API client with retry and checkpoint."""

import asyncio
import json
import logging
import ssl
from pathlib import Path
from typing import Any

import aiohttp
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

CHECKPOINT_FILE = Path(__file__).parent / "checkpoint.json"
MAX_CONCURRENT = 6


def _load_checkpoint() -> dict[str, Any]:
    if CHECKPOINT_FILE.exists():
        return json.loads(CHECKPOINT_FILE.read_text())  # type: ignore[no-any-return]
    return {}


def _save_checkpoint(data: dict[str, Any]) -> None:
    CHECKPOINT_FILE.write_text(json.dumps(data, indent=2))


def clear_checkpoint() -> None:
    """Remove checkpoint file after successful full ingestion."""
    if CHECKPOINT_FILE.exists():
        CHECKPOINT_FILE.unlink()


def is_layer_complete(layer_name: str) -> bool:
    """Check if a layer is already marked complete in checkpoint."""
    checkpoint = _load_checkpoint()
    return bool(checkpoint.get(layer_name, {}).get("complete", False))


def reset_layer_checkpoint(layer_name: str) -> None:
    """Reset a layer's checkpoint offset (called when table is truncated)."""
    checkpoint = _load_checkpoint()
    if layer_name in checkpoint:
        del checkpoint[layer_name]
        _save_checkpoint(checkpoint)


@retry(
    stop=stop_after_attempt(8),
    wait=wait_exponential(multiplier=2, min=5, max=120),
    retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
    before_sleep=lambda rs: logger.warning(
        "Retry attempt %d after error: %s",
        rs.attempt_number,
        rs.outcome.exception() if rs.outcome else "unknown",
    ),
)
async def _fetch_page(
    session: aiohttp.ClientSession,
    semaphore: asyncio.Semaphore,
    url: str,
    params: dict[str, str],
) -> dict[str, Any]:
    """Fetch a single page from ArcGIS REST with retry."""
    async with semaphore:
        async with session.get(url, params=params) as resp:
            resp.raise_for_status()
            return await resp.json(content_type=None)  # type: ignore[no-any-return]


async def fetch_layer(
    endpoint: str,
    *,
    page_size: int = 1000,
    where: str = "1=1",
    out_fields: str = "*",
    geometry_filter: dict[str, Any] | None = None,
    layer_name: str = "",
) -> list[dict[str, Any]]:
    """Fetch all features from an ArcGIS REST endpoint with pagination.

    Uses resultOffset pagination with orderByFields=OBJECTID.
    Supports checkpoint/resume via checkpoint.json.
    """
    query_url = f"{endpoint}/query"
    all_features: list[dict[str, Any]] = []
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    # Load checkpoint for resume
    checkpoint = _load_checkpoint()
    start_offset = checkpoint.get(layer_name, {}).get("offset", 0)
    if start_offset > 0:
        logger.info(
            "Resuming %s from offset %d (checkpoint)", layer_name, start_offset
        )

    offset = start_offset
    timeout = aiohttp.ClientTimeout(total=120)
    # Government GIS endpoints often have SSL cert issues
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE
    connector = aiohttp.TCPConnector(ssl=ssl_ctx)

    async with aiohttp.ClientSession(
        timeout=timeout, connector=connector
    ) as session:
        while True:
            params: dict[str, str] = {
                "where": where,
                "outFields": out_fields,
                "outSR": "4326",
                "f": "geojson",
                "resultOffset": str(offset),
                "resultRecordCount": str(page_size),
                "orderByFields": "OBJECTID",
            }
            if geometry_filter:
                params["geometry"] = json.dumps(geometry_filter)
                params["geometryType"] = "esriGeometryEnvelope"
                params["spatialRel"] = "esriSpatialRelIntersects"
                params["inSR"] = "4326"

            data = await _fetch_page(session, semaphore, query_url, params)

            # Check for API error
            if "error" in data:
                raise RuntimeError(
                    f"ArcGIS API error for {layer_name}: {data['error']}"
                )

            features = data.get("features", [])
            exceeded = data.get("properties", {}).get(
                "exceededTransferLimit", False
            )

            # GeoJSON response wraps exceededTransferLimit differently
            if not exceeded:
                exceeded = data.get("exceededTransferLimit", False)

            all_features.extend(features)

            page_count = len(features)
            total_so_far = len(all_features) + start_offset
            logger.info(
                "%s: page at offset %d → %d features (total: %d)",
                layer_name,
                offset,
                page_count,
                total_so_far,
            )

            # Brief pause between requests to avoid overloading the server
            await asyncio.sleep(0.5)

            # Save checkpoint after each page
            checkpoint[layer_name] = {"offset": offset + page_size}
            _save_checkpoint(checkpoint)

            # Dual stop condition
            if not exceeded and (page_count == 0 or page_count < page_size):
                break

            offset += page_size

    # Mark layer complete in checkpoint
    checkpoint[layer_name] = {"complete": True}
    _save_checkpoint(checkpoint)

    logger.info(
        "%s: download complete — %d features total",
        layer_name,
        len(all_features) + start_offset,
    )
    return all_features
