"""Library API endpoints (US-22.1)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import User, UserSettings, get_db
from app.models.content import LibraryResponse, ServiceUrls
from app.services.auth import get_current_user
from app.services.content import get_library

router = APIRouter(prefix="/api/library", tags=["library"])


async def _get_user_settings(db: AsyncSession, user_id: int) -> UserSettings | None:
    """Get user settings from database."""
    result = await db.execute(select(UserSettings).where(UserSettings.user_id == user_id))
    return result.scalar_one_or_none()


@router.get("", response_model=LibraryResponse)
async def get_library_endpoint(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    type: Annotated[
        str | None,
        Query(description="Filter by type: movie, series, or all (default)"),
    ] = None,
    search: Annotated[
        str | None,
        Query(description="Search by name (case-insensitive)"),
    ] = None,
    watched: Annotated[
        str | None,
        Query(description="Filter by watched status: true, false, or all (default)"),
    ] = None,
    sort: Annotated[
        str,
        Query(description="Sort by: name (default), year, size, date_added, last_watched"),
    ] = "name",
    order: Annotated[
        str,
        Query(description="Sort order: asc (default), desc"),
    ] = "asc",
    min_year: Annotated[
        int | None,
        Query(description="Minimum production year filter"),
    ] = None,
    max_year: Annotated[
        int | None,
        Query(description="Maximum production year filter"),
    ] = None,
    min_size_gb: Annotated[
        float | None,
        Query(description="Minimum size in GB filter"),
    ] = None,
    max_size_gb: Annotated[
        float | None,
        Query(description="Maximum size in GB filter"),
    ] = None,
    page: Annotated[
        int,
        Query(description="Page number (1-indexed), default 1", ge=1),
    ] = 1,
    page_size: Annotated[
        int,
        Query(description="Items per page (1-100), default 50", ge=1, le=100),
    ] = 50,
) -> LibraryResponse:
    """Get cached media items for the current user with pagination.

    Supports filtering by:
    - type: movie, series, or all
    - search: case-insensitive name search
    - watched: true, false, or all
    - min_year/max_year: production year range
    - min_size_gb/max_size_gb: size range in GB

    Supports sorting by:
    - name (default), year, size, date_added, last_watched
    - order: asc (default) or desc

    Supports pagination:
    - page: page number (1-indexed), default 1
    - page_size: items per page (1-100), default 50

    Returns paginated items, total_count (all matching), total_size (all matching),
    pagination info, and service URLs.
    """
    # Get library items with filters, sorting, and pagination
    response = await get_library(
        db=db,
        user_id=current_user.id,
        media_type=type,
        search=search,
        watched=watched,
        sort=sort,
        order=order,
        min_year=min_year,
        max_year=max_year,
        min_size_gb=min_size_gb,
        max_size_gb=max_size_gb,
        page=page,
        page_size=page_size,
    )

    # Add service URLs from user settings
    settings = await _get_user_settings(db, current_user.id)
    response.service_urls = ServiceUrls(
        jellyfin_url=settings.jellyfin_server_url if settings else None,
        jellyseerr_url=settings.jellyseerr_server_url if settings else None,
        radarr_url=settings.radarr_server_url if settings else None,
        sonarr_url=settings.sonarr_server_url if settings else None,
    )

    return response
