"""Pydantic response schemas for homepage metadata."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class HomeSource(BaseModel):
    id: str
    label: str
    source_url: str | None = None
    coverage_note: str


class FeaturedParcel(BaseModel):
    category: Literal["clean_supported", "multifamily", "specific_plan", "hpoz"]
    label: str
    description: str
    ain: str
    apn: str | None = None
    address: str | None = None
    zone_class: str | None = None


class HomeMetadata(BaseModel):
    data_as_of: datetime | None = None
    supported_zone_classes: list[str]
    sources: list[HomeSource]
    featured_parcels: list[FeaturedParcel]


__all__ = ["FeaturedParcel", "HomeMetadata", "HomeSource"]
