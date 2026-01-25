"""Content analysis functions for detecting issues in media content."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, TypedDict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import CachedJellyseerrRequest, CachedMediaItem, UserSettings
from app.models.content import ProblematicEpisode


class LanguageCheckResult(TypedDict):
    """Type for check_audio_languages return value."""

    has_english: bool
    has_french: bool
    has_french_subs: bool
    missing_languages: list[str]


@dataclass
class UserThresholds:
    """User's analysis thresholds."""

    old_content_months: int
    min_age_months: int
    large_movie_size_gb: int
    large_season_size_gb: int


# ============================================================================
# Constants
# ============================================================================

# Hardcoded thresholds per acceptance criteria
OLD_CONTENT_MONTHS_CUTOFF = 4  # Content not watched in 4+ months
MIN_AGE_MONTHS = 3  # Don't flag content added recently
LARGE_MOVIE_SIZE_THRESHOLD_GB = 13  # Movies larger than 13GB
LARGE_SEASON_SIZE_THRESHOLD_GB = 15  # Series if any season exceeds this size

# Unavailable requests configuration (from original script)
FILTER_FUTURE_RELEASES = True  # Filter out content not yet released
FILTER_RECENT_RELEASES = True  # Filter out content released recently
RECENT_RELEASE_MONTHS_CUTOFF = 3  # Don't flag content released < 3 months ago

# Jellyseerr status codes
# 0 = Unknown, 1 = Pending, 2 = Approved, 3 = Processing, 4 = Partially Available, 5 = Available
UNAVAILABLE_STATUS_CODES = {0, 1, 2, 4}  # Status codes for unavailable requests

# Language code variants recognized by the system
ENGLISH_CODES = {"eng", "en", "english"}
FRENCH_CODES = {"fre", "fr", "french", "fra"}


# ============================================================================
# Utility Functions
# ============================================================================


def format_size(size_bytes: int | None) -> str:
    """Format size in bytes to human readable format."""
    if size_bytes is None or size_bytes == 0:
        return "Unknown size"

    size = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024.0:
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024.0

    return f"{size:.1f} PB"


def parse_jellyfin_datetime(date_str: str | None) -> datetime | None:
    """Parse Jellyfin datetime string to datetime object."""
    if not date_str:
        return None

    try:
        # Try ISO format with timezone
        if date_str.endswith("Z"):
            date_str = date_str[:-1] + "+00:00"
        return datetime.fromisoformat(date_str)
    except (ValueError, TypeError):
        return None


def extract_provider_ids(item: CachedMediaItem) -> tuple[str | None, str | None]:
    """Extract TMDB and IMDB IDs from a media item's raw_data.

    Jellyfin stores provider IDs in ProviderIds dict with keys like:
    - "Tmdb": "12345"
    - "Imdb": "tt1234567"

    Returns:
        Tuple of (tmdb_id, imdb_id) - strings or None if not present
    """
    raw_data = item.raw_data
    if not raw_data:
        return None, None

    provider_ids = raw_data.get("ProviderIds", {})
    if not provider_ids:
        return None, None

    tmdb_id = provider_ids.get("Tmdb")
    imdb_id = provider_ids.get("Imdb")

    return tmdb_id, imdb_id


# ============================================================================
# User Thresholds
# ============================================================================


async def get_user_thresholds(db: AsyncSession, user_id: int) -> UserThresholds:
    """Get user's analysis thresholds, falling back to defaults if not configured."""
    result = await db.execute(select(UserSettings).where(UserSettings.user_id == user_id))
    settings = result.scalar_one_or_none()

    return UserThresholds(
        old_content_months=(
            settings.old_content_months
            if settings and settings.old_content_months is not None
            else OLD_CONTENT_MONTHS_CUTOFF
        ),
        min_age_months=(
            settings.min_age_months
            if settings and settings.min_age_months is not None
            else MIN_AGE_MONTHS
        ),
        large_movie_size_gb=(
            settings.large_movie_size_gb
            if settings and settings.large_movie_size_gb is not None
            else LARGE_MOVIE_SIZE_THRESHOLD_GB
        ),
        large_season_size_gb=(
            settings.large_season_size_gb
            if settings and settings.large_season_size_gb is not None
            else LARGE_SEASON_SIZE_THRESHOLD_GB
        ),
    )


