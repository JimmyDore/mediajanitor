"""Whitelist API endpoints.

Uses endpoint factory pattern to eliminate duplication for 6 whitelist types.
The 4 jellyfin-id-based whitelists share identical patterns and are generated
via create_jellyfin_whitelist_routes(). Requests and episode-exempt have
custom logic and remain as separate endpoints.
"""

from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import CachedJellyseerrRequest, User, get_db
from app.models.content import (
    EpisodeExemptAddRequest,
    EpisodeExemptListResponse,
    RequestWhitelistAddRequest,
    RequestWhitelistListResponse,
    WhitelistAddRequest,
    WhitelistAddResponse,
    WhitelistListResponse,
    WhitelistRemoveResponse,
)
from app.services.auth import get_current_user
from app.services.whitelist import (
    add_episode_language_exempt,
    add_to_french_only_whitelist,
    add_to_language_exempt_whitelist,
    add_to_large_whitelist,
    add_to_request_whitelist,
    add_to_whitelist,
    get_episode_language_exempt,
    get_french_only_whitelist,
    get_language_exempt_whitelist,
    get_large_whitelist,
    get_request_whitelist,
    get_whitelist,
    remove_episode_language_exempt,
    remove_from_french_only_whitelist,
    remove_from_language_exempt_whitelist,
    remove_from_large_whitelist,
    remove_from_request_whitelist,
    remove_from_whitelist,
)

router = APIRouter(prefix="/api/whitelist", tags=["whitelist"])


# ============================================================================
# Type aliases for service functions
# ============================================================================

# Use Any for return type since add functions may return None or the model
AddJellyfinFunc = Callable[
    [AsyncSession, int, str, str, str, datetime | None],
    Awaitable[Any],
]
GetListFunc = Callable[..., Awaitable[WhitelistListResponse]]
RemoveFunc = Callable[[AsyncSession, int, int], Awaitable[bool]]


# ============================================================================
# Jellyfin-ID Whitelist Endpoint Factory
# ============================================================================


def create_jellyfin_whitelist_routes(
    path: str,
    add_func: AddJellyfinFunc,
    get_func: GetListFunc,
    remove_func: RemoveFunc,
    whitelist_name: str,
    list_description: str,
    add_description: str,
    remove_description: str,
) -> None:
    """Create GET, POST, DELETE endpoints for a jellyfin-id-based whitelist.

    Args:
        path: URL path segment (e.g., "french-only")
        add_func: Service function to add item
        get_func: Service function to get list
        remove_func: Service function to remove item
        whitelist_name: Human-readable name for messages (e.g., "french-only whitelist")
        list_description: OpenAPI description for GET endpoint
        add_description: OpenAPI description for POST endpoint
        remove_description: OpenAPI description for DELETE endpoint
    """

    @router.get(
        f"/{path}",
        response_model=WhitelistListResponse,
        name=f"list_{path.replace('-', '_')}_whitelist",
    )
    async def list_whitelist(
        current_user: Annotated[User, Depends(get_current_user)],
        db: Annotated[AsyncSession, Depends(get_db)],
    ) -> WhitelistListResponse:
        return await get_func(db=db, user_id=current_user.id)

    # Update docstring for OpenAPI
    list_whitelist.__doc__ = list_description

    @router.post(
        f"/{path}",
        response_model=WhitelistAddResponse,
        status_code=status.HTTP_201_CREATED,
        name=f"add_to_{path.replace('-', '_')}",
    )
    async def add_to_whitelist_endpoint(
        request: WhitelistAddRequest,
        current_user: Annotated[User, Depends(get_current_user)],
        db: Annotated[AsyncSession, Depends(get_db)],
    ) -> WhitelistAddResponse:
        try:
            await add_func(
                db,
                current_user.id,
                request.jellyfin_id,
                request.name,
                request.media_type,
                request.expires_at,
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(e),
            )

        return WhitelistAddResponse(
            message=f"Added to {whitelist_name}",
            jellyfin_id=request.jellyfin_id,
            name=request.name,
        )

    add_to_whitelist_endpoint.__doc__ = add_description

    @router.delete(
        f"/{path}/{{whitelist_id}}",
        response_model=WhitelistRemoveResponse,
        name=f"remove_from_{path.replace('-', '_')}",
    )
    async def remove_from_whitelist_endpoint(
        whitelist_id: int,
        current_user: Annotated[User, Depends(get_current_user)],
        db: Annotated[AsyncSession, Depends(get_db)],
    ) -> WhitelistRemoveResponse:
        removed = await remove_func(
            db,
            current_user.id,
            whitelist_id,
        )

        if not removed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Whitelist entry not found",
            )

        return WhitelistRemoveResponse(message=f"Removed from {whitelist_name}")

    remove_from_whitelist_endpoint.__doc__ = remove_description


