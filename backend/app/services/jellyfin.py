"""Jellyfin service for API interactions and connection validation."""

import httpx

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import UserSettings
from app.services.encryption import decrypt_value, encrypt_value


async def validate_jellyfin_connection(server_url: str, api_key: str) -> bool:
    """
    Validate a Jellyfin connection by making a test API call.

    Returns True if connection is valid, False otherwise.
    """
    # Normalize URL (remove trailing slash)
    server_url = server_url.rstrip("/")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Try to get system info - a simple endpoint that requires authentication
            response = await client.get(
                f"{server_url}/System/Info",
                headers={"X-Emby-Token": api_key},
            )
            return response.status_code == 200
    except (httpx.RequestError, httpx.TimeoutException):
        return False


async def get_user_jellyfin_settings(
    db: AsyncSession, user_id: int
) -> UserSettings | None:
    """Get user's Jellyfin settings from database."""
    result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def save_jellyfin_settings(
    db: AsyncSession, user_id: int, server_url: str, api_key: str
) -> UserSettings:
    """Save or update user's Jellyfin settings."""
    # Normalize URL
    server_url = server_url.rstrip("/")

    # Encrypt API key
    encrypted_api_key = encrypt_value(api_key)

    # Check if settings already exist
    settings = await get_user_jellyfin_settings(db, user_id)

    if settings:
        # Update existing
        settings.jellyfin_server_url = server_url
        settings.jellyfin_api_key_encrypted = encrypted_api_key
    else:
        # Create new
        settings = UserSettings(
            user_id=user_id,
            jellyfin_server_url=server_url,
            jellyfin_api_key_encrypted=encrypted_api_key,
        )
        db.add(settings)

    await db.flush()
    return settings


def get_decrypted_jellyfin_api_key(settings: UserSettings) -> str | None:
    """Decrypt and return the Jellyfin API key from user settings."""
    if settings.jellyfin_api_key_encrypted:
        return decrypt_value(settings.jellyfin_api_key_encrypted)
    return None