# ============================================================================
# Old/Unwatched Content Analysis
# ============================================================================


def is_old_or_unwatched(
    item: CachedMediaItem,
    months_cutoff: int = OLD_CONTENT_MONTHS_CUTOFF,
    min_age_months: int = MIN_AGE_MONTHS,
) -> bool:
    """Check if an item qualifies as old/unwatched content.

    Returns True if:
    - Item was never watched AND was added more than min_age_months ago
    - Item was watched but last played more than months_cutoff ago

    Note: min_age_months only applies to UNPLAYED items (per original script logic).
    Played items are checked against last_played_date regardless of when added.
    """
    now = datetime.now(UTC)
    cutoff_date = now - timedelta(days=months_cutoff * 30)
    min_age_date = now - timedelta(days=min_age_months * 30)

    # Check if item was added recently (for unplayed items check)
    date_created = parse_jellyfin_datetime(item.date_created)
    item_age_ok = True
    if date_created:
        # Make timezone-aware if not already
        if date_created.tzinfo is None:
            date_created = date_created.replace(tzinfo=UTC)
        if date_created > min_age_date:
            item_age_ok = False  # Item is too new

    # Never played - only include if item is old enough (min_age check)
    if not item.played:
        # min_age_months only applies to unplayed items
        return item_age_ok

    # Played but no last_played_date (treat as old)
    # Note: min_age check does NOT apply to played items
    if not item.last_played_date:
        return True

    # Check if last played date is older than cutoff
    last_played = parse_jellyfin_datetime(item.last_played_date)
    if last_played:
        # Make timezone-aware if not already
        if last_played.tzinfo is None:
            last_played = last_played.replace(tzinfo=UTC)
        if last_played < cutoff_date:
            return True

    return False


# ============================================================================
# Large Content Analysis
# ============================================================================


def is_large_movie(
    item: CachedMediaItem,
    threshold_gb: int = LARGE_MOVIE_SIZE_THRESHOLD_GB,
) -> bool:
    """Check if an item is a large movie.

    Args:
        item: The media item to check
        threshold_gb: Size threshold in GB (default: 13)

    Returns True if:
    - Item is a Movie (not Series)
    - Size meets or exceeds threshold_gb

    Note: Uses >= to match original_script.py list_large_movies() behavior.
    """
    if item.media_type != "Movie":
        return False

    if item.size_bytes is None:
        return False

    threshold_bytes = threshold_gb * 1024 * 1024 * 1024
    return item.size_bytes >= threshold_bytes


def is_large_series(
    item: CachedMediaItem,
    threshold_gb: int = LARGE_SEASON_SIZE_THRESHOLD_GB,
) -> bool:
    """Check if an item is a large series (based on largest season size).

    Args:
        item: The media item to check
        threshold_gb: Size threshold in GB (default: 15)

    Returns True if:
    - Item is a Series (not Movie)
    - largest_season_size_bytes meets or exceeds threshold_gb

    Note: Uses >= to match is_large_movie() behavior.
    """
    if item.media_type != "Series":
        return False

    if item.largest_season_size_bytes is None:
        return False

    threshold_bytes = threshold_gb * 1024 * 1024 * 1024
    return item.largest_season_size_bytes >= threshold_bytes


# ============================================================================
# Language Analysis
# ============================================================================


