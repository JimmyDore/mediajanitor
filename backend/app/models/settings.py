"""Pydantic models for settings endpoints."""

from pydantic import BaseModel, HttpUrl


class JellyfinSettingsCreate(BaseModel):
    """Request model for saving Jellyfin settings."""

    server_url: HttpUrl
    api_key: str


class JellyfinSettingsResponse(BaseModel):
    """Response model for Jellyfin settings (without exposing API key)."""

    server_url: str | None
    api_key_configured: bool


class SettingsSaveResponse(BaseModel):
    """Response model for successful settings save."""

    success: bool
    message: str
