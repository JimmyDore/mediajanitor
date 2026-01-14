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
