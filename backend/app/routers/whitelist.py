"""Whitelist API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import User, get_db
from app.models.content import (
    WhitelistAddRequest,
    WhitelistAddResponse,
    WhitelistListResponse,
    WhitelistRemoveResponse,
)
from app.services.auth import get_current_user
from app.services.content import (
    add_to_whitelist,
    get_whitelist,
    remove_from_whitelist,
    add_to_french_only_whitelist,
    get_french_only_whitelist,
    remove_from_french_only_whitelist,
    add_to_language_exempt_whitelist,
    get_language_exempt_whitelist,
    remove_from_language_exempt_whitelist,
)


router = APIRouter(prefix="/api/whitelist", tags=["whitelist"])


@router.get("/content", response_model=WhitelistListResponse)
async def list_content_whitelist(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WhitelistListResponse:
    """Get all items in the user's content whitelist."""
    return await get_whitelist(db=db, user_id=current_user.id)


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


@router.delete("/content/{whitelist_id}", response_model=WhitelistRemoveResponse)
async def remove_content_from_whitelist(
    whitelist_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WhitelistRemoveResponse:
    """Remove an item from the user's content whitelist.

    After removal, the content may reappear in the old/unwatched content list.
    """
    removed = await remove_from_whitelist(
        db=db,
        user_id=current_user.id,
        whitelist_id=whitelist_id,
    )

    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Whitelist entry not found",
        )

    return WhitelistRemoveResponse(message="Removed from whitelist")


# French-Only Whitelist endpoints (US-5.2)


@router.get("/french-only", response_model=WhitelistListResponse)
async def list_french_only_whitelist(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WhitelistListResponse:
    """Get all items in the user's french-only whitelist.

    Items in this whitelist are exempt from missing English audio checks.
    """
    return await get_french_only_whitelist(db=db, user_id=current_user.id)


@router.post("/french-only", response_model=WhitelistAddResponse, status_code=status.HTTP_201_CREATED)
async def add_to_french_only(
    request: WhitelistAddRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WhitelistAddResponse:
    """Add content to the user's french-only whitelist.

    Items in this whitelist are exempt from missing English audio checks.
    Use this for French-language films that don't need English audio.
    """
    try:
        await add_to_french_only_whitelist(
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
        message="Added to french-only whitelist",
        jellyfin_id=request.jellyfin_id,
        name=request.name,
    )


@router.delete("/french-only/{whitelist_id}", response_model=WhitelistRemoveResponse)
async def remove_from_french_only(
    whitelist_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WhitelistRemoveResponse:
    """Remove an item from the user's french-only whitelist.

    After removal, the content may reappear in language issues if it's missing English audio.
    """
    removed = await remove_from_french_only_whitelist(
        db=db,
        user_id=current_user.id,
        whitelist_id=whitelist_id,
    )

    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Whitelist entry not found",
        )

    return WhitelistRemoveResponse(message="Removed from french-only whitelist")


# Language-Exempt Whitelist endpoints (US-5.3)


@router.get("/language-exempt", response_model=WhitelistListResponse)
async def list_language_exempt_whitelist(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WhitelistListResponse:
    """Get all items in the user's language-exempt whitelist.

    Items in this whitelist are exempt from ALL language checks.
    """
    return await get_language_exempt_whitelist(db=db, user_id=current_user.id)


@router.post("/language-exempt", response_model=WhitelistAddResponse, status_code=status.HTTP_201_CREATED)
async def add_to_language_exempt(
    request: WhitelistAddRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WhitelistAddResponse:
    """Add content to the user's language-exempt whitelist.

    Items in this whitelist are exempt from ALL language checks.
    Use this for content that should never flag language issues.
    """
    try:
        await add_to_language_exempt_whitelist(
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
        message="Added to language-exempt whitelist",
        jellyfin_id=request.jellyfin_id,
        name=request.name,
    )


@router.delete("/language-exempt/{whitelist_id}", response_model=WhitelistRemoveResponse)
async def remove_from_language_exempt(
    whitelist_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WhitelistRemoveResponse:
    """Remove an item from the user's language-exempt whitelist.

    After removal, the content may reappear in language issues if it has language problems.
    """
    removed = await remove_from_language_exempt_whitelist(
        db=db,
        user_id=current_user.id,
        whitelist_id=whitelist_id,
    )

    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Whitelist entry not found",
        )

    return WhitelistRemoveResponse(message="Removed from language-exempt whitelist")