def check_audio_languages(item: CachedMediaItem) -> LanguageCheckResult:
    """Check if item has English and French audio tracks.

    Based on original_script.py:check_audio_languages

    For TV series: Uses cached language_check_result from sync (which aggregates
    all episode audio tracks). This is essential because series-level metadata
    doesn't contain episode audio tracks.

    For movies: Uses cached language_check_result if available, otherwise falls
    back to parsing raw_data.MediaSources for backwards compatibility.

    Returns dict with:
    - has_english: bool
    - has_french: bool
    - has_french_subs: bool
    - missing_languages: list[str] - specific issues found
    """
    # US-52.2: Use cached language_check_result when available
    # This is essential for TV series where episode-level audio tracks are
    # not available in series metadata - we must use data from sync
    if item.language_check_result:
        cached = item.language_check_result
        return {
            "has_english": cached.get("has_english", True),
            "has_french": cached.get("has_french", True),
            "has_french_subs": cached.get("has_french_subs", True),
            "missing_languages": cached.get("missing_languages", []),
        }

    # Fallback: Parse raw_data for movies without cached data (backwards compatibility)
    result: LanguageCheckResult = {
        "has_english": False,
        "has_french": False,
        "has_french_subs": False,
        "missing_languages": [],
    }

    raw_data = item.raw_data
    if not raw_data:
        # No raw data - can't check languages, assume OK
        result["has_english"] = True
        result["has_french"] = True
        return result

    media_sources = raw_data.get("MediaSources", [])
    if not media_sources:
        # No media sources - can't check, assume OK
        result["has_english"] = True
        result["has_french"] = True
        return result

    # Get the first media source
    media_source = media_sources[0]
    media_streams = media_source.get("MediaStreams", [])

    for stream in media_streams:
        stream_type = stream.get("Type", "").lower()
        language = stream.get("Language", "unknown").lower()

        if stream_type == "audio":
            if language in ENGLISH_CODES:
                result["has_english"] = True
            if language in FRENCH_CODES:
                result["has_french"] = True

        elif stream_type == "subtitle":
            if language in FRENCH_CODES:
                result["has_french_subs"] = True

    # Determine what's missing
    if not result["has_english"]:
        result["missing_languages"].append("missing_en_audio")
    if not result["has_french"]:
        result["missing_languages"].append("missing_fr_audio")

    return result


def has_language_issues(
    item: CachedMediaItem,
    is_french_only: bool = False,
) -> bool:
    """Check if an item has language issues (missing EN or FR audio).

    Args:
        item: The media item to check
        is_french_only: If True, missing English audio is not considered an issue

    Returns True if the item is missing required audio.
    """
    lang_check = check_audio_languages(item)

    if is_french_only:
        # French-only items only need French audio
        return not lang_check["has_french"]
    else:
        # Regular items need both English and French audio
        return not lang_check["has_english"] or not lang_check["has_french"]


def get_language_issues_list(
    item: CachedMediaItem,
    is_french_only: bool = False,
) -> list[str]:
    """Get list of specific language issues for an item.

    Args:
        item: The media item to check
        is_french_only: If True, missing English audio is not reported

    Returns list like ["missing_en_audio", "missing_fr_audio"]
    """
    lang_check = check_audio_languages(item)
    issues = []

    if not is_french_only and not lang_check["has_english"]:
        issues.append("missing_en_audio")
    if not lang_check["has_french"]:
        issues.append("missing_fr_audio")

    return issues


# ============================================================================
# Unavailable Requests Analysis
# ============================================================================


def _parse_release_date(date_str: str | None) -> datetime | None:
    """Parse release date string to datetime object.

    Handles both ISO format with time and simple date format.
    """
    if not date_str:
        return None

    try:
        # Try ISO format with time
        if "T" in date_str:
            if date_str.endswith("Z"):
                date_str = date_str[:-1] + "+00:00"
            return datetime.fromisoformat(date_str)
        else:
            # Simple date format (YYYY-MM-DD)
            return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=UTC)
    except (ValueError, TypeError):
        return None


