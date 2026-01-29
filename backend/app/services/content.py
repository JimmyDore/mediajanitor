"""Content analysis service - facade module for backwards compatibility.

This module re-exports all public functions from the refactored modules:
- whitelist.py: All whitelist CRUD operations
- content_analysis.py: Content analysis functions (is_old_or_unwatched, is_large_movie, etc.)
- content_queries.py: Query functions (get_content_summary, get_content_issues, get_library, etc.)
- content_cache.py: Cache management functions (delete/lookup cached items)

Import from this module for backwards compatibility, or import directly from
the specific modules for more explicit dependencies.
"""

# Re-export types and constants from content_analysis
from app.services.content_analysis import (
    ENGLISH_CODES,
    FILTER_FUTURE_RELEASES,
    FILTER_RECENT_RELEASES,
    FRENCH_CODES,
    LARGE_MOVIE_SIZE_THRESHOLD_GB,
    LARGE_SEASON_SIZE_THRESHOLD_GB,
    MIN_AGE_MONTHS,
    # Constants
    OLD_CONTENT_MONTHS_CUTOFF,
    RECENT_RELEASE_MONTHS_CUTOFF,
    UNAVAILABLE_STATUS_CODES,
    # Types
    LanguageCheckResult,
    UserThresholds,
    check_audio_languages,
    extract_provider_ids,
    # Utility functions
    format_size,
    get_item_issues,
    get_language_issues_list,
    # User thresholds
    get_user_thresholds,
    has_language_issues,
    is_large_movie,
    is_large_series,
    # Analysis functions
    is_old_or_unwatched,
    is_unavailable_request,
    parse_jellyfin_datetime,
)

# Re-export cache management functions
from app.services.content_cache import (
    delete_cached_jellyseerr_request_by_id,
    delete_cached_jellyseerr_request_by_tmdb_id,
    delete_cached_media_by_tmdb_id,
    get_user_settings,
    lookup_jellyseerr_media_by_request_id,
    lookup_jellyseerr_media_by_tmdb,
)

# Re-export query functions
from app.services.content_queries import (
    # Constants
    DEFAULT_RECENTLY_AVAILABLE_DAYS,
    # Internal types (used by some callers)
    EpisodeAddition,
    SeasonEpisodeDetails,
    # Issues
    get_content_issues,
    # Summary
    get_content_summary,
    # Library
    get_library,
    # Nickname helpers
    get_nickname_map,
    # Old/unwatched content
    get_old_unwatched_content,
    get_recently_available,
    # Recently available
    get_recently_available_count,
    get_unavailable_requests,
    # Unavailable requests
    get_unavailable_requests_count,
    # User settings helpers
    get_user_recently_available_days,
    get_user_show_unreleased_setting,
    # Episode grouping
    group_episodes_for_display,
    resolve_display_name,
)

# Re-export all whitelist functions
from app.services.whitelist import (
    # Episode language exempt
    add_episode_language_exempt,
    # French-only whitelist
    add_to_french_only_whitelist,
    # Language-exempt whitelist
    add_to_language_exempt_whitelist,
    # Large content whitelist
    add_to_large_whitelist,
    # Request whitelist
    add_to_request_whitelist,
    # Content whitelist
    add_to_whitelist,
    get_episode_exempt_set,
    get_episode_language_exempt,
    get_french_only_ids,
    get_french_only_whitelist,
    get_language_exempt_ids,
    get_language_exempt_whitelist,
    get_large_whitelist,
    get_large_whitelist_ids,
    get_request_whitelist,
    get_request_whitelist_ids,
    get_whitelist,
    get_whitelist_ids,
    remove_episode_language_exempt,
    remove_from_french_only_whitelist,
    remove_from_language_exempt_whitelist,
    remove_from_large_whitelist,
    remove_from_request_whitelist,
    remove_from_whitelist,
)

# __all__ for explicit exports
__all__ = [
    # Types
    "LanguageCheckResult",
    "UserThresholds",
    "SeasonEpisodeDetails",
    "EpisodeAddition",
    # Cache management
    "get_user_settings",
    "lookup_jellyseerr_media_by_tmdb",
    "lookup_jellyseerr_media_by_request_id",
    "delete_cached_media_by_tmdb_id",
    "delete_cached_jellyseerr_request_by_tmdb_id",
    "delete_cached_jellyseerr_request_by_id",
    # Constants
    "OLD_CONTENT_MONTHS_CUTOFF",
    "MIN_AGE_MONTHS",
    "LARGE_MOVIE_SIZE_THRESHOLD_GB",
    "LARGE_SEASON_SIZE_THRESHOLD_GB",
    "FILTER_FUTURE_RELEASES",
    "FILTER_RECENT_RELEASES",
    "RECENT_RELEASE_MONTHS_CUTOFF",
    "UNAVAILABLE_STATUS_CODES",
    "ENGLISH_CODES",
    "FRENCH_CODES",
    "DEFAULT_RECENTLY_AVAILABLE_DAYS",
    # Utility functions
    "format_size",
    "parse_jellyfin_datetime",
    "extract_provider_ids",
    # User settings
    "get_user_thresholds",
    "get_user_recently_available_days",
    "get_user_show_unreleased_setting",
    # Analysis functions
    "is_old_or_unwatched",
    "is_large_movie",
    "is_large_series",
    "check_audio_languages",
    "has_language_issues",
    "get_language_issues_list",
    "is_unavailable_request",
    "get_item_issues",
    # Content whitelist
    "add_to_whitelist",
    "get_whitelist",
    "remove_from_whitelist",
    "get_whitelist_ids",
    # French-only whitelist
    "add_to_french_only_whitelist",
    "get_french_only_whitelist",
    "remove_from_french_only_whitelist",
    "get_french_only_ids",
    # Language-exempt whitelist
    "add_to_language_exempt_whitelist",
    "get_language_exempt_whitelist",
    "remove_from_language_exempt_whitelist",
    "get_language_exempt_ids",
    # Episode language exempt
    "add_episode_language_exempt",
    "get_episode_language_exempt",
    "remove_episode_language_exempt",
    "get_episode_exempt_set",
    # Large content whitelist
    "add_to_large_whitelist",
    "get_large_whitelist",
    "remove_from_large_whitelist",
    "get_large_whitelist_ids",
    # Request whitelist
    "add_to_request_whitelist",
    "get_request_whitelist",
    "remove_from_request_whitelist",
    "get_request_whitelist_ids",
    # Nickname helpers
    "get_nickname_map",
    "resolve_display_name",
    # Query functions
    "get_old_unwatched_content",
    "get_content_summary",
    "get_content_issues",
    "get_recently_available_count",
    "get_recently_available",
    "get_unavailable_requests_count",
    "get_unavailable_requests",
    "get_library",
    "group_episodes_for_display",
]
