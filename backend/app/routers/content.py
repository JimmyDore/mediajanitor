"""Content analysis API endpoints."""

from typing import Annotated, Union

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import User, get_db
from app.models.content import (
    ContentIssuesResponse,
    ContentSummaryResponse,
    OldUnwatchedResponse,
    UnavailableRequestsResponse,
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


@router.get("/issues", response_model=Union[ContentIssuesResponse, UnavailableRequestsResponse])
async def get_issues(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    filter: Annotated[
        str | None,
        Query(description="Filter by issue type: old, large, language, requests, multi"),
    ] = None,
) -> Union[ContentIssuesResponse, UnavailableRequestsResponse]:
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
    # Requests filter returns a different response type
    if filter == "requests":
        items = await get_unavailable_requests(db, current_user.id)
        return UnavailableRequestsResponse(
            items=items,
            total_count=len(items),
        )

    return await get_content_issues(db, current_user.id, filter)
