"""Pydantic models for the API."""

from app.models.content import (
    OldUnwatchedItem,
    OldUnwatchedResponse,
)
from app.models.settings import (
    JellyfinSettingsCreate,
    JellyfinSettingsResponse,
    SettingsSaveResponse,
)
from app.models.user import (
    Token,
    UserCreate,
    UserLogin,
    UserResponse,
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
    # Content
    "OldUnwatchedItem",
    "OldUnwatchedResponse",
]
