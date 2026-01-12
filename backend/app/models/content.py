"""Pydantic models for content analysis endpoints."""

from pydantic import BaseModel


class OldUnwatchedItem(BaseModel):
    """Response model for a single old/unwatched content item."""

    jellyfin_id: str
    name: str
    media_type: str  # "Movie" or "Series"
    production_year: int | None
    size_bytes: int | None
    size_formatted: str
    last_played_date: str | None
    path: str | None


class OldUnwatchedResponse(BaseModel):
    """Response model for old/unwatched content list."""

    items: list[OldUnwatchedItem]
    total_count: int
    total_size_bytes: int
    total_size_formatted: str


class WhitelistAddRequest(BaseModel):
    """Request model for adding content to whitelist."""

    jellyfin_id: str
    name: str
    media_type: str  # "Movie" or "Series"


class WhitelistAddResponse(BaseModel):
    """Response model for successful whitelist addition."""

    message: str
    jellyfin_id: str
    name: str


class WhitelistItem(BaseModel):
    """Response model for a single whitelist item."""

    id: int
    jellyfin_id: str
    name: str
    media_type: str  # "Movie" or "Series"
    created_at: str


class WhitelistListResponse(BaseModel):
    """Response model for whitelist list."""

    items: list[WhitelistItem]
    total_count: int


class WhitelistRemoveResponse(BaseModel):
    """Response model for successful whitelist removal."""

    message: str
