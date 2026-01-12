"""Pydantic models for content-related endpoints."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ContentItem(BaseModel):
    """A media item (movie or series) from Jellyfin."""

    id: str
    name: str
    type: str = Field(description="Movie or Series")
    year: Optional[int] = None
    date_created: datetime
    last_played: Optional[datetime] = None
    played: bool = False
    play_count: int = 0
    size: int = Field(description="Size in bytes")
    size_formatted: str = Field(description="Human-readable size")
    path: str
    path_formatted: str = Field(description="Shortened path display")
    is_allowlisted: bool = False

    class Config:
        from_attributes = True


class OldUnwatchedResponse(BaseModel):
    """Response for old/unwatched content endpoint."""

    items: list[ContentItem]
    total_count: int
    total_size: int
    total_size_formatted: str
    protected_count: int
    movies_count: int
    series_count: int
    never_watched_count: int


class LargeMoviesResponse(BaseModel):
    """Response for large movies endpoint."""

    items: list[ContentItem]
    total_count: int
    total_size: int
    total_size_formatted: str
    threshold_gb: int


class DeleteContentRequest(BaseModel):
    """Request to delete content."""

    confirm: bool = Field(description="Must be true to confirm deletion")


class DeleteContentResponse(BaseModel):
    """Response after deleting content."""

    success: bool
    message: str
    deleted_id: Optional[str] = None
