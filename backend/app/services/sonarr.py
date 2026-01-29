"""Sonarr service for API interactions and connection validation."""

from datetime import UTC, datetime, timedelta
from typing import Any, TypedDict

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import UserSettings
from app.services.encryption import decrypt_value, encrypt_value


class EpisodeHistoryEntry(TypedDict):
    """Episode download history entry from Sonarr."""

    season: int
    episode: int
    title: str
    added_at: str


async def validate_sonarr_connection(server_url: str, api_key: str) -> bool:
    """
    Validate a Sonarr connection by making a test API call.

    Returns True if connection is valid, False otherwise.
    """
    # Normalize URL (remove trailing slash)
    server_url = server_url.rstrip("/")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Try to get system status - requires authentication
            response = await client.get(
                f"{server_url}/api/v3/system/status",
                headers={"X-Api-Key": api_key},
            )
            return response.status_code == 200
    except (httpx.RequestError, httpx.TimeoutException):
        return False


async def get_user_sonarr_settings(db: AsyncSession, user_id: int) -> UserSettings | None:
    """Get user's Sonarr settings from database."""
    result = await db.execute(select(UserSettings).where(UserSettings.user_id == user_id))
    return result.scalar_one_or_none()


async def save_sonarr_settings(
    db: AsyncSession, user_id: int, server_url: str, api_key: str
) -> UserSettings:
    """Save or update user's Sonarr settings."""
    # Normalize URL
    server_url = server_url.rstrip("/")

    # Encrypt API key
    encrypted_api_key = encrypt_value(api_key)

    # Check if settings already exist
    settings = await get_user_sonarr_settings(db, user_id)

    if settings:
        # Update existing
        settings.sonarr_server_url = server_url
        settings.sonarr_api_key_encrypted = encrypted_api_key
    else:
        # Create new
        settings = UserSettings(
            user_id=user_id,
            sonarr_server_url=server_url,
            sonarr_api_key_encrypted=encrypted_api_key,
        )
        db.add(settings)

    await db.flush()
    return settings


def get_decrypted_sonarr_api_key(settings: UserSettings) -> str | None:
    """Decrypt and return the Sonarr API key from user settings."""
    if settings.sonarr_api_key_encrypted:
        return decrypt_value(settings.sonarr_api_key_encrypted)
    return None


async def get_sonarr_series_by_tmdb_id(server_url: str, api_key: str, tmdb_id: int) -> int | None:
    """
    Find a Sonarr series by TMDB ID.

    Sonarr doesn't have a direct TMDB filter, so we fetch all series
    and search for the matching tmdbId.

    Returns the Sonarr series ID if found, None otherwise.
    """
    server_url = server_url.rstrip("/")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{server_url}/api/v3/series",
                headers={"X-Api-Key": api_key},
            )
            if response.status_code != 200:
                return None

            series_list = response.json()
            for series in series_list:
                if series.get("tmdbId") == tmdb_id:
                    series_id = series.get("id")
                    return int(series_id) if series_id is not None else None
            return None
    except (httpx.RequestError, httpx.TimeoutException):
        return None


async def get_sonarr_tmdb_to_slug_map(server_url: str, api_key: str) -> dict[int, str]:
    """
    Build a mapping from TMDB ID to Sonarr titleSlug.

    Sonarr's web UI uses titleSlug in URLs (e.g., /series/arcane),
    not internal IDs. This map allows us to build correct external links.

    Returns dict mapping tmdb_id -> titleSlug
    """
    server_url = server_url.rstrip("/")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{server_url}/api/v3/series",
                headers={"X-Api-Key": api_key},
            )
            if response.status_code != 200:
                return {}

            series_list = response.json()
            tmdb_to_slug: dict[int, str] = {}
            for series in series_list:
                tmdb_id = series.get("tmdbId")
                title_slug = series.get("titleSlug")
                if tmdb_id is not None and title_slug:
                    tmdb_to_slug[int(tmdb_id)] = str(title_slug)
            return tmdb_to_slug
    except (httpx.RequestError, httpx.TimeoutException):
        return {}


