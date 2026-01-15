"""Info endpoints for non-issue data (Recently Available)."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import User, get_db
from app.models.content import (
    RecentlyAvailableResponse,
)
from app.services.auth import get_current_user
from app.services.content import (
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
