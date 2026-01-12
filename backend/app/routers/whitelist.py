"""Whitelist API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import User, get_db
from app.models.content import WhitelistAddRequest, WhitelistAddResponse
from app.services.auth import get_current_user
from app.services.content import add_to_whitelist


router = APIRouter(prefix="/api/whitelist", tags=["whitelist"])


@router.post("/content", response_model=WhitelistAddResponse, status_code=status.HTTP_201_CREATED)
async def add_content_to_whitelist(
    request: WhitelistAddRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WhitelistAddResponse:
    """Add content to the user's whitelist.

    This protects the content from appearing in the old/unwatched content list.
    """
    try:
        await add_to_whitelist(
            db=db,
            user_id=current_user.id,
            jellyfin_id=request.jellyfin_id,
            name=request.name,
            media_type=request.media_type,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )

    return WhitelistAddResponse(
        message="Added to whitelist",
        jellyfin_id=request.jellyfin_id,
        name=request.name,
    )
