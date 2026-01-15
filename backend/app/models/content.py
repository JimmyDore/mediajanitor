"""Pydantic models for content analysis endpoints."""

from datetime import datetime

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
    expires_at: datetime | None = None  # NULL = permanent (never expires)


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
    expires_at: str | None = None  # ISO format datetime or null for permanent


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


class RecentlyAvailableItem(BaseModel):
    """Response model for a single recently available content item."""

    jellyseerr_id: int
    title: str
    media_type: str  # "movie" or "tv"
    availability_date: str
    requested_by: str | None = None
    display_name: str | None = None  # Resolved from nickname mapping, or same as requested_by


class RecentlyAvailableResponse(BaseModel):
    """Response model for recently available content list."""

    items: list[RecentlyAvailableItem]
    total_count: int


# US-D.3: Unified Issues View models


class ServiceUrls(BaseModel):
    """Service URLs for constructing external links."""

    jellyfin_url: str | None = None
    jellyseerr_url: str | None = None
    radarr_url: str | None = None
    sonarr_url: str | None = None


class ContentIssueItem(BaseModel):
    """Response model for a single content item with issues."""

    jellyfin_id: str
    name: str
    media_type: str  # "Movie" or "Series" or "movie" or "tv"
    production_year: int | None
    size_bytes: int | None
    size_formatted: str
    last_played_date: str | None
    played: bool | None = None  # Whether content has been watched (for accurate "Never" display)
    path: str | None
    date_created: str | None = None  # When content was added to the library (ISO format)
    issues: list[str]  # List of issue types: "old", "large", "language", "request"
    language_issues: list[str] | None = None  # Specific language issues: "missing_en_audio", "missing_fr_audio", "missing_fr_subs"
    tmdb_id: str | None = None  # TMDB ID for external links
    imdb_id: str | None = None  # IMDB ID for external links
    sonarr_title_slug: str | None = None  # Sonarr titleSlug for external links (e.g., "arcane")
    jellyseerr_request_id: int | None = None  # Matching Jellyseerr request ID (for reconciliation)
    # Request-specific fields (only populated for items with "request" issue)
    requested_by: str | None = None  # Who requested it
    request_date: str | None = None  # When it was requested
    missing_seasons: list[int] | None = None  # For TV shows only - which seasons are missing
    release_date: str | None = None  # Movie releaseDate or TV firstAirDate (YYYY-MM-DD)


class ContentIssuesResponse(BaseModel):
    """Response model for unified issues list."""

    items: list[ContentIssueItem]
    total_count: int
    total_size_bytes: int
    total_size_formatted: str
    service_urls: ServiceUrls | None = None  # URLs for external links


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
    tmdb_id: int | None = None  # TMDB ID for external links
    release_date: str | None = None  # Movie releaseDate or TV firstAirDate (YYYY-MM-DD)


class UnavailableRequestsResponse(BaseModel):
    """Response model for unavailable requests list."""

    items: list[UnavailableRequestItem]
    total_count: int
    total_size_bytes: int = 0  # Requests don't have size
    total_size_formatted: str = "0 B"


# US-13.4: Request Whitelist models


class RequestWhitelistAddRequest(BaseModel):
    """Request model for adding a Jellyseerr request to whitelist."""

    jellyseerr_id: int
    title: str
    media_type: str  # "movie" or "tv"
    expires_at: datetime | None = None  # NULL = permanent (never expires)


class RequestWhitelistItem(BaseModel):
    """Response model for a single request whitelist item."""

    id: int
    jellyseerr_id: int
    title: str
    media_type: str  # "movie" or "tv"
    created_at: str
    expires_at: str | None = None  # ISO format datetime or null for permanent


class RequestWhitelistListResponse(BaseModel):
    """Response model for request whitelist list."""

    items: list[RequestWhitelistItem]
    total_count: int


# US-15.4, US-15.5, US-15.6: Delete content models


class DeleteContentRequest(BaseModel):
    """Request model for deleting content from Radarr/Sonarr."""

    tmdb_id: int
    delete_from_arr: bool = True  # Delete from Radarr/Sonarr
    delete_from_jellyseerr: bool = True  # Also delete Jellyseerr request if exists
    jellyseerr_request_id: int | None = None  # Optional: specific Jellyseerr request ID to delete


class DeleteContentResponse(BaseModel):
    """Response model for content deletion."""

    success: bool
    message: str
    arr_deleted: bool = False  # Whether deleted from Radarr/Sonarr
    jellyseerr_deleted: bool = False  # Whether deleted from Jellyseerr


class DeleteRequestResponse(BaseModel):
    """Response model for Jellyseerr request deletion."""

    success: bool
    message: str