# ============================================================================
# Generate routes for 4 jellyfin-id-based whitelists
# ============================================================================

# Content Whitelist (old/unwatched content protection)
create_jellyfin_whitelist_routes(
    path="content",
    add_func=add_to_whitelist,
    get_func=get_whitelist,
    remove_func=remove_from_whitelist,
    whitelist_name="whitelist",
    list_description="Get all items in the user's content whitelist.",
    add_description="""Add content to the user's whitelist.

This protects the content from appearing in the old/unwatched content list.""",
    remove_description="""Remove an item from the user's content whitelist.

After removal, the content may reappear in the old/unwatched content list.""",
)

# French-Only Whitelist (exempt from missing English audio checks)
create_jellyfin_whitelist_routes(
    path="french-only",
    add_func=add_to_french_only_whitelist,
    get_func=get_french_only_whitelist,
    remove_func=remove_from_french_only_whitelist,
    whitelist_name="french-only whitelist",
    list_description="""Get all items in the user's french-only whitelist.

Items in this whitelist are exempt from missing English audio checks.""",
    add_description="""Add content to the user's french-only whitelist.

Items in this whitelist are exempt from missing English audio checks.
Use this for French-language films that don't need English audio.""",
    remove_description="""Remove an item from the user's french-only whitelist.

After removal, the content may reappear in language issues if it's missing English audio.""",
)

# Language-Exempt Whitelist (exempt from ALL language checks)
create_jellyfin_whitelist_routes(
    path="language-exempt",
    add_func=add_to_language_exempt_whitelist,
    get_func=get_language_exempt_whitelist,
    remove_func=remove_from_language_exempt_whitelist,
    whitelist_name="language-exempt whitelist",
    list_description="""Get all items in the user's language-exempt whitelist.

Items in this whitelist are exempt from ALL language checks.""",
    add_description="""Add content to the user's language-exempt whitelist.

Items in this whitelist are exempt from ALL language checks.
Use this for content that should never flag language issues.""",
    remove_description="""Remove an item from the user's language-exempt whitelist.

After removal, the content may reappear in language issues if it has language problems.""",
)

# Large Content Whitelist (exempt from large content checks)
create_jellyfin_whitelist_routes(
    path="large",
    add_func=add_to_large_whitelist,
    get_func=get_large_whitelist,
    remove_func=remove_from_large_whitelist,
    whitelist_name="large content whitelist",
    list_description="""Get all items in the user's large content whitelist.

Items in this whitelist are exempt from large content checks.""",
    add_description="""Add content to the user's large content whitelist.

Items in this whitelist are exempt from large content checks.
Use this for content you want to keep in high quality.""",
    remove_description="""Remove an item from the user's large content whitelist.

After removal, the content may reappear in the large content list.""",
)


# ============================================================================
# Request Whitelist - Has special title lookup logic, cannot be generalized
# ============================================================================


