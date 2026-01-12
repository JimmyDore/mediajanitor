"""Pydantic models for the API."""

from app.models.user import (
    UserCreate,
    UserLogin,
    UserResponse,
    Token,
)
from app.models.settings import (
    JellyfinSettingsCreate,
    JellyfinSettingsResponse,
    SettingsSaveResponse,
)

__all__ = [
    # User
    "UserCreate",
    "UserLogin",
    "UserResponse",
    "Token",
    # Settings
    "JellyfinSettingsCreate",
    "JellyfinSettingsResponse",
    "SettingsSaveResponse",
]
