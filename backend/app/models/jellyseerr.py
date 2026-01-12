"""Pydantic models for Jellyseerr-related endpoints."""

from datetime import datetime, date
from typing import Optional

from pydantic import BaseModel, Field


class SeasonInfo(BaseModel):
    """Information about a TV season."""

    season_number: int
    name: str = ""
    air_date: Optional[str] = None
    episode_count: int = 0
    status: Optional[int] = None


class InProgressSeason(BaseModel):
    """Information about an in-progress (currently airing) season."""

    season_number: int
    name: str = ""
    episodes_aired: int = 0
    total_episodes: int = 0


class SeasonAnalysis(BaseModel):
    """Analysis of TV series seasons availability."""

    analysis_available: bool = False
    title: str = ""
    missing_seasons: list[SeasonInfo] = Field(default_factory=list)
    available_seasons: list[SeasonInfo] = Field(default_factory=list)
    future_seasons: list[SeasonInfo] = Field(default_factory=list)
    in_progress_seasons: list[InProgressSeason] = Field(default_factory=list)
    total_seasons: int = 0
    total_released_seasons: int = 0
    is_complete_for_released: bool = False
    summary: str = ""


class JellyseerrRequest(BaseModel):
    """A request from Jellyseerr."""

    id: int
    status: int
    title: str
    type: str = Field(description="movie or tv")
    release_date: Optional[str] = None
    requested_by: str
    created_at: datetime
    tmdb_id: Optional[int] = None
    season_analysis: Optional[SeasonAnalysis] = None


class UnavailableRequestsResponse(BaseModel):
    """Response for unavailable requests endpoint."""

    items: list[JellyseerrRequest]
    total_count: int
    future_releases_filtered: int = 0
    recent_releases_filtered: int = 0


class InProgressRequest(JellyseerrRequest):
    """A request with in-progress (currently airing) seasons."""

    in_progress_seasons: list[InProgressSeason] = Field(default_factory=list)


class InProgressRequestsResponse(BaseModel):
    """Response for in-progress requests endpoint."""

    items: list[InProgressRequest]
    total_count: int


class RecentlyAvailableItem(BaseModel):
    """An item that recently became available."""

    id: int
    title: str
    type: str
    requested_by: str
    availability_date: date
    available_seasons: list[int] = Field(default_factory=list)
    recent_episodes: dict[int, list[int]] = Field(default_factory=dict)


class RecentlyAvailableResponse(BaseModel):
    """Response for recently available endpoint."""

    items: list[RecentlyAvailableItem]
    total_count: int
    grouped_by_date: dict[str, list[RecentlyAvailableItem]] = Field(default_factory=dict)