@router.get("/requests", response_model=RequestWhitelistListResponse)
async def list_request_whitelist(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RequestWhitelistListResponse:
    """Get all items in the user's request whitelist.

    Items in this whitelist are hidden from the unavailable requests list.
    """
    return await get_request_whitelist(db=db, user_id=current_user.id)


@router.post("/requests", response_model=WhitelistAddResponse, status_code=status.HTTP_201_CREATED)
async def add_to_requests(
    request: RequestWhitelistAddRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WhitelistAddResponse:
    """Add a Jellyseerr request to the user's request whitelist.

    Items in this whitelist are hidden from the unavailable requests list.
    Use this to hide requests you're intentionally waiting on.
    """
    # If title looks like a TMDB ID fallback (e.g., "TMDB-123456"), look up actual title
    title = request.title
    if title.startswith("TMDB-"):
        result = await db.execute(
            select(CachedJellyseerrRequest).where(
                CachedJellyseerrRequest.user_id == current_user.id,
                CachedJellyseerrRequest.jellyseerr_id == request.jellyseerr_id,
            )
        )
        cached_request = result.scalar_one_or_none()
        if cached_request:
            title = _extract_title_from_cached_request(cached_request, title)

    try:
        await add_to_request_whitelist(
            db=db,
            user_id=current_user.id,
            jellyseerr_id=request.jellyseerr_id,
            title=title,
            media_type=request.media_type,
            expires_at=request.expires_at,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )

    return WhitelistAddResponse(
        message="Added to request whitelist",
        jellyfin_id=str(request.jellyseerr_id),  # Reusing existing response model
        name=title,
    )


def _extract_title_from_cached_request(
    cached_request: CachedJellyseerrRequest, fallback: str
) -> str:
    """Extract title from cached request, trying multiple sources."""
    # Try to get title from various sources
    if cached_request.title and not cached_request.title.startswith("TMDB-"):
        return cached_request.title

    if cached_request.raw_data:
        raw_data: dict[str, Any] = cached_request.raw_data
        media: dict[str, Any] = raw_data.get("media", {})
        # Try title/name from media object first
        extracted_title: str | None = (
            media.get("title")
            or media.get("name")
            or media.get("originalTitle")
            or media.get("originalName")
        )
        # Fallback to slug (human-readable URL segment)
        if not extracted_title and media.get("externalServiceSlug"):
            slug: str = media.get("externalServiceSlug", "")
            # Convert slug to title: "the-new-years" -> "The New Years"
            extracted_title = slug.replace("-", " ").title()
        if extracted_title:
            return str(extracted_title)

    return fallback


@router.delete("/requests/{whitelist_id}", response_model=WhitelistRemoveResponse)
async def remove_from_requests(
    whitelist_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WhitelistRemoveResponse:
    """Remove an item from the user's request whitelist.

    After removal, the request may reappear in the unavailable requests list.
    """
    removed = await remove_from_request_whitelist(
        db=db,
        user_id=current_user.id,
        whitelist_id=whitelist_id,
    )

    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Whitelist entry not found",
        )

    return WhitelistRemoveResponse(message="Removed from request whitelist")


# ============================================================================
# Episode Language Exempt - Has completely different fields, cannot be generalized
# ============================================================================


@router.get("/episode-exempt", response_model=EpisodeExemptListResponse)
async def list_episode_exempt(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EpisodeExemptListResponse:
    """Get all episodes in the user's episode language exempt list.

    Episodes in this list are exempt from language checks during sync.
    """
    return await get_episode_language_exempt(db=db, user_id=current_user.id)


@router.post(
    "/episode-exempt", response_model=WhitelistAddResponse, status_code=status.HTTP_201_CREATED
)
async def add_episode_to_exempt(
    request: EpisodeExemptAddRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WhitelistAddResponse:
    """Add an episode to the user's episode language exempt list.

    Episodes in this list are exempt from language checks during sync.
    Use this for episodes that intentionally have limited audio tracks.
    """
    try:
        await add_episode_language_exempt(
            db=db,
            user_id=current_user.id,
            jellyfin_id=request.jellyfin_id,
            series_name=request.series_name,
            season_number=request.season_number,
            episode_number=request.episode_number,
            episode_name=request.episode_name,
            expires_at=request.expires_at,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )

    identifier = f"S{request.season_number:02d}E{request.episode_number:02d}"
    return WhitelistAddResponse(
        message="Added to episode language exempt list",
        jellyfin_id=request.jellyfin_id,
        name=f"{request.series_name} - {identifier}",
    )


@router.delete("/episode-exempt/{exempt_id}", response_model=WhitelistRemoveResponse)
async def remove_episode_from_exempt(
    exempt_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WhitelistRemoveResponse:
    """Remove an episode from the user's episode language exempt list.

    After removal, the episode may reappear in language issues if it has language problems.
    """
    removed = await remove_episode_language_exempt(
        db=db,
        user_id=current_user.id,
        exempt_id=exempt_id,
    )

    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Episode exempt entry not found",
        )

    return WhitelistRemoveResponse(message="Removed from episode language exempt list")
