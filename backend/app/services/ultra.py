"""Ultra.cc seedbox service for API interactions."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import UserSettings
from app.services.encryption import decrypt_value, encrypt_value


async def get_user_ultra_settings(db: AsyncSession, user_id: int) -> UserSettings | None:
    """Get user's Ultra settings from database."""
    result = await db.execute(select(UserSettings).where(UserSettings.user_id == user_id))
    return result.scalar_one_or_none()


async def save_ultra_settings(
    db: AsyncSession, user_id: int, server_url: str, api_key: str
) -> UserSettings:
    """Save or update user's Ultra.cc settings."""
    # Normalize URL
    server_url = server_url.rstrip("/")

    # Encrypt API key
    encrypted_api_key = encrypt_value(api_key)

    # Check if settings already exist
    settings = await get_user_ultra_settings(db, user_id)

    if settings:
        # Update existing
        settings.ultra_api_url = server_url
        settings.ultra_api_key_encrypted = encrypted_api_key
    else:
        # Create new
        settings = UserSettings(
            user_id=user_id,
            ultra_api_url=server_url,
            ultra_api_key_encrypted=encrypted_api_key,
        )
        db.add(settings)

    await db.flush()
    return settings


def get_decrypted_ultra_api_key(settings: UserSettings) -> str | None:
    """Decrypt and return the Ultra API key from user settings."""
    if settings.ultra_api_key_encrypted:
        return decrypt_value(settings.ultra_api_key_encrypted)
    return None
