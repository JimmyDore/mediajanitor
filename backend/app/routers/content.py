"""Content analysis API endpoints."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import CachedJellyseerrRequest, CachedMediaItem, User, UserSettings, get_db
from app.models.content import (
    ContentIssueItem,
    ContentIssuesResponse,
    ContentSummaryResponse,
    DeleteContentRequest,
    DeleteContentResponse,
    DeleteRequestResponse,
    OldUnwatchedResponse,
    ServiceUrls,
)
from app.services.auth import get_current_user
from app.services.content import (
    get_content_issues,
    get_content_summary,
    get_old_unwatched_content,
    get_unavailable_requests,
)
from app.services.jellyseerr import (
    delete_jellyseerr_media,
    get_decrypted_jellyseerr_api_key,
)
from app.services.radarr import (
    delete_movie_by_tmdb_id,
    get_decrypted_radarr_api_key,
)
from app.services.sonarr import (
    delete_series_by_tmdb_id,
    get_decrypted_sonarr_api_key,
    get_sonarr_tmdb_to_slug_map,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/content", tags=["content"])


@router.get("/summary", response_model=ContentSummaryResponse)
async def get_summary(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ContentSummaryResponse:
    """Get summary counts for all issue types.

    Returns counts for:
    - old_content: Old/unwatched content count and total size
    - large_movies: Large movies (>13GB) count and total size
    - language_issues: Content with language issues (placeholder)
    - unavailable_requests: Unavailable Jellyseerr requests (placeholder)
    """
    return await get_content_summary(db, current_user.id)


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


@router.get("/issues", response_model=ContentIssuesResponse)
async def get_issues(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    filter: Annotated[
        str | None,
        Query(description="Filter by issue type: old, large, language, requests"),
    ] = None,
) -> ContentIssuesResponse:
    """Get unified list of all content with issues for the current user.

    Supports filtering by issue type:
    - old: Old/unwatched content (4+ months since last watched)
    - large: Movies larger than 13GB
    - language: Content with language issues
    - requests: Unavailable Jellyseerr requests

    Each item includes a list of all applicable issues.
    Results are sorted by size (largest first) for content, by request date for requests.
    """
    # Get user settings for service URLs
    settings = await _get_user_settings(db, current_user.id)
    service_urls = ServiceUrls(
        jellyfin_url=settings.jellyfin_server_url if settings else None,
        jellyseerr_url=settings.jellyseerr_server_url if settings else None,
        radarr_url=settings.radarr_server_url if settings else None,
        sonarr_url=settings.sonarr_server_url if settings else None,
    )

    # Requests filter converts to unified format
    if filter == "requests":
        request_items = await get_unavailable_requests(db, current_user.id)

        # Build Sonarr TMDB -> titleSlug map for TV show requests
        sonarr_slug_map: dict[int, str] = {}
        if settings and settings.sonarr_server_url and settings.sonarr_api_key_encrypted:
            sonarr_api_key = get_decrypted_sonarr_api_key(settings)
            if sonarr_api_key:
                sonarr_slug_map = await get_sonarr_tmdb_to_slug_map(
                    settings.sonarr_server_url, sonarr_api_key
                )

        # Convert request items to ContentIssueItem format
        unified_items = []
        for req in request_items:
            # Look up Sonarr titleSlug for TV requests
            sonarr_title_slug = None
            if req.media_type == "tv" and req.tmdb_id:
                sonarr_title_slug = sonarr_slug_map.get(req.tmdb_id)

            unified_items.append(
                ContentIssueItem(
                    jellyfin_id=f"request-{req.jellyseerr_id}",  # Use jellyseerr_id with prefix
                    name=req.title,
                    media_type=req.media_type,
                    production_year=None,  # Requests don't have production year
                    size_bytes=None,  # Requests don't have size
                    size_formatted="",
                    last_played_date=None,  # Requests don't have watched date
                    path=None,
                    issues=req.issues,
                    tmdb_id=str(req.tmdb_id) if req.tmdb_id else None,
                    jellyseerr_request_id=req.jellyseerr_id,  # Request items have their own ID
                    sonarr_title_slug=sonarr_title_slug,  # Sonarr link for TV shows
                    # Request-specific fields
                    requested_by=req.requested_by,
                    request_date=req.request_date,
                    missing_seasons=req.missing_seasons,
                    release_date=req.release_date,
                )
            )
        return ContentIssuesResponse(
            items=unified_items,
            total_count=len(unified_items),
            total_size_bytes=0,
            total_size_formatted="0 B",
            service_urls=service_urls,
        )

    response = await get_content_issues(db, current_user.id, filter)
    response.service_urls = service_urls
    return response


# US-15.4, US-15.5, US-15.6: Delete content endpoints


async def _get_user_settings(db: AsyncSession, user_id: int) -> UserSettings | None:
    """Get user settings from database."""
    result = await db.execute(select(UserSettings).where(UserSettings.user_id == user_id))
    return result.scalar_one_or_none()


async def _lookup_jellyseerr_media_by_tmdb(
    db: AsyncSession, user_id: int, tmdb_id: int, media_type: str
) -> int | None:
    """Look up Jellyseerr media ID by TMDB ID and media type.

    Args:
        db: Database session
        user_id: User ID to filter by
        tmdb_id: TMDB ID to search for
        media_type: "movie" or "tv" (lowercase)

    Returns:
        Jellyseerr media ID if found, None otherwise.
        Note: This returns media.id (for deletion), NOT request.id.
    """
    result = await db.execute(
        select(CachedJellyseerrRequest.jellyseerr_media_id)
        .where(CachedJellyseerrRequest.user_id == user_id)
        .where(CachedJellyseerrRequest.tmdb_id == tmdb_id)
        .where(CachedJellyseerrRequest.media_type == media_type)
        .distinct()
        .limit(1)
    )
    row = result.scalar_one_or_none()
    return row


async def _delete_cached_media_by_tmdb_id(db: AsyncSession, user_id: int, tmdb_id: int) -> int:
    """Delete CachedMediaItem by TMDB ID stored in raw_data.ProviderIds.Tmdb.

    Args:
        db: Database session
        user_id: User ID to filter by
        tmdb_id: TMDB ID to match in raw_data.ProviderIds.Tmdb

    Returns:
        Number of items deleted
    """
    # First, find all matching media items (TMDB ID is stored as string in JSON)
    tmdb_id_str = str(tmdb_id)
    result = await db.execute(
        select(CachedMediaItem)
        .where(CachedMediaItem.user_id == user_id)
        .where(CachedMediaItem.raw_data.isnot(None))
    )
    items = result.scalars().all()

    # Filter items by TMDB ID in raw_data
    items_to_delete = []
    for item in items:
        raw_data = item.raw_data or {}
        provider_ids = raw_data.get("ProviderIds", {})
        if provider_ids.get("Tmdb") == tmdb_id_str:
            items_to_delete.append(item.id)

    if not items_to_delete:
        logger.debug(f"No CachedMediaItem found for TMDB ID {tmdb_id}")
        return 0

    # Delete the matching items
    await db.execute(delete(CachedMediaItem).where(CachedMediaItem.id.in_(items_to_delete)))

    logger.info(f"Deleted {len(items_to_delete)} CachedMediaItem(s) for TMDB ID {tmdb_id}")
    return len(items_to_delete)


async def _delete_cached_jellyseerr_request_by_tmdb_id(
    db: AsyncSession, user_id: int, tmdb_id: int, media_type: str
) -> None:
    """Delete CachedJellyseerrRequest by TMDB ID.

    Args:
        db: Database session
        user_id: User ID to filter by
        tmdb_id: TMDB ID to match
        media_type: "movie" or "tv" (lowercase)
    """
    await db.execute(
        delete(CachedJellyseerrRequest)
        .where(CachedJellyseerrRequest.user_id == user_id)
        .where(CachedJellyseerrRequest.tmdb_id == tmdb_id)
        .where(CachedJellyseerrRequest.media_type == media_type)
    )
    logger.debug(f"Deleted CachedJellyseerrRequest(s) for TMDB ID {tmdb_id}")


async def _delete_cached_jellyseerr_request_by_id(
    db: AsyncSession, user_id: int, jellyseerr_id: int
) -> None:
    """Delete CachedJellyseerrRequest by Jellyseerr ID.

    Args:
        db: Database session
        user_id: User ID to filter by
        jellyseerr_id: Jellyseerr request ID to match
    """
    await db.execute(
        delete(CachedJellyseerrRequest)
        .where(CachedJellyseerrRequest.user_id == user_id)
        .where(CachedJellyseerrRequest.jellyseerr_id == jellyseerr_id)
    )
    logger.debug(f"Deleted CachedJellyseerrRequest for Jellyseerr ID {jellyseerr_id}")


@router.delete("/movie/{tmdb_id}", response_model=DeleteContentResponse)
async def delete_movie(
    tmdb_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    delete_request: DeleteContentRequest | None = None,
) -> DeleteContentResponse:
    """Delete a movie from Radarr by TMDB ID.

    Optionally also deletes the associated Jellyseerr request.
    """
    settings = await _get_user_settings(db, current_user.id)

    if not settings or not settings.radarr_server_url or not settings.radarr_api_key_encrypted:
        raise HTTPException(
            status_code=400,
            detail="Radarr is not configured. Please configure Radarr in Settings.",
        )

    radarr_api_key = get_decrypted_radarr_api_key(settings)
    if not radarr_api_key:
        raise HTTPException(status_code=400, detail="Radarr API key not configured")

    # Delete from Radarr
    arr_deleted = False
    arr_message = ""
    delete_from_arr = delete_request.delete_from_arr if delete_request else True

    if delete_from_arr:
        success, message = await delete_movie_by_tmdb_id(
            settings.radarr_server_url, radarr_api_key, tmdb_id
        )
        arr_deleted = success
        arr_message = message
    else:
        arr_message = "Skipped Radarr deletion"

    # Optionally delete from Jellyseerr (delete media entry, not request)
    jellyseerr_deleted = False
    jellyseerr_message = ""
    delete_from_jellyseerr = delete_request.delete_from_jellyseerr if delete_request else True
    jellyseerr_media_id: int | None = None

    if delete_from_jellyseerr:
        # Look up media ID by TMDB ID (media.id is different from request.id)
        jellyseerr_media_id = await _lookup_jellyseerr_media_by_tmdb(
            db, current_user.id, tmdb_id, "movie"
        )

        if jellyseerr_media_id:
            if settings.jellyseerr_server_url and settings.jellyseerr_api_key_encrypted:
                jellyseerr_api_key = get_decrypted_jellyseerr_api_key(settings)
                if jellyseerr_api_key:
                    success, message = await delete_jellyseerr_media(
                        settings.jellyseerr_server_url, jellyseerr_api_key, jellyseerr_media_id
                    )
                    jellyseerr_deleted = success
                    jellyseerr_message = message
        else:
            jellyseerr_message = "No media found for this TMDB ID"

    # US-49.1: Delete from cache if Radarr deletion succeeded
    # (must be after Jellyseerr lookup but before response)
    if arr_deleted:
        await _delete_cached_media_by_tmdb_id(db, current_user.id, tmdb_id)
        await _delete_cached_jellyseerr_request_by_tmdb_id(db, current_user.id, tmdb_id, "movie")

    # Compose response message
    messages = []
    if delete_from_arr:
        messages.append(arr_message)
    if delete_from_jellyseerr:
        if jellyseerr_media_id:
            messages.append(
                jellyseerr_message if jellyseerr_message else "Jellyseerr not configured"
            )
        else:
            messages.append(jellyseerr_message)

    overall_success = (not delete_from_arr or arr_deleted) and (
        not delete_from_jellyseerr or not jellyseerr_media_id or jellyseerr_deleted
    )

    return DeleteContentResponse(
        success=overall_success,
        message="; ".join(messages) if messages else "No actions performed",
        arr_deleted=arr_deleted,
        jellyseerr_deleted=jellyseerr_deleted,
    )


@router.delete("/series/{tmdb_id}", response_model=DeleteContentResponse)
async def delete_series(
    tmdb_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    delete_request: DeleteContentRequest | None = None,
) -> DeleteContentResponse:
    """Delete a TV series from Sonarr by TMDB ID.

    Optionally also deletes the associated Jellyseerr request.
    """
    settings = await _get_user_settings(db, current_user.id)

    if not settings or not settings.sonarr_server_url or not settings.sonarr_api_key_encrypted:
        raise HTTPException(
            status_code=400,
            detail="Sonarr is not configured. Please configure Sonarr in Settings.",
        )

    sonarr_api_key = get_decrypted_sonarr_api_key(settings)
    if not sonarr_api_key:
        raise HTTPException(status_code=400, detail="Sonarr API key not configured")

    # Delete from Sonarr
    arr_deleted = False
    arr_message = ""
    delete_from_arr = delete_request.delete_from_arr if delete_request else True

    if delete_from_arr:
        success, message = await delete_series_by_tmdb_id(
            settings.sonarr_server_url, sonarr_api_key, tmdb_id
        )
        arr_deleted = success
        arr_message = message
    else:
        arr_message = "Skipped Sonarr deletion"

    # Optionally delete from Jellyseerr (delete media entry, not request)
    jellyseerr_deleted = False
    jellyseerr_message = ""
    delete_from_jellyseerr = delete_request.delete_from_jellyseerr if delete_request else True
    jellyseerr_media_id: int | None = None

    if delete_from_jellyseerr:
        # Look up media ID by TMDB ID (media.id is different from request.id)
        jellyseerr_media_id = await _lookup_jellyseerr_media_by_tmdb(
            db, current_user.id, tmdb_id, "tv"
        )

        if jellyseerr_media_id:
            if settings.jellyseerr_server_url and settings.jellyseerr_api_key_encrypted:
                jellyseerr_api_key = get_decrypted_jellyseerr_api_key(settings)
                if jellyseerr_api_key:
                    success, message = await delete_jellyseerr_media(
                        settings.jellyseerr_server_url, jellyseerr_api_key, jellyseerr_media_id
                    )
                    jellyseerr_deleted = success
                    jellyseerr_message = message
        else:
            jellyseerr_message = "No media found for this TMDB ID"

    # US-49.2: Delete from cache if Sonarr deletion succeeded
    # (must be after Jellyseerr lookup but before response)
    if arr_deleted:
        await _delete_cached_media_by_tmdb_id(db, current_user.id, tmdb_id)
        await _delete_cached_jellyseerr_request_by_tmdb_id(db, current_user.id, tmdb_id, "tv")

    # Compose response message
    messages = []
    if delete_from_arr:
        messages.append(arr_message)
    if delete_from_jellyseerr:
        if jellyseerr_media_id:
            messages.append(
                jellyseerr_message if jellyseerr_message else "Jellyseerr not configured"
            )
        else:
            messages.append(jellyseerr_message)

    overall_success = (not delete_from_arr or arr_deleted) and (
        not delete_from_jellyseerr or not jellyseerr_media_id or jellyseerr_deleted
    )

    return DeleteContentResponse(
        success=overall_success,
        message="; ".join(messages) if messages else "No actions performed",
        arr_deleted=arr_deleted,
        jellyseerr_deleted=jellyseerr_deleted,
    )


async def _lookup_jellyseerr_media_by_request_id(
    db: AsyncSession, user_id: int, jellyseerr_id: int
) -> int | None:
    """Look up Jellyseerr media ID by request ID.

    Args:
        db: Database session
        user_id: User ID to filter by
        jellyseerr_id: Jellyseerr request ID

    Returns:
        Jellyseerr media ID if found, None otherwise.
    """
    result = await db.execute(
        select(CachedJellyseerrRequest.jellyseerr_media_id)
        .where(CachedJellyseerrRequest.user_id == user_id)
        .where(CachedJellyseerrRequest.jellyseerr_id == jellyseerr_id)
    )
    row = result.scalar_one_or_none()
    return row


@router.delete("/request/{jellyseerr_id}", response_model=DeleteRequestResponse)
async def delete_request_endpoint(
    jellyseerr_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DeleteRequestResponse:
    """Delete a media entry from Jellyseerr by request ID.

    Note: This looks up the media ID from the cached request and deletes
    the media entry (not the request), which properly removes the item
    from Jellyseerr's tracking.
    """
    settings = await _get_user_settings(db, current_user.id)

    if (
        not settings
        or not settings.jellyseerr_server_url
        or not settings.jellyseerr_api_key_encrypted
    ):
        raise HTTPException(
            status_code=400,
            detail="Jellyseerr is not configured. Please configure Jellyseerr in Settings.",
        )

    jellyseerr_api_key = get_decrypted_jellyseerr_api_key(settings)
    if not jellyseerr_api_key:
        raise HTTPException(status_code=400, detail="Jellyseerr API key not configured")

    # Look up the media ID from the cached request
    media_id = await _lookup_jellyseerr_media_by_request_id(db, current_user.id, jellyseerr_id)
    if not media_id:
        raise HTTPException(
            status_code=404,
            detail=f"No media found for request {jellyseerr_id}. Try syncing your data.",
        )

    success, message = await delete_jellyseerr_media(
        settings.jellyseerr_server_url, jellyseerr_api_key, media_id
    )

    if not success:
        raise HTTPException(status_code=400, detail=message)

    # Delete from cache after successful Jellyseerr deletion
    await _delete_cached_jellyseerr_request_by_id(db, current_user.id, jellyseerr_id)

    return DeleteRequestResponse(success=True, message=message)
