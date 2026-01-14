"""Sync service for fetching and caching data from Jellyfin and Jellyseerr."""

import logging
from datetime import datetime, timezone
from typing import Any, cast

import httpx
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import (
    UserSettings,
    CachedMediaItem,
    CachedJellyseerrRequest,
    SyncStatus,
)
from app.services.encryption import decrypt_value

logger = logging.getLogger(__name__)


async def fetch_jellyfin_media(
    server_url: str, api_key: str
) -> list[dict[str, Any]]:
    """
    Fetch all movies and series from Jellyfin API.

    Based on original_script.py:get_movies_and_shows_for_user
    """
    server_url = server_url.rstrip("/")

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            # First get users to find an admin user for fetching library
            users_response = await client.get(
                f"{server_url}/Users",
                headers={"X-Emby-Token": api_key},
            )
            users_response.raise_for_status()
            users = users_response.json()

            if not users:
                logger.warning("No users found in Jellyfin")
                return []

            # Use the first admin user or first user
            user = users[0]
            user_id = user["Id"]

            # Fetch items with relevant fields
            params = {
                "UserId": user_id,
                "IncludeItemTypes": "Movie,Series",
                "Recursive": "true",
                "Fields": "DateCreated,DateLastSaved,UserData,Path,Overview,Genres,Studios,People,ProductionYear,DateLastMediaAdded,MediaSources,ProviderIds",
                "SortBy": "SortName",
                "SortOrder": "Ascending",
                "StartIndex": 0,
                "Limit": 10000,
            }

            response = await client.get(
                f"{server_url}/Users/{user_id}/Items",
                headers={"X-Emby-Token": api_key},
                params=params,
            )
            response.raise_for_status()

            data = response.json()
            items: list[dict[str, Any]] = data.get("Items", [])
            logger.info(f"Fetched {len(items)} media items from Jellyfin")
            return items

    except httpx.HTTPStatusError as e:
        logger.error(f"Jellyfin API error: {e.response.status_code}")
        raise
    except httpx.RequestError as e:
        logger.error(f"Jellyfin connection error: {e}")
        raise


def extract_title_from_request(req: dict[str, Any]) -> str:
    """
    Extract title from a Jellyseerr request using embedded data.

    Uses fallback chain: title → name → originalTitle → originalName → tmdbId

    No separate API calls are made - all data comes from the request response.
    """
    media = req.get("media", {})

    # Try fields in order of preference
    # Movies typically have 'title' and 'originalTitle'
    # TV shows typically have 'name' and 'originalName'
    title = (
        media.get("title")
        or media.get("name")
        or media.get("originalTitle")
        or media.get("originalName")
    )

    if title:
        return str(title)

    # Last resort: use TMDB ID
    tmdb_id = media.get("tmdbId")
    if tmdb_id:
        return f"TMDB-{tmdb_id}"

    return "Unknown"


def extract_release_date_from_request(req: dict[str, Any]) -> str | None:
    """
    Extract release date from a Jellyseerr request using embedded data.

    For movies: uses media.releaseDate
    For TV shows: uses media.firstAirDate

    Returns date string in format stored by Jellyseerr (typically YYYY-MM-DD).
    """
    media = req.get("media", {})
    media_type = media.get("mediaType", "")

    release_date: str | None = None
    if media_type == "movie":
        release_date = media.get("releaseDate")
    elif media_type == "tv":
        release_date = media.get("firstAirDate")

    return release_date


async def fetch_jellyseerr_requests(
    server_url: str, api_key: str
) -> list[dict[str, Any]]:
    """
    Fetch all requests from Jellyseerr API with pagination.

    Based on original_script.py:fetch_jellyseer_requests

    Titles are extracted from embedded data in the response using
    the fallback chain: title → name → originalTitle → originalName → tmdbId
    """
    server_url = server_url.rstrip("/")

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            all_requests: list[dict[str, Any]] = []
            page = 1
            take = 50

            while True:
                params = {
                    "take": take,
                    "skip": (page - 1) * take,
                }

                response = await client.get(
                    f"{server_url}/api/v1/request",
                    headers={"X-Api-Key": api_key},
                    params=params,
                )
                response.raise_for_status()

                data = response.json()
                page_results = data.get("results", [])
                page_info = data.get("pageInfo", {})

                all_requests.extend(page_results)

                total_pages = page_info.get("pages", 1)
                if page >= total_pages or len(page_results) == 0:
                    break

                page += 1

                if page > 100:  # Safety limit
                    break

            logger.info(f"Fetched {len(all_requests)} requests from Jellyseerr")
            return all_requests

    except httpx.HTTPStatusError as e:
        logger.error(f"Jellyseerr API error: {e.response.status_code}")
        raise
    except httpx.RequestError as e:
        logger.error(f"Jellyseerr connection error: {e}")
        raise


def extract_size_from_item(item: dict[str, Any]) -> int | None:
    """Extract total size in bytes from media sources."""
    media_sources = item.get("MediaSources", [])
    if not media_sources:
        return None

    total_size = 0
    for source in media_sources:
        size = source.get("Size")
        if size:
            total_size += size

    return total_size if total_size > 0 else None


