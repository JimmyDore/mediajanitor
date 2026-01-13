"""Settings router for user configuration endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import User, UserSettings, get_db
from app.models.settings import (
    AnalysisPreferencesCreate,
    AnalysisPreferencesResponse,
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

# Default values for analysis preferences
DEFAULT_OLD_CONTENT_MONTHS = 4
DEFAULT_MIN_AGE_MONTHS = 3
DEFAULT_LARGE_MOVIE_SIZE_GB = 13

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


# Analysis Preferences Endpoints


async def _get_or_create_user_settings(
    db: AsyncSession, user_id: int
) -> UserSettings:
    """Get existing user settings or create new one with defaults."""
    result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == user_id)
    )
    settings = result.scalar_one_or_none()

    if not settings:
        settings = UserSettings(user_id=user_id)
        db.add(settings)
        await db.flush()

    return settings


@router.get("/analysis", response_model=AnalysisPreferencesResponse)
async def get_analysis_preferences(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AnalysisPreferencesResponse:
    """Get analysis preferences (thresholds) for the user.

    Returns defaults if not configured.
    """
    result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == current_user.id)
    )
    settings = result.scalar_one_or_none()

    # Return user values or defaults
    return AnalysisPreferencesResponse(
        old_content_months=(
            settings.old_content_months
            if settings and settings.old_content_months is not None
            else DEFAULT_OLD_CONTENT_MONTHS
        ),
        min_age_months=(
            settings.min_age_months
            if settings and settings.min_age_months is not None
            else DEFAULT_MIN_AGE_MONTHS
        ),
        large_movie_size_gb=(
            settings.large_movie_size_gb
            if settings and settings.large_movie_size_gb is not None
            else DEFAULT_LARGE_MOVIE_SIZE_GB
        ),
    )


@router.post("/analysis", response_model=SettingsSaveResponse)
async def save_analysis_preferences(
    prefs: AnalysisPreferencesCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SettingsSaveResponse:
    """Save analysis preferences (thresholds) for the user.

    Supports partial updates - only provided fields are updated.
    """
    settings = await _get_or_create_user_settings(db, current_user.id)

    # Only update fields that were provided
    if prefs.old_content_months is not None:
        settings.old_content_months = prefs.old_content_months
    if prefs.min_age_months is not None:
        settings.min_age_months = prefs.min_age_months
    if prefs.large_movie_size_gb is not None:
        settings.large_movie_size_gb = prefs.large_movie_size_gb

    return SettingsSaveResponse(
        success=True,
        message="Analysis preferences saved successfully.",
    )


@router.delete("/analysis", response_model=SettingsSaveResponse)
async def reset_analysis_preferences(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SettingsSaveResponse:
    """Reset analysis preferences to defaults."""
    result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == current_user.id)
    )
    settings = result.scalar_one_or_none()

    if settings:
        settings.old_content_months = None
        settings.min_age_months = None
        settings.large_movie_size_gb = None

    return SettingsSaveResponse(
        success=True,
        message="Analysis preferences reset to defaults.",
    )
