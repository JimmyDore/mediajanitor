"""Pydantic models for the API."""

from app.models.content import (
    ContentItem,
    OldUnwatchedResponse,
    LargeMoviesResponse,
    DeleteContentRequest,
    DeleteContentResponse,
)
from app.models.whitelist import (
    WhitelistItemBase,
    WhitelistItemCreate,
    WhitelistItemResponse,
    WhitelistListResponse,
    EpisodeExemptionBase,
    EpisodeExemptionCreate,
    EpisodeExemptionResponse,
    EpisodeExemptionListResponse,
    BulkAddRequest,
    BulkAddResponse,
    DeleteResponse,
)
from app.models.jellyseerr import (
    SeasonInfo,
    InProgressSeason,
    SeasonAnalysis,
    JellyseerrRequest,
    UnavailableRequestsResponse,
    InProgressRequest,
    InProgressRequestsResponse,
    RecentlyAvailableItem,
    RecentlyAvailableResponse,
)

__all__ = [
    # Content
    "ContentItem",
    "OldUnwatchedResponse",
    "LargeMoviesResponse",
    "DeleteContentRequest",
    "DeleteContentResponse",
    # Whitelist
    "WhitelistItemBase",
    "WhitelistItemCreate",
    "WhitelistItemResponse",
    "WhitelistListResponse",
    "EpisodeExemptionBase",
    "EpisodeExemptionCreate",
    "EpisodeExemptionResponse",
    "EpisodeExemptionListResponse",
    "BulkAddRequest",
    "BulkAddResponse",
    "DeleteResponse",
    # Jellyseerr
    "SeasonInfo",
    "InProgressSeason",
    "SeasonAnalysis",
    "JellyseerrRequest",
    "UnavailableRequestsResponse",
    "InProgressRequest",
    "InProgressRequestsResponse",
    "RecentlyAvailableItem",
    "RecentlyAvailableResponse",
]
