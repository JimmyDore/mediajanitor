"""Content analysis API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import CachedJellyseerrRequest, User, UserSettings, get_db
from app.models.content import (
    ContentIssueItem,
    ContentIssuesResponse,
    ContentSummaryResponse,
    DeleteContentRequest,
    DeleteContentResponse,
    DeleteRequestResponse,
    OldUnwatchedResponse,
)
from app.services.auth import get_current_user
from app.services.content import (
    get_content_issues,
    get_content_summary,
    get_old_unwatched_content,
    get_unavailable_requests,
)
from app.services.jellyseerr import (
    delete_jellyseerr_request,
    get_decrypted_jellyseerr_api_key,
)
from app.services.radarr import (
    delete_movie_by_tmdb_id,
    get_decrypted_radarr_api_key,
)
from app.services.sonarr import (
    delete_series_by_tmdb_id,
    get_decrypted_sonarr_api_key,
)


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
        Query(description="Filter by issue type: old, large, language, requests, multi"),
    ] = None,
) -> ContentIssuesResponse:
    """Get unified list of all content with issues for the current user.

    Supports filtering by issue type:
    - old: Old/unwatched content (4+ months since last watched)
    - large: Movies larger than 13GB
    - language: Content with language issues
    - requests: Unavailable Jellyseerr requests
    - multi: Content with 2+ issues (worst offenders)

    Each item includes a list of all applicable issues.
    Results are sorted by size (largest first) for content, by request date for requests.
    """
    # Requests filter converts to unified format
    if filter == "requests":
        request_items = await get_unavailable_requests(db, current_user.id)
        # Convert request items to ContentIssueItem format
        unified_items = [
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
                # Request-specific fields
                requested_by=req.requested_by,
                request_date=req.request_date,
                missing_seasons=req.missing_seasons,
                release_date=req.release_date,
            )
            for req in request_items
        ]
        return ContentIssuesResponse(
            items=unified_items,
            total_count=len(unified_items),
            total_size_bytes=0,
            total_size_formatted="0 B",
        )

    return await get_content_issues(db, current_user.id, filter)


# US-15.4, US-15.5, US-15.6: Delete content endpoints


async def _get_user_settings(db: AsyncSession, user_id: int) -> UserSettings | None:
    """Get user settings from database."""
    result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == user_id)
    )
    return result.scalar_one_or_none()


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

    # Optionally delete from Jellyseerr
    jellyseerr_deleted = False
    jellyseerr_message = ""
    delete_from_jellyseerr = delete_request.delete_from_jellyseerr if delete_request else True
    jellyseerr_request_id = delete_request.jellyseerr_request_id if delete_request else None

    if delete_from_jellyseerr and jellyseerr_request_id:
        if settings.jellyseerr_server_url and settings.jellyseerr_api_key_encrypted:
            jellyseerr_api_key = get_decrypted_jellyseerr_api_key(settings)
            if jellyseerr_api_key:
                success, message = await delete_jellyseerr_request(
                    settings.jellyseerr_server_url, jellyseerr_api_key, jellyseerr_request_id
                )
                jellyseerr_deleted = success
                jellyseerr_message = message

    # Compose response message
    messages = []
    if delete_from_arr:
        messages.append(arr_message)
    if delete_from_jellyseerr and jellyseerr_request_id:
        messages.append(jellyseerr_message if jellyseerr_message else "Jellyseerr not configured")

    overall_success = (not delete_from_arr or arr_deleted) and \
                      (not delete_from_jellyseerr or not jellyseerr_request_id or jellyseerr_deleted)

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

    # Optionally delete from Jellyseerr
    jellyseerr_deleted = False
    jellyseerr_message = ""
    delete_from_jellyseerr = delete_request.delete_from_jellyseerr if delete_request else True
    jellyseerr_request_id = delete_request.jellyseerr_request_id if delete_request else None

    if delete_from_jellyseerr and jellyseerr_request_id:
        if settings.jellyseerr_server_url and settings.jellyseerr_api_key_encrypted:
            jellyseerr_api_key = get_decrypted_jellyseerr_api_key(settings)
            if jellyseerr_api_key:
                success, message = await delete_jellyseerr_request(
                    settings.jellyseerr_server_url, jellyseerr_api_key, jellyseerr_request_id
                )
                jellyseerr_deleted = success
                jellyseerr_message = message

    # Compose response message
    messages = []
    if delete_from_arr:
        messages.append(arr_message)
    if delete_from_jellyseerr and jellyseerr_request_id:
        messages.append(jellyseerr_message if jellyseerr_message else "Jellyseerr not configured")

    overall_success = (not delete_from_arr or arr_deleted) and \
                      (not delete_from_jellyseerr or not jellyseerr_request_id or jellyseerr_deleted)

    return DeleteContentResponse(
        success=overall_success,
        message="; ".join(messages) if messages else "No actions performed",
        arr_deleted=arr_deleted,
        jellyseerr_deleted=jellyseerr_deleted,
    )


@router.delete("/request/{jellyseerr_id}", response_model=DeleteRequestResponse)
async def delete_request_endpoint(
    jellyseerr_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DeleteRequestResponse:
    """Delete a request from Jellyseerr by request ID."""
    settings = await _get_user_settings(db, current_user.id)

    if not settings or not settings.jellyseerr_server_url or not settings.jellyseerr_api_key_encrypted:
        raise HTTPException(
            status_code=400,
            detail="Jellyseerr is not configured. Please configure Jellyseerr in Settings.",
        )

    jellyseerr_api_key = get_decrypted_jellyseerr_api_key(settings)
    if not jellyseerr_api_key:
        raise HTTPException(status_code=400, detail="Jellyseerr API key not configured")

    success, message = await delete_jellyseerr_request(
        settings.jellyseerr_server_url, jellyseerr_api_key, jellyseerr_id
    )

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return DeleteRequestResponse(success=True, message=message)
