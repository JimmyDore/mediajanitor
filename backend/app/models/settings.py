"""Pydantic models for settings endpoints."""

from typing import Literal

from pydantic import BaseModel, Field, HttpUrl

# Theme preference type
ThemePreference = Literal["light", "dark", "system"]

# Title language preference type
TitleLanguage = Literal["en", "fr"]


class JellyfinSettingsCreate(BaseModel):
    """Request model for saving Jellyfin settings."""

    server_url: HttpUrl
    api_key: str


class JellyfinSettingsResponse(BaseModel):
    """Response model for Jellyfin settings (without exposing API key)."""

    server_url: str | None
    api_key_configured: bool


class JellyseerrSettingsCreate(BaseModel):
    """Request model for saving Jellyseerr settings."""

    server_url: HttpUrl
    api_key: str


class JellyseerrSettingsResponse(BaseModel):
    """Response model for Jellyseerr settings (without exposing API key)."""

    server_url: str | None
    api_key_configured: bool


class RadarrSettingsCreate(BaseModel):
    """Request model for saving Radarr settings."""

    server_url: HttpUrl
    api_key: str


class RadarrSettingsResponse(BaseModel):
    """Response model for Radarr settings (without exposing API key)."""

    server_url: str | None
    api_key_configured: bool


class SonarrSettingsCreate(BaseModel):
    """Request model for saving Sonarr settings."""

    server_url: HttpUrl
    api_key: str


class SonarrSettingsResponse(BaseModel):
    """Response model for Sonarr settings (without exposing API key)."""

    server_url: str | None
    api_key_configured: bool


class UltraSettingsCreate(BaseModel):
    """Request model for saving Ultra.cc seedbox settings."""

    server_url: HttpUrl
    api_key: str


class UltraSettingsResponse(BaseModel):
    """Response model for Ultra settings (without exposing API key)."""

    server_url: str | None
    api_key_configured: bool
    # Cached stats from last sync
    free_storage_gb: float | None = None
    traffic_available_percent: float | None = None
    last_synced_at: str | None = None  # ISO format datetime
    # Warning thresholds (for dashboard display)
    storage_warning_gb: int | None = None
    traffic_warning_percent: int | None = None


class UltraThresholdsCreate(BaseModel):
    """Request model for saving Ultra.cc warning thresholds."""

    storage_warning_gb: int | None = Field(default=None, ge=1, le=1000)
    traffic_warning_percent: int | None = Field(default=None, ge=1, le=100)


class UltraThresholdsResponse(BaseModel):
    """Response model for Ultra warning thresholds."""

    storage_warning_gb: int
    traffic_warning_percent: int


class SettingsSaveResponse(BaseModel):
    """Response model for successful settings save."""

    success: bool
    message: str


# Analysis Preferences (Thresholds)


class AnalysisPreferencesCreate(BaseModel):
    """Request model for saving analysis preferences (partial update supported)."""

    old_content_months: int | None = Field(default=None, ge=1, le=24)
    min_age_months: int | None = Field(default=None, ge=0, le=12)
    large_movie_size_gb: int | None = Field(default=None, ge=1, le=100)
    large_season_size_gb: int | None = Field(default=None, ge=1, le=100)


class AnalysisPreferencesResponse(BaseModel):
    """Response model for analysis preferences."""

    old_content_months: int
    min_age_months: int
    large_movie_size_gb: int
    large_season_size_gb: int


# Display Preferences


class DisplayPreferencesCreate(BaseModel):
    """Request model for saving display preferences."""

    show_unreleased_requests: bool | None = None
    theme_preference: ThemePreference | None = None
    recently_available_days: int | None = Field(default=None, ge=1, le=30)
    title_language: TitleLanguage | None = None


class DisplayPreferencesResponse(BaseModel):
    """Response model for display preferences."""

    show_unreleased_requests: bool
    theme_preference: ThemePreference
    recently_available_days: int
    title_language: TitleLanguage


# User Nicknames


class NicknameCreate(BaseModel):
    """Request model for creating a nickname mapping."""

    jellyseerr_username: str = Field(..., min_length=1, max_length=255)
    display_name: str = Field(..., min_length=1, max_length=255)


class NicknameUpdate(BaseModel):
    """Request model for updating a nickname mapping."""

    display_name: str = Field(..., min_length=1, max_length=255)


class NicknameItem(BaseModel):
    """Response model for a single nickname mapping."""

    id: int
    jellyseerr_username: str
    display_name: str
    has_jellyseerr_account: bool
    created_at: str  # ISO format datetime


class NicknameListResponse(BaseModel):
    """Response model for nickname list."""

    items: list[NicknameItem]
    total_count: int


class NicknameRefreshResponse(BaseModel):
    """Response model for refreshing nicknames from Jellyfin users."""

    success: bool
    message: str
    new_users_count: int
