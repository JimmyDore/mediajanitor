"""Info endpoints for non-issue data (Recently Available, Currently Airing)."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import User, get_db
from app.models.content import (
    CurrentlyAiringResponse,
    RecentlyAvailableResponse,
)
from app.services.auth import get_current_user
from app.services.content import (
    get_currently_airing,
    get_recently_available,
)


router = APIRouter(prefix="/api/info", tags=["info"])


@router.get("/recent", response_model=RecentlyAvailableResponse)
async def get_recent(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RecentlyAvailableResponse:
    """Get content that became available in the past 7 days.

    Returns items sorted by date, newest first.
    """
    return await get_recently_available(db, current_user.id)


@router.get("/airing", response_model=CurrentlyAiringResponse)
async def get_airing(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CurrentlyAiringResponse:
    """Get series that are currently airing (have in-progress seasons).

    Returns items sorted by next air date.
    """
    return await get_currently_airing(db, current_user.id)
