"""Jellyseerr service for API interactions and connection validation."""

import httpx

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import UserSettings
from app.services.encryption import decrypt_value, encrypt_value


async def validate_jellyseerr_connection(server_url: str, api_key: str) -> bool:
    """
    Validate a Jellyseerr connection by making a test API call.

    Returns True if connection is valid, False otherwise.
    """
    # Normalize URL (remove trailing slash)
    server_url = server_url.rstrip("/")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Try to get status endpoint - requires authentication
            response = await client.get(
                f"{server_url}/api/v1/status",
                headers={"X-Api-Key": api_key},
            )
            return response.status_code == 200
    except (httpx.RequestError, httpx.TimeoutException):
        return False


async def get_user_jellyseerr_settings(
    db: AsyncSession, user_id: int
) -> UserSettings | None:
    """Get user's Jellyseerr settings from database."""
    result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def save_jellyseerr_settings(
    db: AsyncSession, user_id: int, server_url: str, api_key: str
) -> UserSettings:
    """Save or update user's Jellyseerr settings."""
    # Normalize URL
    server_url = server_url.rstrip("/")

    # Encrypt API key
    encrypted_api_key = encrypt_value(api_key)

    # Check if settings already exist
    settings = await get_user_jellyseerr_settings(db, user_id)

    if settings:
        # Update existing
        settings.jellyseerr_server_url = server_url
        settings.jellyseerr_api_key_encrypted = encrypted_api_key
    else:
        # Create new
        settings = UserSettings(
            user_id=user_id,
            jellyseerr_server_url=server_url,
            jellyseerr_api_key_encrypted=encrypted_api_key,
        )
        db.add(settings)

    await db.flush()
    return settings


def get_decrypted_jellyseerr_api_key(settings: UserSettings) -> str | None:
    """Decrypt and return the Jellyseerr API key from user settings."""
    if settings.jellyseerr_api_key_encrypted:
        return decrypt_value(settings.jellyseerr_api_key_encrypted)
    return None


async def delete_jellyseerr_request(
    server_url: str, api_key: str, request_id: int
) -> tuple[bool, str]:
    """
    Delete a request from Jellyseerr.

    Args:
        server_url: Jellyseerr server URL
        api_key: Jellyseerr API key
        request_id: The Jellyseerr request ID

    Returns a tuple of (success: bool, message: str).
    Jellyseerr returns 204 No Content on successful deletion.
    """
    server_url = server_url.rstrip("/")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.delete(
                f"{server_url}/api/v1/request/{request_id}",
                headers={"X-Api-Key": api_key},
            )
            # Jellyseerr returns 204 No Content on success
            if response.status_code == 204:
                return True, "Request deleted successfully from Jellyseerr"
            if response.status_code == 404:
                return False, f"Request {request_id} not found in Jellyseerr"
            return False, f"Failed to delete request from Jellyseerr (status: {response.status_code})"
    except (httpx.RequestError, httpx.TimeoutException) as e:
        return False, f"Failed to connect to Jellyseerr: {str(e)}"
