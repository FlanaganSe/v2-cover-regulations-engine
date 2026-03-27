"""Pydantic response schemas for parcel endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

# ── Search endpoint ──────────────────────────────────────────────


class ParcelSearchResult(BaseModel):
    """Single result from parcel search."""

    model_config = ConfigDict(from_attributes=True)

    ain: str
    apn: str | None = None
    address: str | None = None
    zone_class: str | None = None


# ── Detail endpoint ──────────────────────────────────────────────


class ParcelFacts(BaseModel):
    ain: str
    apn: str | None = None
    address: str | None = None
    center_lat: float | None = None
    center_lon: float | None = None
    lot_sqft: float | None = None
    year_built: int | None = None
    use_description: str | None = None
    bedrooms: int | None = None
    sqft_main: int | None = None


class Scope(BaseModel):
    in_la_city: bool
    supported_zone: bool
    chapter_1a: bool


class Zoning(BaseModel):
    zone_string: str | None = None
    zone_class: str | None = None
    height_district: str | None = None
    q_flag: bool = False
    d_flag: bool = False
    t_flag: bool = False
    suffixes: list[str] = []


class OverlayRef(BaseModel):
    name: str
    url: str | None = None


class Overlays(BaseModel):
    specific_plan: OverlayRef | None = None
    hpoz: OverlayRef | None = None
    community_plan: str | None = None
    general_plan_lu: str | None = None


class Standards(BaseModel):
    height_ft: int | None = None
    stories: int | None = None
    far_or_rfa: float | None = None
    far_type: str | None = None
    front_setback_ft: str | None = None
    side_setback_ft: str | None = None
    rear_setback_ft: str | None = None
    density_description: str | None = None
    allowed_uses: list[str] = []


class Adu(BaseModel):
    allowed: bool
    max_sqft: int
    setbacks_ft: int
    notes: str


class ConfidenceResponse(BaseModel):
    level: str
    reasons: list[str]


class Metadata(BaseModel):
    data_as_of: datetime | None = None
    source_urls: list[str] = []


class ParcelDetail(BaseModel):
    """Full parcel detail response."""

    parcel: ParcelFacts
    scope: Scope
    zoning: Zoning
    overlays: Overlays
    standards: Standards
    adu: Adu
    confidence: ConfidenceResponse
    assessment: None = None  # Placeholder for M4 LLM integration
    metadata: Metadata


__all__ = [
    "Adu",
    "ConfidenceResponse",
    "Metadata",
    "Overlays",
    "OverlayRef",
    "ParcelDetail",
    "ParcelFacts",
    "ParcelSearchResult",
    "Scope",
    "Standards",
    "Zoning",
]
