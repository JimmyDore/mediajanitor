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


class IssueCategorySummary(BaseModel):
    """Summary for a single issue category."""

    count: int
    total_size_bytes: int = 0
    total_size_formatted: str = "0 B"


class InfoCategorySummary(BaseModel):
    """Summary for a single info category (not an issue)."""

    count: int


class ContentSummaryResponse(BaseModel):
    """Response model for content summary with counts for all issue types and info."""

    old_content: IssueCategorySummary
    large_movies: IssueCategorySummary
    language_issues: IssueCategorySummary
    unavailable_requests: IssueCategorySummary
    # Info categories (not issues)
    recently_available: InfoCategorySummary
    currently_airing: InfoCategorySummary


class RecentlyAvailableItem(BaseModel):
    """Response model for a single recently available content item."""

    jellyseerr_id: int
    title: str
    media_type: str  # "movie" or "tv"
    availability_date: str
    requested_by: str | None = None


class RecentlyAvailableResponse(BaseModel):
    """Response model for recently available content list."""

    items: list[RecentlyAvailableItem]
    total_count: int


class CurrentlyAiringItem(BaseModel):
    """Response model for a single currently airing series."""

    jellyseerr_id: int
    title: str
    in_progress_seasons: list[dict[str, int | str]]


class CurrentlyAiringResponse(BaseModel):
    """Response model for currently airing series list."""

    items: list[CurrentlyAiringItem]
    total_count: int


# US-D.3: Unified Issues View models


class ContentIssueItem(BaseModel):
    """Response model for a single content item with issues."""

    jellyfin_id: str
    name: str
    media_type: str  # "Movie" or "Series"
    production_year: int | None
    size_bytes: int | None
    size_formatted: str
    last_played_date: str | None
    path: str | None
    issues: list[str]  # List of issue types: "old", "large", "language", "request"
    language_issues: list[str] | None = None  # Specific language issues: "missing_en_audio", "missing_fr_audio", "missing_fr_subs"


class ContentIssuesResponse(BaseModel):
    """Response model for unified issues list."""

    items: list[ContentIssueItem]
    total_count: int
    total_size_bytes: int
    total_size_formatted: str


# US-6.1: Unavailable Requests models


class UnavailableRequestItem(BaseModel):
    """Response model for a single unavailable Jellyseerr request."""

    jellyseerr_id: int
    title: str
    media_type: str  # "movie" or "tv"
    requested_by: str | None = None
    request_date: str | None = None
    issues: list[str]  # ["request"]
    missing_seasons: list[int] | None = None  # For TV shows only


class UnavailableRequestsResponse(BaseModel):
    """Response model for unavailable requests list."""

    items: list[UnavailableRequestItem]
    total_count: int
    total_size_bytes: int = 0  # Requests don't have size
    total_size_formatted: str = "0 B"