def _get_request_release_date(request: CachedJellyseerrRequest) -> str | None:
    """Get release date from a Jellyseerr request."""
    raw_data = request.raw_data or {}
    media: dict[str, Any] = raw_data.get("media", {})

    # For movies, use releaseDate
    if request.media_type == "movie":
        release_date: str | None = media.get("releaseDate")
        return release_date
    # For TV, use firstAirDate
    elif request.media_type == "tv":
        first_air_date: str | None = media.get("firstAirDate")
        return first_air_date

    return None


def _should_include_request(
    request: CachedJellyseerrRequest,
    show_unreleased: bool = False,
) -> bool:
    """Check if a request should be included in unavailable list.

    Filters out:
    - Future releases (not yet released) - unless show_unreleased=True
    - Recent releases (released less than 3 months ago)

    Args:
        request: The Jellyseerr request to check
        show_unreleased: If True, include future releases (user preference)
    """
    release_date_str = _get_request_release_date(request)
    if not release_date_str:
        # No release date - include by default (safer approach)
        return True

    release_date = _parse_release_date(release_date_str)
    if not release_date:
        return True

    now = datetime.now(UTC)
    today = now.date()
    release_date_only = release_date.date()

    # Filter future releases (unless user wants to see them)
    if FILTER_FUTURE_RELEASES and not show_unreleased and release_date_only > today:
        return False

    # Filter recent releases
    if FILTER_RECENT_RELEASES:
        cutoff_date = today - timedelta(days=RECENT_RELEASE_MONTHS_CUTOFF * 30)
        if release_date_only > cutoff_date:
            return False

    return True


def _get_missing_seasons(request: CachedJellyseerrRequest) -> list[int]:
    """Get list of missing season numbers for a TV request.

    Missing means status is not 5 (Available).
    Reads from media.seasons[] which contains actual availability status.
    """
    if request.media_type != "tv":
        return []

    raw_data = request.raw_data or {}
    media = raw_data.get("media", {})
    seasons = media.get("seasons", [])

    missing = []
    for season in seasons:
        season_num = season.get("seasonNumber")
        season_status = season.get("status", 0)

        # Season is missing if not Available (status 5)
        # Skip specials (season 0)
        if season_num and season_num > 0 and season_status != 5:
            missing.append(season_num)

    return sorted(missing)


def _is_tv_complete_for_released(request: CachedJellyseerrRequest) -> bool:
    """Check if TV show has all released seasons available (status 5).

    For TV shows with status 4 (Partially Available), the request.status may
    not accurately reflect availability. This happens when Jellyseerr marks
    the overall show as partial but all individual seasons are actually available.

    Returns True if:
    - media.status is 5 (fully available), OR
    - media.status is 4 AND all seasons have status 5
    """
    if request.media_type != "tv":
        return False

    raw_data = request.raw_data or {}
    media = raw_data.get("media", {})
    media_status = media.get("status", 0)

    # Media fully available at top level
    if media_status == 5:
        return True

    # Check season-level for partial status
    if media_status == 4:
        seasons = media.get("seasons", [])
        if not seasons:
            return False
        for season in seasons:
            season_num = season.get("seasonNumber", 0)
            # Skip specials (season 0)
            if season_num > 0 and season.get("status", 0) != 5:
                return False
        return True

    return False


def is_unavailable_request(
    request: CachedJellyseerrRequest,
    show_unreleased: bool = False,
) -> bool:
    """Check if a request is unavailable.

    A request is unavailable if:
    - Status is 0 (Unknown), 1 (Pending), 2 (Approved), or 4 (Partially Available)
    - NOT status 3 (Processing) or 5 (Available)
    - For TV shows with status 4: also checks if all seasons are available
    - Release date is not in the future (unless show_unreleased=True)
    - Release date is not too recent (< 3 months)

    Args:
        request: The Jellyseerr request to check
        show_unreleased: If True, include future releases (user preference)
    """
    if request.status not in UNAVAILABLE_STATUS_CODES:
        return False

    # For TV shows with status 4 (Partially Available), check if actually complete
    # This handles cases where Jellyseerr marks show as partial but all seasons are available
    if request.media_type == "tv" and request.status == 4:
        if _is_tv_complete_for_released(request):
            return False

    return _should_include_request(request, show_unreleased)


