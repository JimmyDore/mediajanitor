"""Radarr service for API interactions and connection validation."""

import httpx

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import UserSettings
from app.services.encryption import decrypt_value, encrypt_value


async def validate_radarr_connection(server_url: str, api_key: str) -> bool:
    """
    Validate a Radarr connection by making a test API call.

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


async def get_user_radarr_settings(
    db: AsyncSession, user_id: int
) -> UserSettings | None:
    """Get user's Radarr settings from database."""
    result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def save_radarr_settings(
    db: AsyncSession, user_id: int, server_url: str, api_key: str
) -> UserSettings:
    """Save or update user's Radarr settings."""
    # Normalize URL
    server_url = server_url.rstrip("/")

    # Encrypt API key
    encrypted_api_key = encrypt_value(api_key)

    # Check if settings already exist
    settings = await get_user_radarr_settings(db, user_id)

    if settings:
        # Update existing
        settings.radarr_server_url = server_url
        settings.radarr_api_key_encrypted = encrypted_api_key
    else:
        # Create new
        settings = UserSettings(
            user_id=user_id,
            radarr_server_url=server_url,
            radarr_api_key_encrypted=encrypted_api_key,
        )
        db.add(settings)

    await db.flush()
    return settings


def get_decrypted_radarr_api_key(settings: UserSettings) -> str | None:
    """Decrypt and return the Radarr API key from user settings."""
    if settings.radarr_api_key_encrypted:
        return decrypt_value(settings.radarr_api_key_encrypted)
    return None


async def get_radarr_movie_by_tmdb_id(
    server_url: str, api_key: str, tmdb_id: int
) -> int | None:
    """
    Find a Radarr movie by TMDB ID.

    Returns the Radarr movie ID if found, None otherwise.
    """
    server_url = server_url.rstrip("/")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{server_url}/api/v3/movie",
                headers={"X-Api-Key": api_key},
                params={"tmdbId": tmdb_id},
            )
            if response.status_code != 200:
                return None

            movies = response.json()
            if movies and len(movies) > 0:
                movie_id = movies[0].get("id")
                return int(movie_id) if movie_id is not None else None
            return None
    except (httpx.RequestError, httpx.TimeoutException):
        return None


async def delete_radarr_movie(
    server_url: str, api_key: str, radarr_id: int, delete_files: bool = True
) -> bool:
    """
    Delete a movie from Radarr by its Radarr ID.

    Args:
        server_url: Radarr server URL
        api_key: Radarr API key
        radarr_id: The Radarr movie ID
        delete_files: Whether to delete files on disk (default: True)

    Returns True if deletion was successful, False otherwise.
    """
    server_url = server_url.rstrip("/")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(
                f"{server_url}/api/v3/movie/{radarr_id}",
                headers={"X-Api-Key": api_key},
                params={"deleteFiles": str(delete_files).lower()},
            )
            # Radarr returns 200 on successful deletion
            return response.status_code == 200
    except (httpx.RequestError, httpx.TimeoutException):
        return False


async def delete_movie_by_tmdb_id(
    server_url: str, api_key: str, tmdb_id: int, delete_files: bool = True
) -> tuple[bool, str]:
    """
    Delete a movie from Radarr by TMDB ID.

    Args:
        server_url: Radarr server URL
        api_key: Radarr API key
        tmdb_id: The TMDB ID of the movie
        delete_files: Whether to delete files on disk (default: True)

    Returns a tuple of (success: bool, message: str).
    """
    # First, find the Radarr movie ID
    radarr_id = await get_radarr_movie_by_tmdb_id(server_url, api_key, tmdb_id)
    if radarr_id is None:
        return False, f"Movie with TMDB ID {tmdb_id} not found in Radarr"

    # Delete the movie
    success = await delete_radarr_movie(server_url, api_key, radarr_id, delete_files)
    if success:
        return True, "Movie deleted successfully from Radarr"
    return False, "Failed to delete movie from Radarr"
