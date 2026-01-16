"""Sync service for fetching and caching data from Jellyfin and Jellyseerr."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, TypedDict, cast

import httpx
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import (
    User,
    UserSettings,
    CachedMediaItem,
    CachedJellyseerrRequest,
    SyncStatus,
)
from app.services.encryption import decrypt_value
from app.services.retry import retry_with_backoff
from app.services.slack import send_slack_message

logger = logging.getLogger(__name__)


async def send_sync_failure_notification(
    user_email: str,
    service: str,
    error_message: str,
) -> None:
    """
    Send a Slack notification about a sync failure.

    This is a fire-and-forget function - it logs errors but never raises.

    Args:
        user_email: Email of the user whose sync failed
        service: Name of the service that failed (e.g., "Jellyfin", "Jellyseerr")
        error_message: The error message describing the failure
    """
    settings = get_settings()
    webhook_url = settings.slack_webhook_sync_failures

    if not webhook_url:
        # Webhook not configured, silently skip
        return

    failure_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # Create message in Slack Block Kit format
    message = {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"⚠️ {service} Sync Failed",
                    "emoji": True,
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*User:*\n{user_email}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Service:*\n{service}"
                    }
                ]
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Time:*\n{failure_time}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Error:*\n```{error_message[:200]}```"
                    }
                ]
            }
        ],
        "text": f"Sync failed for {user_email}: {service} - {error_message}"  # Fallback text
    }

    try:
        await send_slack_message(webhook_url, message)
    except Exception as e:
        # Log but don't raise - this is fire-and-forget
        logger.warning(f"Failed to send sync failure notification for {user_email}: {e}")


class AggregatedWatchData(TypedDict):
    """Aggregated watch data from multiple users."""

    played: bool
    play_count: int
    last_played_date: str | None


def aggregate_user_watch_data(user_data_list: list[dict[str, Any]]) -> AggregatedWatchData:
    """
    Aggregate watch data from multiple Jellyfin users.

    Args:
        user_data_list: List of UserData dicts from different users

    Returns:
        AggregatedWatchData with:
        - played: True if ANY user has watched
        - play_count: Sum of all users' play counts
        - last_played_date: Most recent date across all users
    """
    played = False
    total_play_count = 0
    latest_played_date: str | None = None

    for user_data in user_data_list:
        if user_data.get("Played", False):
            played = True

        play_count = user_data.get("PlayCount", 0)
        total_play_count += play_count

        last_played = user_data.get("LastPlayedDate")
        if last_played:
            if latest_played_date is None or last_played > latest_played_date:
                latest_played_date = last_played

    return {
        "played": played,
        "play_count": total_play_count,
        "last_played_date": latest_played_date,
    }


async def fetch_jellyfin_users(
    server_url: str, api_key: str
) -> list[dict[str, Any]]:
    """
    Fetch all users from Jellyfin API with retry on transient failures.

    Returns list of user dicts with Id and Name.
    """
    server_url = server_url.rstrip("/")

    async def _fetch() -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{server_url}/Users",
                headers={"X-Emby-Token": api_key},
            )
            response.raise_for_status()
            users: list[dict[str, Any]] = response.json()
            return users

    return await retry_with_backoff(_fetch, "Jellyfin")


async def fetch_user_items(
    client: httpx.AsyncClient,
    server_url: str,
    api_key: str,
    user_id: str,
    user_name: str,
    user_index: int,
    total_users: int,
) -> list[dict[str, Any]]:
    """
    Fetch all movies and series for a specific Jellyfin user with retry on transient failures.

    Args:
        client: Shared httpx client
        server_url: Jellyfin server URL
        api_key: Jellyfin API key
        user_id: User's Jellyfin ID
        user_name: User's display name (for logging)
        user_index: 1-based index of user being processed
        total_users: Total number of users

    Returns list of media items with UserData for this user.
    """
    logger.info(f"Fetching user {user_index}/{total_users}: {user_name}")

    params: dict[str, str | int] = {
        "UserId": user_id,
        "IncludeItemTypes": "Movie,Series",
        "Recursive": "true",
        "Fields": "DateCreated,DateLastSaved,UserData,Path,Overview,Genres,Studios,People,ProductionYear,DateLastMediaAdded,MediaSources,ProviderIds",
        "SortBy": "SortName",
        "SortOrder": "Ascending",
        "StartIndex": 0,
        "Limit": 10000,
    }

    async def _fetch() -> list[dict[str, Any]]:
        response = await client.get(
            f"{server_url}/Users/{user_id}/Items",
            headers={"X-Emby-Token": api_key},
            params=params,
        )
        response.raise_for_status()
        data = response.json()
        items: list[dict[str, Any]] = data.get("Items", [])
        return items

    items = await retry_with_backoff(_fetch, "Jellyfin")
    logger.info(f"User {user_name}: {len(items)} items")
    return items


async def fetch_all_users_media(
    server_url: str, api_key: str
) -> list[dict[str, Any]]:
    """
    Fetch media from all Jellyfin users and aggregate watch data.

    Uses asyncio.gather() to parallelize user fetches (6-15 users expected).

    Watch data aggregation:
    - played = True if ANY user has watched
    - last_played_date = most recent date across all users
    - play_count = sum of all users' play counts

    Returns list of media items with aggregated UserData.
    """
    server_url = server_url.rstrip("/")

    # Fetch list of users
    users = await fetch_jellyfin_users(server_url, api_key)

    if not users:
        logger.warning("No users found in Jellyfin")
        return []

    logger.info(f"Found {len(users)} Jellyfin users, fetching items for each...")

    # Dictionary to store items by ID with watch data from all users
    items_dict: dict[str, dict[str, Any]] = {}

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Create tasks for all users
        tasks = [
            fetch_user_items(
                client,
                server_url,
                api_key,
                user["Id"],
                user.get("Name", "Unknown"),
                idx + 1,
                len(users),
            )
            for idx, user in enumerate(users)
        ]

        # Execute all user fetches in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results from each user
        for user, result in zip(users, results):
            if isinstance(result, Exception):
                logger.warning(f"Failed to fetch items for user {user.get('Name', 'Unknown')}: {result}")
                continue

            user_items = cast(list[dict[str, Any]], result)

            for item in user_items:
                item_id = item.get("Id")
                if not item_id:
                    continue

                # First time seeing this item - store it
                if item_id not in items_dict:
                    # Create a copy without UserData (we'll aggregate UserData separately)
                    item_copy = item.copy()
                    item_copy.pop("UserData", None)
                    items_dict[item_id] = {
                        "item": item_copy,
                        "user_data_list": [],
                    }

                # Add this user's watch data
                user_data = item.get("UserData", {})
                if user_data.get("PlayCount", 0) > 0 or user_data.get("Played", False):
                    items_dict[item_id]["user_data_list"].append(user_data)

    # Convert back to list with aggregated UserData
    result_items: list[dict[str, Any]] = []
    for item_id, data in items_dict.items():
        item = data["item"].copy()
        user_data_list = data["user_data_list"]

        # Aggregate watch data from all users
        aggregated = aggregate_user_watch_data(user_data_list)

        # Create aggregated UserData in Jellyfin format
        item["UserData"] = {
            "Played": aggregated["played"],
            "PlayCount": aggregated["play_count"],
            "LastPlayedDate": aggregated["last_played_date"],
        }

        result_items.append(item)

    logger.info(f"Aggregated {len(result_items)} media items from {len(users)} users")
    return result_items


async def fetch_media_details(
    client: httpx.AsyncClient,
    server_url: str,
    api_key: str,
    tmdb_id: int,
    media_type: str,
) -> dict[str, Any]:
    """
    Fetch media details (including title) from Jellyseerr API.

    Args:
        client: httpx client to reuse connection
        server_url: Jellyseerr server URL
        api_key: Jellyseerr API key
        tmdb_id: TMDB ID of the media
        media_type: "movie" or "tv"

    Returns dict with title and other media info, or empty dict on failure.
    """
    endpoint = "movie" if media_type == "movie" else "tv"

    try:
        response = await client.get(
            f"{server_url}/api/v1/{endpoint}/{tmdb_id}",
            headers={"X-Api-Key": api_key},
            params={"language": "en"},
        )
        if response.status_code == 200:
            data: dict[str, Any] = response.json()
            return data
        else:
            logger.warning(
                f"Failed to fetch {media_type} details for TMDB {tmdb_id}: {response.status_code}"
            )
            return {}
    except (httpx.RequestError, httpx.TimeoutException) as e:
        logger.warning(f"Error fetching {media_type} details for TMDB {tmdb_id}: {e}")
        return {}


async def fetch_jellyfin_media(
    server_url: str, api_key: str
) -> list[dict[str, Any]]:
    """
    Fetch all movies and series from Jellyfin API with multi-user watch data.

    This function fetches items from ALL Jellyfin users and aggregates watch data:
    - played = True if ANY user has watched
    - last_played_date = most recent date across all users
    - play_count = sum of all users' play counts

    Based on original_script.py:aggregate_all_user_data
    """
    try:
        return await fetch_all_users_media(server_url, api_key)
    except httpx.HTTPStatusError as e:
        logger.error(f"Jellyfin API error: {e.response.status_code}")
        raise
    except httpx.RequestError as e:
        logger.error(f"Jellyfin connection error: {e}")
        raise


async def fetch_jellyfin_media_with_progress(
    server_url: str, api_key: str, db: AsyncSession, user_id: int
) -> list[dict[str, Any]]:
    """
    Fetch all movies and series from Jellyfin API with progress updates.

    Same as fetch_jellyfin_media but updates sync progress in database
    for frontend polling.
    """
    server_url = server_url.rstrip("/")

    try:
        # Fetch list of users
        users = await fetch_jellyfin_users(server_url, api_key)

        if not users:
            logger.warning("No users found in Jellyfin")
            return []

        total_users = len(users)
        logger.info(f"Found {total_users} Jellyfin users, fetching items for each...")

        # Update progress with total user count
        await update_sync_progress(
            db, user_id,
            current_step="syncing_media",
            current_step_progress=0,
            current_step_total=total_users,
            current_user_name=None
        )

        # Dictionary to store items by ID with watch data from all users
        items_dict: dict[str, dict[str, Any]] = {}

        async with httpx.AsyncClient(timeout=60.0) as client:
            # Process users sequentially to update progress (with some parallelism)
            # Batch users in groups of 3 for better progress visibility
            batch_size = 3
            for batch_start in range(0, total_users, batch_size):
                batch_end = min(batch_start + batch_size, total_users)
                batch_users = users[batch_start:batch_end]

                # Update progress to show first user in current batch
                first_user_name = batch_users[0].get("Name", "Unknown")
                await update_sync_progress(
                    db, user_id,
                    current_step_progress=batch_start + 1,
                    current_user_name=first_user_name
                )

                # Create tasks for this batch
                tasks = [
                    fetch_user_items(
                        client,
                        server_url,
                        api_key,
                        user["Id"],
                        user.get("Name", "Unknown"),
                        batch_start + idx + 1,
                        total_users,
                    )
                    for idx, user in enumerate(batch_users)
                ]

                # Execute batch in parallel
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Process results from this batch
                for user, result in zip(batch_users, results):
                    if isinstance(result, Exception):
                        logger.warning(f"Failed to fetch items for user {user.get('Name', 'Unknown')}: {result}")
                        continue

                    user_items = cast(list[dict[str, Any]], result)

                    for item in user_items:
                        item_id = item.get("Id")
                        if not item_id:
                            continue

                        # First time seeing this item - store it
                        if item_id not in items_dict:
                            # Create a copy without UserData (we'll aggregate UserData separately)
                            item_copy = item.copy()
                            item_copy.pop("UserData", None)
                            items_dict[item_id] = {
                                "item": item_copy,
                                "user_data_list": [],
                            }

                        # Add this user's watch data
                        user_data = item.get("UserData", {})
                        if user_data.get("PlayCount", 0) > 0 or user_data.get("Played", False):
                            items_dict[item_id]["user_data_list"].append(user_data)

        # Convert back to list with aggregated UserData
        result_items: list[dict[str, Any]] = []
        for item_id, data in items_dict.items():
            item = data["item"].copy()
            user_data_list = data["user_data_list"]

            # Aggregate watch data from all users
            aggregated = aggregate_user_watch_data(user_data_list)

            # Create aggregated UserData in Jellyfin format
            item["UserData"] = {
                "Played": aggregated["played"],
                "PlayCount": aggregated["play_count"],
                "LastPlayedDate": aggregated["last_played_date"],
            }

            result_items.append(item)

        logger.info(f"Aggregated {len(result_items)} media items from {total_users} users")
        return result_items

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
    Fetch all requests from Jellyseerr API with pagination and retry on transient failures.

    Based on original_script.py:fetch_jellyseer_requests

    The /api/v1/request endpoint does not include titles in the media object,
    so we make additional calls to /api/v1/movie/{tmdbId} or /api/v1/tv/{tmdbId}
    to fetch the actual titles. Results are cached to avoid duplicate calls.
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

                async def _fetch_page() -> dict[str, Any]:
                    response = await client.get(
                        f"{server_url}/api/v1/request",
                        headers={"X-Api-Key": api_key},
                        params=params,
                    )
                    response.raise_for_status()
                    result: dict[str, Any] = response.json()
                    return result

                data = await retry_with_backoff(_fetch_page, "Jellyseerr")
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

            # Enrich requests with titles from media detail endpoints
            # Use a cache to avoid duplicate lookups for the same TMDB ID
            title_cache: dict[tuple[str, int], dict[str, Any]] = {}

            for req in all_requests:
                media = req.get("media", {})
                tmdb_id = media.get("tmdbId")
                media_type = media.get("mediaType", "")

                if not tmdb_id or not media_type:
                    continue

                cache_key = (media_type, tmdb_id)
                if cache_key not in title_cache:
                    details = await fetch_media_details(
                        client, server_url, api_key, tmdb_id, media_type
                    )
                    title_cache[cache_key] = details

                # Merge title info into the media object
                details = title_cache[cache_key]
                if details:
                    # Movies have 'title', TV shows have 'name'
                    if media_type == "movie":
                        media["title"] = details.get("title")
                        media["originalTitle"] = details.get("originalTitle")
                        media["releaseDate"] = details.get("releaseDate")
                    else:  # tv
                        media["name"] = details.get("name")
                        media["originalName"] = details.get("originalName")
                        media["firstAirDate"] = details.get("firstAirDate")

            logger.info(f"Enriched {len(title_cache)} unique media items with titles")
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


async def fetch_series_seasons(
    client: httpx.AsyncClient,
    server_url: str,
    api_key: str,
    series_id: str,
) -> list[dict[str, Any]]:
    """
    Fetch all seasons for a series from Jellyfin API with retry on transient failures.

    Returns list of season dicts with Id and IndexNumber.
    """
    params = {
        "ParentId": series_id,
        "IncludeItemTypes": "Season",
    }

    async def _fetch() -> list[dict[str, Any]]:
        response = await client.get(
            f"{server_url}/Items",
            headers={"X-Emby-Token": api_key},
            params=params,
        )
        response.raise_for_status()
        data = response.json()
        seasons: list[dict[str, Any]] = data.get("Items", [])
        return seasons

    return await retry_with_backoff(_fetch, "Jellyfin")


async def fetch_season_episodes(
    client: httpx.AsyncClient,
    server_url: str,
    api_key: str,
    season_id: str,
) -> list[dict[str, Any]]:
    """
    Fetch all episodes for a season from Jellyfin API with retry on transient failures.

    Returns list of episode dicts with MediaSources for size calculation.
    """
    params = {
        "ParentId": season_id,
        "IncludeItemTypes": "Episode",
        "Fields": "MediaSources",
    }

    async def _fetch() -> list[dict[str, Any]]:
        response = await client.get(
            f"{server_url}/Items",
            headers={"X-Emby-Token": api_key},
            params=params,
        )
        response.raise_for_status()
        data = response.json()
        episodes: list[dict[str, Any]] = data.get("Items", [])
        return episodes

    return await retry_with_backoff(_fetch, "Jellyfin")


def calculate_season_total_size(episodes: list[dict[str, Any]]) -> int:
    """Calculate total size of all episodes in a season."""
    total_size = 0
    for episode in episodes:
        size = extract_size_from_item(episode)
        if size:
            total_size += size
    return total_size


async def calculate_season_sizes(
    db: AsyncSession,
    user_id: int,
    server_url: str,
    api_key: str,
) -> None:
    """
    Calculate and store largest season sizes for all series in user's cache.

    This function:
    1. Fetches all series from cached_media_items for the user
    2. For each series, fetches seasons from Jellyfin API
    3. For each season, fetches episodes and calculates total size
    4. Stores the largest season size in largest_season_size_bytes

    Args:
        db: Database session
        user_id: User ID
        server_url: Jellyfin server URL
        api_key: Decrypted Jellyfin API key
    """
    server_url = server_url.rstrip("/")

    # Fetch all series from cache
    result = await db.execute(
        select(CachedMediaItem).where(
            CachedMediaItem.user_id == user_id,
            CachedMediaItem.media_type == "Series",
        )
    )
    series_items = result.scalars().all()

    if not series_items:
        logger.info("No series found for user, skipping season size calculation")
        return

    logger.info(f"Calculating season sizes for {len(series_items)} series...")

    async with httpx.AsyncClient(timeout=60.0) as client:
        for series in series_items:
            try:
                # Fetch seasons for this series
                seasons = await fetch_series_seasons(
                    client, server_url, api_key, series.jellyfin_id
                )

                if not seasons:
                    logger.debug(f"No seasons found for series '{series.name}'")
                    continue

                # Calculate size for each season and find the largest
                largest_season_size = 0
                for season in seasons:
                    season_id = season.get("Id")
                    if not season_id:
                        continue

                    episodes = await fetch_season_episodes(
                        client, server_url, api_key, season_id
                    )
                    season_size = calculate_season_total_size(episodes)

                    if season_size > largest_season_size:
                        largest_season_size = season_size

                # Update the series with largest season size
                if largest_season_size > 0:
                    series.largest_season_size_bytes = largest_season_size
                    logger.debug(
                        f"Series '{series.name}': largest season = "
                        f"{largest_season_size / (1024**3):.2f} GB"
                    )

            except (httpx.RequestError, httpx.HTTPStatusError) as e:
                logger.warning(
                    f"Failed to calculate season sizes for series '{series.name}': {e}"
                )
                # Continue to next series on error
                continue

    await db.flush()


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
            jellyseerr_media_id=media.get("id"),  # media.id for deletion (distinct from request.id)
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
    current_step: str | None = None,
    total_steps: int | None = None,
    current_step_progress: int | None = None,
    current_step_total: int | None = None,
    current_user_name: str | None = None,
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
            # Reset progress fields when starting
            sync_status.current_step = current_step
            sync_status.total_steps = total_steps
            sync_status.current_step_progress = None
            sync_status.current_step_total = None
            sync_status.current_user_name = None
        else:
            sync_status.last_sync_completed = now
            sync_status.last_sync_status = status
            sync_status.last_sync_error = error
            sync_status.media_items_count = media_count
            sync_status.requests_count = requests_count
            # Clear progress fields when complete
            sync_status.current_step = None
            sync_status.total_steps = None
            sync_status.current_step_progress = None
            sync_status.current_step_total = None
            sync_status.current_user_name = None
    else:
        sync_status = SyncStatus(
            user_id=user_id,
            last_sync_started=now if started else None,
            last_sync_completed=None if started else now,
            last_sync_status=None if started else status,
            last_sync_error=error,
            media_items_count=media_count,
            requests_count=requests_count,
            current_step=current_step if started else None,
            total_steps=total_steps if started else None,
            current_step_progress=None,
            current_step_total=None,
            current_user_name=None,
        )
        db.add(sync_status)

    await db.flush()


async def update_sync_progress(
    db: AsyncSession,
    user_id: int,
    current_step: str | None = None,
    current_step_progress: int | None = None,
    current_step_total: int | None = None,
    current_user_name: str | None = None,
) -> None:
    """Update sync progress for a user (without changing overall status)."""
    result = await db.execute(
        select(SyncStatus).where(SyncStatus.user_id == user_id)
    )
    sync_status = result.scalar_one_or_none()

    if sync_status:
        if current_step is not None:
            sync_status.current_step = current_step
        if current_step_progress is not None:
            sync_status.current_step_progress = current_step_progress
        if current_step_total is not None:
            sync_status.current_step_total = current_step_total
        if current_user_name is not None:
            sync_status.current_user_name = current_user_name
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

    Updates progress in sync_status table for frontend polling.
    Sends Slack notifications on sync failures.
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

    # Get user email for notifications
    user_result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = user_result.scalar_one_or_none()
    user_email = user.email if user else f"user_{user_id}"

    # Determine total steps (1 for Jellyfin, +1 if Jellyseerr configured)
    has_jellyseerr = settings.jellyseerr_server_url and settings.jellyseerr_api_key_encrypted
    total_steps = 2 if has_jellyseerr else 1

    # Mark sync as started with initial progress
    await update_sync_status(
        db, user_id, "in_progress", started=True,
        current_step="syncing_media", total_steps=total_steps
    )

    media_count = 0
    requests_count = 0
    error_message = None

    try:
        # Fetch and cache Jellyfin data with progress updates
        jellyfin_api_key = decrypt_value(settings.jellyfin_api_key_encrypted)
        items = await fetch_jellyfin_media_with_progress(
            settings.jellyfin_server_url, jellyfin_api_key, db, user_id
        )
        media_count = await cache_media_items(db, user_id, items)
        logger.info(f"Cached {media_count} media items for user {user_id}")

        # Calculate season sizes for series (background task after main sync)
        await update_sync_progress(
            db, user_id, current_step="calculating_sizes",
            current_step_progress=None, current_step_total=None, current_user_name=None
        )
        await calculate_season_sizes(
            db, user_id, settings.jellyfin_server_url, jellyfin_api_key
        )

    except Exception as e:
        error_message = f"Jellyfin sync failed: {str(e)}"
        logger.error(error_message)
        await update_sync_status(
            db, user_id, "failed", error=error_message, media_count=0, requests_count=0
        )
        # Send sync failure notification (fire-and-forget)
        try:
            await send_sync_failure_notification(
                user_email=user_email,
                service="Jellyfin",
                error_message=str(e),
            )
        except Exception:
            pass  # Don't let notification failure affect sync error handling
        return {
            "status": "failed",
            "error": error_message,
            "media_items_synced": 0,
            "requests_synced": 0,
        }

    try:
        # Fetch and cache Jellyseerr data (if configured)
        if settings.jellyseerr_server_url and settings.jellyseerr_api_key_encrypted:
            # Update progress to syncing requests
            await update_sync_progress(
                db, user_id, current_step="syncing_requests",
                current_step_progress=None, current_step_total=None, current_user_name=None
            )

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
        # Send sync failure notification (fire-and-forget)
        try:
            await send_sync_failure_notification(
                user_email=user_email,
                service="Jellyseerr",
                error_message=str(e),
            )
        except Exception:
            pass  # Don't let notification failure affect sync error handling

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