# ============================================================================
# Issue Detection
# ============================================================================


def get_item_issues(
    item: CachedMediaItem,
    whitelisted_ids: set[str],
    french_only_ids: set[str] | None = None,
    language_exempt_ids: set[str] | None = None,
    large_whitelist_ids: set[str] | None = None,
    thresholds: UserThresholds | None = None,
) -> tuple[list[str], list[str]]:
    """Get all issue types that apply to a content item.

    Args:
        item: The media item to check
        whitelisted_ids: Set of jellyfin_ids in content whitelist
        french_only_ids: Set of jellyfin_ids in french-only whitelist
        language_exempt_ids: Set of jellyfin_ids exempt from ALL language checks
        large_whitelist_ids: Set of jellyfin_ids exempt from large content checks
        thresholds: User's custom thresholds (uses defaults if None)

    Returns tuple of:
    - list of issue types: "old", "large", "language", "request"
    - list of specific language issues: "missing_en_audio", "missing_fr_audio", etc.
    """
    issues: list[str] = []
    language_issues_detail: list[str] = []

    # Use defaults if thresholds not provided
    old_months = thresholds.old_content_months if thresholds else OLD_CONTENT_MONTHS_CUTOFF
    min_age = thresholds.min_age_months if thresholds else MIN_AGE_MONTHS
    large_movie_size = (
        thresholds.large_movie_size_gb if thresholds else LARGE_MOVIE_SIZE_THRESHOLD_GB
    )
    large_season_size = (
        thresholds.large_season_size_gb if thresholds else LARGE_SEASON_SIZE_THRESHOLD_GB
    )

    # Check for old/unwatched (exclude whitelisted)
    if item.jellyfin_id not in whitelisted_ids and is_old_or_unwatched(
        item, months_cutoff=old_months, min_age_months=min_age
    ):
        issues.append("old")

    # Check for large content (movie or series) - skip if large-whitelisted
    is_large_exempt = large_whitelist_ids is not None and item.jellyfin_id in large_whitelist_ids
    if not is_large_exempt:
        if is_large_movie(item, threshold_gb=large_movie_size):
            issues.append("large")
        elif is_large_series(item, threshold_gb=large_season_size):
            issues.append("large")

    # Check for language issues (skip if language-exempt, respect french-only whitelist)
    is_language_exempt = language_exempt_ids is not None and item.jellyfin_id in language_exempt_ids
    if not is_language_exempt:
        is_french_only = french_only_ids is not None and item.jellyfin_id in french_only_ids
        if has_language_issues(item, is_french_only=is_french_only):
            issues.append("language")
            language_issues_detail = get_language_issues_list(item, is_french_only=is_french_only)

    return issues, language_issues_detail


def get_problematic_episodes(
    item: CachedMediaItem, issues: list[str]
) -> list[ProblematicEpisode] | None:
    """Get list of problematic episodes for a series with language issues.

    Args:
        item: The media item to check
        issues: List of issue types for this item

    Returns:
        List of ProblematicEpisode objects if series has language issues, None otherwise.
    """
    # Only for Series items with language issues
    if item.media_type != "Series" or "language" not in issues:
        return None

    # Check if we have cached problematic episodes data
    if not item.problematic_episodes:
        return None

    # Convert cached data to ProblematicEpisode models
    episodes = []
    for ep_data in item.problematic_episodes:
        episodes.append(
            ProblematicEpisode(
                identifier=ep_data.get("identifier", ""),
                name=ep_data.get("name", ""),
                season=ep_data.get("season", 0),
                episode=ep_data.get("episode", 0),
                missing_languages=ep_data.get("missing_languages", []),
            )
        )

    return episodes if episodes else None
