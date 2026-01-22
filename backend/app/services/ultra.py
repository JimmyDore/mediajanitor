"""Ultra.cc seedbox service for API interactions."""

import logging
from typing import TypedDict

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import UserSettings
from app.services.encryption import decrypt_value, encrypt_value

logger = logging.getLogger(__name__)


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


class UltraStatsResult(TypedDict):
    """Result from Ultra.cc API stats fetch."""

    free_storage_gb: float
    traffic_available_percentage: float


async def fetch_ultra_stats(url: str, api_key: str) -> UltraStatsResult | None:
    """
    Fetch storage and traffic stats from Ultra.cc API.

    Args:
        url: Ultra.cc API base URL
        api_key: Ultra.cc API key (Bearer token)

    Returns:
        Dict with free_storage_gb and traffic_available_percentage,
        or None if the API call fails.

    API endpoint: {url}/total-stats
    Response structure: service_stats_info.free_storage_gb,
        service_stats_info.traffic_available_percentage
    """
    url = url.rstrip("/")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{url}/total-stats",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            response.raise_for_status()
            data = response.json()

            # Extract stats from response
            service_stats = data.get("service_stats_info", {})
            free_storage_gb = service_stats.get("free_storage_gb")
            traffic_available_percentage = service_stats.get("traffic_available_percentage")

            if free_storage_gb is None or traffic_available_percentage is None:
                logger.warning(f"Ultra API response missing expected fields: {data.keys()}")
                return None

            return {
                "free_storage_gb": float(free_storage_gb),
                "traffic_available_percentage": float(traffic_available_percentage),
            }

    except httpx.HTTPStatusError as e:
        logger.warning(f"Ultra API HTTP error: {e.response.status_code}")
        return None
    except httpx.RequestError as e:
        logger.warning(f"Ultra API request error: {e}")
        return None
    except (ValueError, KeyError, TypeError) as e:
        logger.warning(f"Ultra API response parsing error: {e}")
        return None
