"""Homepage metadata endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.schemas.home import HomeMetadata
from app.services.home_service import get_home_metadata

router = APIRouter(prefix="/api", tags=["home"])


@router.get("/home", response_model=HomeMetadata)
async def home(
    session: AsyncSession = Depends(get_session),
) -> HomeMetadata:
    """Return homepage metadata for the root workspace state."""
    return await get_home_metadata(session)
