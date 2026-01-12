"""Settings router for user configuration endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import User, get_db
from app.models.settings import (
    JellyfinSettingsCreate,
    JellyfinSettingsResponse,
    JellyseerrSettingsCreate,
    JellyseerrSettingsResponse,
    SettingsSaveResponse,
)
from app.services.auth import get_current_user
from app.services.jellyfin import (
    get_user_jellyfin_settings,
    save_jellyfin_settings,
    validate_jellyfin_connection,
)
from app.services.jellyseerr import (
    get_user_jellyseerr_settings,
    save_jellyseerr_settings,
    validate_jellyseerr_connection,
)

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.post("/jellyfin", response_model=SettingsSaveResponse)
async def save_jellyfin_config(
    settings_data: JellyfinSettingsCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SettingsSaveResponse:
    """Save Jellyfin connection settings after validating the connection."""
    # Convert HttpUrl to string
    server_url = str(settings_data.server_url)

    # Validate connection before saving
    is_valid = await validate_jellyfin_connection(server_url, settings_data.api_key)
    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail="Could not establish connection to Jellyfin server. Please check URL and API key.",
        )

    # Save settings
    await save_jellyfin_settings(
        db, current_user.id, server_url, settings_data.api_key
    )

    return SettingsSaveResponse(
        success=True,
        message="Jellyfin settings saved successfully.",
    )


@router.get("/jellyfin", response_model=JellyfinSettingsResponse)
async def get_jellyfin_config(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JellyfinSettingsResponse:
    """Get current Jellyfin connection settings for the user."""
    settings = await get_user_jellyfin_settings(db, current_user.id)

    if settings and settings.jellyfin_server_url:
        return JellyfinSettingsResponse(
            server_url=settings.jellyfin_server_url,
            api_key_configured=settings.jellyfin_api_key_encrypted is not None,
        )

    return JellyfinSettingsResponse(
        server_url=None,
        api_key_configured=False,
    )


@router.post("/jellyseerr", response_model=SettingsSaveResponse)
async def save_jellyseerr_config(
    settings_data: JellyseerrSettingsCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SettingsSaveResponse:
    """Save Jellyseerr connection settings after validating the connection."""
    # Convert HttpUrl to string
    server_url = str(settings_data.server_url)

    # Validate connection before saving
    is_valid = await validate_jellyseerr_connection(server_url, settings_data.api_key)
    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail="Could not establish connection to Jellyseerr server. Please check URL and API key.",
        )

    # Save settings
    await save_jellyseerr_settings(
        db, current_user.id, server_url, settings_data.api_key
    )

    return SettingsSaveResponse(
        success=True,
        message="Jellyseerr settings saved successfully.",
    )


@router.get("/jellyseerr", response_model=JellyseerrSettingsResponse)
async def get_jellyseerr_config(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JellyseerrSettingsResponse:
    """Get current Jellyseerr connection settings for the user."""
    settings = await get_user_jellyseerr_settings(db, current_user.id)

    if settings and settings.jellyseerr_server_url:
        return JellyseerrSettingsResponse(
            server_url=settings.jellyseerr_server_url,
            api_key_configured=settings.jellyseerr_api_key_encrypted is not None,
        )

    return JellyseerrSettingsResponse(
        server_url=None,
        api_key_configured=False,
    )