async def cache_media_items(
    db: AsyncSession, user_id: int, items: list[dict[str, Any]]
) -> int:
    """Cache media items in database, replacing old data."""
    # Delete existing cached items for this user
    await db.execute(
        delete(CachedMediaItem).where(CachedMediaItem.user_id == user_id)
    )

    # Insert new items
    cached_count = 0
    for item in items:
        user_data = item.get("UserData", {})
        cached_item = CachedMediaItem(
            user_id=user_id,
            jellyfin_id=item.get("Id", ""),
            name=item.get("Name", "Unknown"),
            media_type=item.get("Type", "Unknown"),
            production_year=item.get("ProductionYear"),
            date_created=item.get("DateCreated"),
            path=item.get("Path"),
            size_bytes=extract_size_from_item(item),
            played=user_data.get("Played", False),
            play_count=user_data.get("PlayCount", 0),
            last_played_date=user_data.get("LastPlayedDate"),
            raw_data=item,
        )
        db.add(cached_item)
        cached_count += 1

    await db.flush()
    return cached_count


async def cache_jellyseerr_requests(
    db: AsyncSession, user_id: int, requests: list[dict[str, Any]]
) -> int:
    """Cache Jellyseerr requests in database, replacing old data."""
    # Delete existing cached requests for this user
    await db.execute(
        delete(CachedJellyseerrRequest).where(
            CachedJellyseerrRequest.user_id == user_id
        )
    )

    # Insert new requests
    cached_count = 0
    for req in requests:
        media = req.get("media", {})
        requested_by = req.get("requestedBy", {})

        # Extract title using fallback chain (from embedded data, no extra API calls)
        title = extract_title_from_request(req)

        # Extract release date (movies: releaseDate, TV: firstAirDate)
        release_date = extract_release_date_from_request(req)

        cached_request = CachedJellyseerrRequest(
            user_id=user_id,
            jellyseerr_id=req.get("id", 0),
            tmdb_id=media.get("tmdbId"),
            media_type=media.get("mediaType", "unknown"),
            status=req.get("status", 0),
            title=title,
            requested_by=requested_by.get("displayName"),
            created_at_source=req.get("createdAt"),
            release_date=release_date,
            raw_data=req,
        )
        db.add(cached_request)
        cached_count += 1

    await db.flush()
    return cached_count


async def update_sync_status(
    db: AsyncSession,
    user_id: int,
    status: str,
    error: str | None = None,
    media_count: int | None = None,
    requests_count: int | None = None,
    started: bool = False,
) -> None:
    """Update sync status for a user."""
    result = await db.execute(
        select(SyncStatus).where(SyncStatus.user_id == user_id)
    )
    sync_status = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)

    if sync_status:
        if started:
            sync_status.last_sync_started = now
        else:
            sync_status.last_sync_completed = now
            sync_status.last_sync_status = status
            sync_status.last_sync_error = error
            sync_status.media_items_count = media_count
            sync_status.requests_count = requests_count
    else:
        sync_status = SyncStatus(
            user_id=user_id,
            last_sync_started=now if started else None,
            last_sync_completed=None if started else now,
            last_sync_status=None if started else status,
            last_sync_error=error,
            media_items_count=media_count,
            requests_count=requests_count,
        )
        db.add(sync_status)

    await db.flush()


async def get_sync_status(db: AsyncSession, user_id: int) -> SyncStatus | None:
    """Get sync status for a user."""
    result = await db.execute(
        select(SyncStatus).where(SyncStatus.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def run_user_sync(
    db: AsyncSession, user_id: int
) -> dict[str, Any]:
    """
    Run a full sync for a user.

    Fetches data from Jellyfin and Jellyseerr (if configured),
    and caches it in the database.
    """
    # Get user settings
    result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == user_id)
    )
    settings = result.scalar_one_or_none()

    if not settings or not settings.jellyfin_server_url or not settings.jellyfin_api_key_encrypted:
        return {
            "status": "failed",
            "error": "Jellyfin not configured",
            "media_items_synced": 0,
            "requests_synced": 0,
        }

    # Mark sync as started
    await update_sync_status(db, user_id, "in_progress", started=True)

    media_count = 0
    requests_count = 0
    error_message = None

    try:
        # Fetch and cache Jellyfin data
        jellyfin_api_key = decrypt_value(settings.jellyfin_api_key_encrypted)
        items = await fetch_jellyfin_media(
            settings.jellyfin_server_url, jellyfin_api_key
        )
        media_count = await cache_media_items(db, user_id, items)
        logger.info(f"Cached {media_count} media items for user {user_id}")

    except Exception as e:
        error_message = f"Jellyfin sync failed: {str(e)}"
        logger.error(error_message)
        await update_sync_status(
            db, user_id, "failed", error=error_message, media_count=0, requests_count=0
        )
        return {
            "status": "failed",
            "error": error_message,
            "media_items_synced": 0,
            "requests_synced": 0,
        }

    try:
        # Fetch and cache Jellyseerr data (if configured)
        if settings.jellyseerr_server_url and settings.jellyseerr_api_key_encrypted:
            jellyseerr_api_key = decrypt_value(settings.jellyseerr_api_key_encrypted)
            requests_data = await fetch_jellyseerr_requests(
                settings.jellyseerr_server_url, jellyseerr_api_key
            )
            requests_count = await cache_jellyseerr_requests(db, user_id, requests_data)
            logger.info(f"Cached {requests_count} Jellyseerr requests for user {user_id}")

    except Exception as e:
        # Jellyseerr sync failure is not critical - we still have Jellyfin data
        error_message = f"Jellyseerr sync failed: {str(e)}"
        logger.warning(error_message)

    # Update sync status
    final_status = "success" if not error_message else "partial"
    await update_sync_status(
        db,
        user_id,
        final_status,
        error=error_message,
        media_count=media_count,
        requests_count=requests_count,
    )

    return {
        "status": final_status,
        "media_items_synced": media_count,
        "requests_synced": requests_count,
        "error": error_message,
    }