async def delete_sonarr_series(
    server_url: str, api_key: str, sonarr_id: int, delete_files: bool = True
) -> bool:
    """
    Delete a series from Sonarr by its Sonarr ID.

    Args:
        server_url: Sonarr server URL
        api_key: Sonarr API key
        sonarr_id: The Sonarr series ID
        delete_files: Whether to delete files on disk (default: True)

    Returns True if deletion was successful, False otherwise.
    """
    server_url = server_url.rstrip("/")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(
                f"{server_url}/api/v3/series/{sonarr_id}",
                headers={"X-Api-Key": api_key},
                params={"deleteFiles": str(delete_files).lower()},
            )
            # Sonarr returns 200 on successful deletion
            return response.status_code == 200
    except (httpx.RequestError, httpx.TimeoutException):
        return False


async def delete_series_by_tmdb_id(
    server_url: str, api_key: str, tmdb_id: int, delete_files: bool = True
) -> tuple[bool, str]:
    """
    Delete a series from Sonarr by TMDB ID.

    Args:
        server_url: Sonarr server URL
        api_key: Sonarr API key
        tmdb_id: The TMDB ID of the series
        delete_files: Whether to delete files on disk (default: True)

    Returns a tuple of (success: bool, message: str).
    """
    # First, find the Sonarr series ID
    sonarr_id = await get_sonarr_series_by_tmdb_id(server_url, api_key, tmdb_id)
    if sonarr_id is None:
        return False, f"Series with TMDB ID {tmdb_id} not found in Sonarr"

    # Delete the series
    success = await delete_sonarr_series(server_url, api_key, sonarr_id, delete_files)
    if success:
        return True, "Series deleted successfully from Sonarr"
    return False, "Failed to delete series from Sonarr"


async def get_sonarr_history_since(
    server_url: str, api_key: str, days_back: int = 7
) -> dict[int, list[EpisodeHistoryEntry]]:
    """
    Fetch download history from Sonarr since a specific date.

    Uses Sonarr's history/since endpoint to get episode download events.
    Returns a map of TMDB ID -> list of episode additions.

    Args:
        server_url: Sonarr server URL
        api_key: Sonarr API key
        days_back: Number of days to look back (default: 7)

    Returns:
        Dict mapping TMDB ID to list of EpisodeHistoryEntry dicts
        Returns empty dict on any error (graceful degradation)
    """
    server_url = server_url.rstrip("/")

    # Calculate cutoff date
    cutoff_date = datetime.now(UTC) - timedelta(days=days_back)
    date_param = cutoff_date.strftime("%Y-%m-%dT%H:%M:%SZ")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{server_url}/api/v3/history/since",
                headers={"X-Api-Key": api_key},
                params={
                    "date": date_param,
                    "eventType": "downloadFolderImported",
                    "includeSeries": "true",
                    "includeEpisode": "true",
                },
            )
            if response.status_code != 200:
                return {}

            history_items: list[dict[str, Any]] = response.json()

            # Build map: tmdb_id -> list of episode additions
            result: dict[int, list[EpisodeHistoryEntry]] = {}

            for item in history_items:
                series = item.get("series", {})
                tmdb_id = series.get("tmdbId")

                # Skip entries without TMDB ID
                if tmdb_id is None:
                    continue

                episode_data = item.get("episode", {})

                entry: EpisodeHistoryEntry = {
                    "season": episode_data.get("seasonNumber", 0),
                    "episode": episode_data.get("episodeNumber", 0),
                    "title": episode_data.get("title", "Unknown"),
                    "added_at": item.get("date", ""),
                }

                if tmdb_id not in result:
                    result[tmdb_id] = []

                result[tmdb_id].append(entry)

            return result

    except (httpx.RequestError, httpx.TimeoutException):
        return {}
