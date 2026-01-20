"""Sync router for data sync endpoints."""

from datetime import datetime, timezone, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import User, get_db
from app.services.auth import get_current_user
from app.services.jellyfin import get_user_jellyfin_settings
from app.services.sync import get_sync_status, update_sync_status
from app.tasks import sync_user

# Rate limit: max 1 sync per 5 minutes per user
SYNC_RATE_LIMIT_MINUTES = 5

router = APIRouter(prefix="/api/sync", tags=["sync"])


class SyncResponse(BaseModel):
    """Response model for sync operation."""

    status: str
    media_items_synced: int
    requests_synced: int
    error: str | None = None


class SyncProgressInfo(BaseModel):
    """Progress info during an active sync."""

    current_step: str | None = None  # "syncing_media" or "syncing_requests"
    total_steps: int | None = None  # 1 or 2 (Jellyfin only, or Jellyfin + Jellyseerr)
    current_step_progress: int | None = None  # e.g., user 3 of 10
    current_step_total: int | None = None  # e.g., 10 total users
    current_user_name: str | None = None  # e.g., "John"


class SyncStatusResponse(BaseModel):
    """Response model for sync status."""

    last_synced: str | None
    status: str | None
    is_syncing: bool = False  # True when sync is in progress
    media_items_count: int | None = None
    requests_count: int | None = None
    error: str | None = None
    progress: SyncProgressInfo | None = None  # Only present when is_syncing=True


class SyncRequest(BaseModel):
    """Request model for sync operation."""

    force: bool = False  # Bypass rate limit for first sync


@router.post("", response_model=SyncResponse)
async def trigger_sync(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    request: SyncRequest | None = None,
) -> SyncResponse:
    """
    Trigger a data sync for the current user.

    Fetches data from Jellyfin and Jellyseerr (if configured)
    and caches it in the database.

    Rate limited to 1 sync per 5 minutes per user.
    First sync (when user has never synced) bypasses rate limit when force=True.
    """
    # Check rate limit (bypass if force=True and user has never synced)
    sync_status = await get_sync_status(db, current_user.id)
    is_first_sync = sync_status is None or sync_status.last_sync_completed is None
    should_bypass_rate_limit = request and request.force and is_first_sync

    if not should_bypass_rate_limit and sync_status and sync_status.last_sync_started:
        time_since_sync = datetime.now(timezone.utc) - sync_status.last_sync_started.replace(tzinfo=timezone.utc)
        rate_limit = timedelta(minutes=SYNC_RATE_LIMIT_MINUTES)
        if time_since_sync < rate_limit:
            remaining = rate_limit - time_since_sync
            minutes_remaining = int(remaining.total_seconds() // 60) + 1
            raise HTTPException(
                status_code=429,
                detail=f"Rate limited. Please wait {minutes_remaining} minute(s) before syncing again.",
            )

    # Check if Jellyfin is configured
    settings = await get_user_jellyfin_settings(db, current_user.id)
    if not settings or not settings.jellyfin_server_url or not settings.jellyfin_api_key_encrypted:
        raise HTTPException(
            status_code=400,
            detail="Jellyfin connection not configured. Please configure it in Settings first.",
        )

    # Mark sync as started (for rate limiting and status tracking)
    await update_sync_status(db, current_user.id, status="syncing", started=True)

    # Dispatch sync to Celery worker (async, returns immediately)
    sync_user.delay(current_user.id)

    return SyncResponse(
        status="sync_started",
        media_items_synced=0,
        requests_synced=0,
        error=None,
    )


@router.get("/status", response_model=SyncStatusResponse)
async def get_user_sync_status(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SyncStatusResponse:
    """Get the sync status for the current user.

    Returns progress info when a sync is in progress, allowing
    the frontend to poll for updates and display progress.
    """
    sync_status = await get_sync_status(db, current_user.id)

    if not sync_status:
        return SyncStatusResponse(
            last_synced=None,
            status=None,
        )

    # Check if sync is currently in progress
    is_syncing = sync_status.current_step is not None

    # Build progress info if syncing
    progress = None
    if is_syncing:
        progress = SyncProgressInfo(
            current_step=sync_status.current_step,
            total_steps=sync_status.total_steps,
            current_step_progress=sync_status.current_step_progress,
            current_step_total=sync_status.current_step_total,
            current_user_name=sync_status.current_user_name,
        )

    return SyncStatusResponse(
        last_synced=(
            sync_status.last_sync_completed.isoformat()
            if sync_status.last_sync_completed
            else None
        ),
        status=sync_status.last_sync_status,
        is_syncing=is_syncing,
        media_items_count=sync_status.media_items_count,
        requests_count=sync_status.requests_count,
        error=sync_status.last_sync_error,
        progress=progress,
    )
