"""Content analysis API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import User, get_db
from app.models.content import (
    ContentIssueItem,
    ContentIssuesResponse,
    ContentSummaryResponse,
    OldUnwatchedResponse,
)
from app.services.auth import get_current_user
from app.services.content import (
    get_content_issues,
    get_content_summary,
    get_old_unwatched_content,
    get_unavailable_requests,
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
