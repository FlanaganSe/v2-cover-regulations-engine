"""Parcel API endpoints: search, detail, and assessment."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.schemas.parcel import Assessment, ParcelDetail, ParcelSearchResult
from app.services.parcel_service import (
    get_parcel_assessment,
    get_parcel_detail,
    get_parcel_facts,
    search_parcels,
)

router = APIRouter(prefix="/api/parcels", tags=["parcels"])


@router.get("/search", response_model=list[ParcelSearchResult])
async def search(
    q: str = Query("", min_length=0, description="Address or APN"),
    session: AsyncSession = Depends(get_session),
) -> list[ParcelSearchResult]:
    """Search parcels by address text or APN/AIN."""
    return await search_parcels(session, q)


@router.get("/{ain}/facts", response_model=ParcelDetail)
async def facts(
    ain: str,
    session: AsyncSession = Depends(get_session),
) -> ParcelDetail:
    """Fast parcel detail: facts, zoning, overlays, standards — no LLM."""
    result = await get_parcel_facts(session, ain)
    if result is None:
        raise HTTPException(status_code=404, detail="Parcel not found")
    return result


@router.get("/{ain}/assessment", response_model=Assessment)
async def assessment(
    ain: str,
    session: AsyncSession = Depends(get_session),
) -> Assessment:
    """LLM assessment for a parcel (slower)."""
    result = await get_parcel_assessment(session, ain)
    if result is None:
        raise HTTPException(status_code=404, detail="Parcel not found")
    return result


@router.get("/{ain}", response_model=ParcelDetail)
async def detail(
    ain: str,
    session: AsyncSession = Depends(get_session),
) -> ParcelDetail:
    """Full parcel detail: facts, zoning, overlays, standards, confidence."""
    result = await get_parcel_detail(session, ain)
    if result is None:
        raise HTTPException(status_code=404, detail="Parcel not found")
    return result
