"""Settings router for user configuration endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import User, UserSettings, get_db
from app.models.settings import (
    AnalysisPreferencesCreate,
    AnalysisPreferencesResponse,
    DisplayPreferencesCreate,
    DisplayPreferencesResponse,
    JellyfinSettingsCreate,
    JellyfinSettingsResponse,
    JellyseerrSettingsCreate,
    JellyseerrSettingsResponse,
    NicknameCreate,
    NicknameItem,
    NicknameListResponse,
    NicknameUpdate,
    RadarrSettingsCreate,
    RadarrSettingsResponse,
    SettingsSaveResponse,
    SonarrSettingsCreate,
    SonarrSettingsResponse,
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
from app.services.radarr import (
    get_user_radarr_settings,
    save_radarr_settings,
    validate_radarr_connection,
)
from app.services.sonarr import (
    get_user_sonarr_settings,
    save_sonarr_settings,
    validate_sonarr_connection,
)
from app.services.nicknames import (
    create_nickname,
    delete_nickname,
    get_nicknames,
    update_nickname,
)

# Default values for analysis preferences
DEFAULT_OLD_CONTENT_MONTHS = 4
DEFAULT_MIN_AGE_MONTHS = 3
DEFAULT_LARGE_MOVIE_SIZE_GB = 13
DEFAULT_LARGE_SEASON_SIZE_GB = 15
# Default value for display preferences
DEFAULT_RECENTLY_AVAILABLE_DAYS = 7

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


# Radarr Endpoints


@router.post("/radarr", response_model=SettingsSaveResponse)
async def save_radarr_config(
    settings_data: RadarrSettingsCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SettingsSaveResponse:
    """Save Radarr connection settings after validating the connection."""
    # Convert HttpUrl to string
    server_url = str(settings_data.server_url)

    # Validate connection before saving
    is_valid = await validate_radarr_connection(server_url, settings_data.api_key)
    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail="Could not establish connection to Radarr server. Please check URL and API key.",
        )

    # Save settings
    await save_radarr_settings(
        db, current_user.id, server_url, settings_data.api_key
    )

    return SettingsSaveResponse(
        success=True,
        message="Radarr settings saved successfully.",
    )


@router.get("/radarr", response_model=RadarrSettingsResponse)
async def get_radarr_config(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RadarrSettingsResponse:
    """Get current Radarr connection settings for the user."""
    settings = await get_user_radarr_settings(db, current_user.id)

    if settings and settings.radarr_server_url:
        return RadarrSettingsResponse(
            server_url=settings.radarr_server_url,
            api_key_configured=settings.radarr_api_key_encrypted is not None,
        )

    return RadarrSettingsResponse(
        server_url=None,
        api_key_configured=False,
    )


# Sonarr Endpoints


@router.post("/sonarr", response_model=SettingsSaveResponse)
async def save_sonarr_config(
    settings_data: SonarrSettingsCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SettingsSaveResponse:
    """Save Sonarr connection settings after validating the connection."""
    # Convert HttpUrl to string
    server_url = str(settings_data.server_url)

    # Validate connection before saving
    is_valid = await validate_sonarr_connection(server_url, settings_data.api_key)
    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail="Could not establish connection to Sonarr server. Please check URL and API key.",
        )

    # Save settings
    await save_sonarr_settings(
        db, current_user.id, server_url, settings_data.api_key
    )

    return SettingsSaveResponse(
        success=True,
        message="Sonarr settings saved successfully.",
    )


@router.get("/sonarr", response_model=SonarrSettingsResponse)
async def get_sonarr_config(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SonarrSettingsResponse:
    """Get current Sonarr connection settings for the user."""
    settings = await get_user_sonarr_settings(db, current_user.id)

    if settings and settings.sonarr_server_url:
        return SonarrSettingsResponse(
            server_url=settings.sonarr_server_url,
            api_key_configured=settings.sonarr_api_key_encrypted is not None,
        )

    return SonarrSettingsResponse(
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
        large_season_size_gb=(
            settings.large_season_size_gb
            if settings and settings.large_season_size_gb is not None
            else DEFAULT_LARGE_SEASON_SIZE_GB
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
    if prefs.large_season_size_gb is not None:
        settings.large_season_size_gb = prefs.large_season_size_gb

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
        settings.large_season_size_gb = None

    return SettingsSaveResponse(
        success=True,
        message="Analysis preferences reset to defaults.",
    )


# Display Preferences Endpoints


@router.get("/display", response_model=DisplayPreferencesResponse)
async def get_display_preferences(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DisplayPreferencesResponse:
    """Get display preferences for the user.

    Returns defaults if not configured.
    """
    result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == current_user.id)
    )
    settings = result.scalar_one_or_none()

    # Return user values or defaults
    # Cast theme_preference to the Literal type (stored as string in DB)
    theme_pref = settings.theme_preference if settings else "system"
    # Validate the stored value is a valid theme
    if theme_pref not in ("light", "dark", "system"):
        theme_pref = "system"
    return DisplayPreferencesResponse(
        show_unreleased_requests=(
            settings.show_unreleased_requests if settings else False
        ),
        theme_preference=theme_pref,  # type: ignore[arg-type]
        recently_available_days=(
            settings.recently_available_days
            if settings and settings.recently_available_days is not None
            else DEFAULT_RECENTLY_AVAILABLE_DAYS
        ),
    )


@router.post("/display", response_model=SettingsSaveResponse)
async def save_display_preferences(
    prefs: DisplayPreferencesCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SettingsSaveResponse:
    """Save display preferences for the user.

    Supports partial updates - only provided fields are updated.
    """
    settings = await _get_or_create_user_settings(db, current_user.id)

    # Only update fields that were provided
    if prefs.show_unreleased_requests is not None:
        settings.show_unreleased_requests = prefs.show_unreleased_requests
    if prefs.theme_preference is not None:
        settings.theme_preference = prefs.theme_preference
    if prefs.recently_available_days is not None:
        settings.recently_available_days = prefs.recently_available_days

    return SettingsSaveResponse(
        success=True,
        message="Display preferences saved successfully.",
    )


# Nickname Endpoints


@router.get("/nicknames", response_model=NicknameListResponse)
async def list_nicknames(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> NicknameListResponse:
    """Get all nickname mappings for the user.

    Nicknames allow mapping Jellyseerr usernames to friendly display names.
    """
    return await get_nicknames(db=db, user_id=current_user.id)


@router.post("/nicknames", response_model=NicknameItem, status_code=201)
async def create_nickname_mapping(
    request: NicknameCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> NicknameItem:
    """Create a new nickname mapping.

    Maps a Jellyseerr username to a friendly display name.
    Each username can only have one mapping per user.
    """
    try:
        entry = await create_nickname(
            db=db,
            user_id=current_user.id,
            jellyseerr_username=request.jellyseerr_username,
            display_name=request.display_name,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=409,
            detail=str(e),
        )

    return NicknameItem(
        id=entry.id,
        jellyseerr_username=entry.jellyseerr_username,
        display_name=entry.display_name,
        has_jellyseerr_account=entry.has_jellyseerr_account,
        created_at=entry.created_at.isoformat() if entry.created_at else "",
    )


@router.put("/nicknames/{nickname_id}", response_model=NicknameItem)
async def update_nickname_mapping(
    nickname_id: int,
    request: NicknameUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> NicknameItem:
    """Update an existing nickname mapping's display name."""
    # First check if entry exists
    result = await get_nicknames(db=db, user_id=current_user.id)
    entry = next((item for item in result.items if item.id == nickname_id), None)

    if not entry:
        raise HTTPException(
            status_code=404,
            detail="Nickname mapping not found",
        )

    # Update the display name
    success = await update_nickname(
        db=db,
        user_id=current_user.id,
        nickname_id=nickname_id,
        display_name=request.display_name,
    )

    if not success:
        raise HTTPException(
            status_code=404,
            detail="Nickname mapping not found",
        )

    return NicknameItem(
        id=entry.id,
        jellyseerr_username=entry.jellyseerr_username,
        display_name=request.display_name,
        has_jellyseerr_account=entry.has_jellyseerr_account,
        created_at=entry.created_at,
    )


@router.delete("/nicknames/{nickname_id}", response_model=SettingsSaveResponse)
async def delete_nickname_mapping(
    nickname_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SettingsSaveResponse:
    """Delete a nickname mapping."""
    success = await delete_nickname(
        db=db,
        user_id=current_user.id,
        nickname_id=nickname_id,
    )

    if not success:
        raise HTTPException(
            status_code=404,
            detail="Nickname mapping not found",
        )

    return SettingsSaveResponse(
        success=True,
        message="Nickname mapping deleted successfully.",
    )
