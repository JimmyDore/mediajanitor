"""Pydantic models for settings endpoints."""

from pydantic import BaseModel, Field, HttpUrl


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
