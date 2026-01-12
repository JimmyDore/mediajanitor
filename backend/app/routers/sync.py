"""Sync router for data sync endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import User, get_db
from app.services.auth import get_current_user
from app.services.jellyfin import get_user_jellyfin_settings
from app.services.sync import run_user_sync, get_sync_status

router = APIRouter(prefix="/api/sync", tags=["sync"])


class SyncResponse(BaseModel):
    """Response model for sync operation."""

    status: str
    media_items_synced: int
    requests_synced: int
    error: str | None = None


class SyncStatusResponse(BaseModel):
    """Response model for sync status."""

    last_synced: str | None
    status: str | None
    media_items_count: int | None = None
    requests_count: int | None = None
    error: str | None = None


@router.post("", response_model=SyncResponse)
async def trigger_sync(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SyncResponse:
    """
    Trigger a data sync for the current user.

    Fetches data from Jellyfin and Jellyseerr (if configured)
    and caches it in the database.
    """
    # Check if Jellyfin is configured
    settings = await get_user_jellyfin_settings(db, current_user.id)
    if not settings or not settings.jellyfin_server_url or not settings.jellyfin_api_key_encrypted:
        raise HTTPException(
            status_code=400,
            detail="Jellyfin connection not configured. Please configure it in Settings first.",
        )

    # Run the sync
    result = await run_user_sync(db, current_user.id)

    return SyncResponse(
        status=result["status"],
        media_items_synced=result["media_items_synced"],
        requests_synced=result["requests_synced"],
        error=result.get("error"),
    )


@router.get("/status", response_model=SyncStatusResponse)
async def get_user_sync_status(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SyncStatusResponse:
    """Get the sync status for the current user."""
    sync_status = await get_sync_status(db, current_user.id)

    if not sync_status:
        return SyncStatusResponse(
            last_synced=None,
            status=None,
        )

    return SyncStatusResponse(
        last_synced=(
            sync_status.last_sync_completed.isoformat()
            if sync_status.last_sync_completed
            else None
        ),
        status=sync_status.last_sync_status,
        media_items_count=sync_status.media_items_count,
        requests_count=sync_status.requests_count,
        error=sync_status.last_sync_error,
    )
