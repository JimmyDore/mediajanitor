"""Pydantic models for settings endpoints."""

from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


# Theme preference type
ThemePreference = Literal["light", "dark", "system"]


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


class AnalysisPreferencesResponse(BaseModel):
    """Response model for analysis preferences."""

    old_content_months: int
    min_age_months: int
    large_movie_size_gb: int


# Display Preferences


class DisplayPreferencesCreate(BaseModel):
    """Request model for saving display preferences."""

    show_unreleased_requests: bool | None = None
    theme_preference: ThemePreference | None = None
    recently_available_days: int | None = Field(default=None, ge=1, le=30)


class DisplayPreferencesResponse(BaseModel):
    """Response model for display preferences."""

    show_unreleased_requests: bool
    theme_preference: ThemePreference
    recently_available_days: int
