"""Content analysis API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import User, get_db
from app.models.content import OldUnwatchedResponse
from app.services.auth import get_current_user
from app.services.content import get_old_unwatched_content


router = APIRouter(prefix="/api/content", tags=["content"])


@router.get("/old-unwatched", response_model=OldUnwatchedResponse)
async def get_old_unwatched(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OldUnwatchedResponse:
    """Get list of old/unwatched content for the current user.

    Returns content that:
    - Has never been watched AND was added more than 3 months ago
    - Was last watched more than 4 months ago

    Content in the user's whitelist is excluded.
    Results are sorted by size (largest first).
    """
    return await get_old_unwatched_content(db, current_user.id)
