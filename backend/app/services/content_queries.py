"""Content query functions for fetching and filtering content data."""

from datetime import UTC, datetime, timedelta
from typing import Any, TypedDict

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import (
    CachedJellyseerrRequest,
    CachedMediaItem,
    ContentWhitelist,
    UserNickname,
    UserSettings,
)
from app.models.content import (
    ContentIssueItem,
    ContentIssuesResponse,
    ContentSummaryResponse,
    InfoCategorySummary,
    IssueCategorySummary,
    LibraryItem,
    LibraryResponse,
    OldUnwatchedItem,
    OldUnwatchedResponse,
    RecentlyAvailableItem,
    RecentlyAvailableResponse,
    UnavailableRequestItem,
)
from app.services.content_analysis import (
    _get_missing_seasons,
    _parse_release_date,
    extract_provider_ids,
    format_size,
    get_item_issues,
    get_problematic_episodes,
    get_user_thresholds,
    has_language_issues,
    is_large_movie,
    is_large_series,
    is_old_or_unwatched,
    is_unavailable_request,
    parse_jellyfin_datetime,
)
from app.services.whitelist import (
    get_french_only_ids,
    get_language_exempt_ids,
    get_large_whitelist_ids,
    get_request_whitelist_ids,
)

# Constants for info endpoints
DEFAULT_RECENTLY_AVAILABLE_DAYS = 7  # Content available in past 7 days


# ============================================================================
# User Settings Helpers
# ============================================================================


async def get_user_recently_available_days(db: AsyncSession, user_id: int) -> int:
    """Get user's recently_available_days setting, falling back to default."""
    result = await db.execute(select(UserSettings).where(UserSettings.user_id == user_id))
    settings = result.scalar_one_or_none()

    if settings and settings.recently_available_days is not None:
        return settings.recently_available_days
    return DEFAULT_RECENTLY_AVAILABLE_DAYS


async def get_user_show_unreleased_setting(db: AsyncSession, user_id: int) -> bool:
    """Get user's show_unreleased_requests setting.

    Returns False (default) if not configured.
    """
    result = await db.execute(select(UserSettings).where(UserSettings.user_id == user_id))
    settings = result.scalar_one_or_none()
    return settings.show_unreleased_requests if settings else False


# ============================================================================
# Nickname/Display Name Helpers
# ============================================================================


async def get_nickname_map(db: AsyncSession, user_id: int) -> dict[str, str]:
    """Get a mapping of jellyseerr_username -> display_name for a user.

    Returns a dict where keys are Jellyseerr usernames and values are display names.
    """
    result = await db.execute(select(UserNickname).where(UserNickname.user_id == user_id))
    nicknames = result.scalars().all()

    return {n.jellyseerr_username: n.display_name for n in nicknames}


def resolve_display_name(
    requested_by: str | None,
    nickname_map: dict[str, str],
) -> str | None:
    """Resolve the display name for a requester.

    If the requester has a nickname mapping, return the display name.
    Otherwise, return the original requested_by value.
    If requested_by is None, return None.

    Args:
        requested_by: The Jellyseerr username
        nickname_map: Dict mapping usernames to display names

    Returns:
        The resolved display name, or None if requested_by is None
    """
    if requested_by is None:
        return None
    return nickname_map.get(requested_by, requested_by)


# ============================================================================
# Old/Unwatched Content Queries
# ============================================================================


async def get_old_unwatched_content(
    db: AsyncSession,
    user_id: int,
) -> OldUnwatchedResponse:
    """Get all old/unwatched content for a user, excluding whitelisted items.

    Returns items sorted by size (largest first).
    """
    # Get user's thresholds
    thresholds = await get_user_thresholds(db, user_id)

    # Get user's cached media items
    result = await db.execute(select(CachedMediaItem).where(CachedMediaItem.user_id == user_id))
    all_items = result.scalars().all()

    # Get user's whitelist (only non-expired entries)
    now = datetime.now(UTC)
    whitelist_result = await db.execute(
        select(ContentWhitelist.jellyfin_id).where(
            ContentWhitelist.user_id == user_id,
            or_(
                ContentWhitelist.expires_at.is_(None),
                ContentWhitelist.expires_at > now,
            ),
        )
    )
    whitelisted_ids = set(whitelist_result.scalars().all())

    # Filter items
    filtered_items: list[CachedMediaItem] = []
    for item in all_items:
        # Skip whitelisted content
        if item.jellyfin_id in whitelisted_ids:
            continue

        # Check if old/unwatched using user's thresholds
        if is_old_or_unwatched(
            item,
            months_cutoff=thresholds.old_content_months,
            min_age_months=thresholds.min_age_months,
        ):
            filtered_items.append(item)

    # Sort by size descending (largest first)
    filtered_items.sort(key=lambda x: x.size_bytes or 0, reverse=True)

    # Calculate totals
    total_size_bytes = sum(item.size_bytes or 0 for item in filtered_items)

    # Convert to response models
    response_items = [
        OldUnwatchedItem(
            jellyfin_id=item.jellyfin_id,
            name=item.name,
            media_type=item.media_type,
            production_year=item.production_year,
            size_bytes=item.size_bytes,
            size_formatted=format_size(item.size_bytes),
            last_played_date=item.last_played_date,
            path=item.path,
        )
        for item in filtered_items
    ]

    return OldUnwatchedResponse(
        items=response_items,
        total_count=len(response_items),
        total_size_bytes=total_size_bytes,
        total_size_formatted=format_size(total_size_bytes),
    )


# ============================================================================
# Content Summary Query
# ============================================================================


async def get_content_summary(
    db: AsyncSession,
    user_id: int,
) -> ContentSummaryResponse:
    """Get summary counts for all issue types for a user.

    Returns counts for:
    - old_content: Old/unwatched content (excludes whitelisted)
    - large_movies: Movies larger than threshold
    - language_issues: Content with language issues
    - unavailable_requests: Unavailable Jellyseerr requests

    Uses asyncio.gather() to parallelize independent whitelist queries (US-59.1).
    """
    import asyncio

    # Get user's thresholds
    thresholds = await get_user_thresholds(db, user_id)

    # Get user's cached media items
    result = await db.execute(select(CachedMediaItem).where(CachedMediaItem.user_id == user_id))
    all_items = result.scalars().all()

    # Get user's whitelist (only non-expired entries)
    now = datetime.now(UTC)
    whitelist_result = await db.execute(
        select(ContentWhitelist.jellyfin_id).where(
            ContentWhitelist.user_id == user_id,
            or_(
                ContentWhitelist.expires_at.is_(None),
                ContentWhitelist.expires_at > now,
            ),
        )
    )
    whitelisted_ids = set(whitelist_result.scalars().all())

    # Parallelize independent whitelist queries (US-59.1)
    (
        large_whitelist_ids,
        french_only_ids,
        language_exempt_ids,
        unavailable_requests_count,
        recently_available_count,
    ) = await asyncio.gather(
        get_large_whitelist_ids(db, user_id),
        get_french_only_ids(db, user_id),
        get_language_exempt_ids(db, user_id),
        get_unavailable_requests_count(db, user_id),
        get_recently_available_count(db, user_id),
    )

    # Calculate old content (excluding whitelisted)
    old_content_items: list[CachedMediaItem] = []
    for item in all_items:
        if item.jellyfin_id in whitelisted_ids:
            continue
        if is_old_or_unwatched(
            item,
            months_cutoff=thresholds.old_content_months,
            min_age_months=thresholds.min_age_months,
        ):
            old_content_items.append(item)

    old_content_size = sum(item.size_bytes or 0 for item in old_content_items)

    # Calculate large content (movies + series), excluding whitelisted
    large_content_items: list[CachedMediaItem] = []
    for item in all_items:
        if item.jellyfin_id in large_whitelist_ids:
            continue
        if is_large_movie(item, threshold_gb=thresholds.large_movie_size_gb):
            large_content_items.append(item)
        elif is_large_series(item, threshold_gb=thresholds.large_season_size_gb):
            large_content_items.append(item)

    large_content_size = sum(item.size_bytes or 0 for item in large_content_items)

    # Calculate language issues (respecting french-only and language-exempt whitelists)
    language_issues_items: list[CachedMediaItem] = []
    for item in all_items:
        # Skip items exempt from all language checks
        if item.jellyfin_id in language_exempt_ids:
            continue
        is_french_only = item.jellyfin_id in french_only_ids
        if has_language_issues(item, is_french_only=is_french_only):
            language_issues_items.append(item)

    language_issues_size = sum(item.size_bytes or 0 for item in language_issues_items)

    return ContentSummaryResponse(
        old_content=IssueCategorySummary(
            count=len(old_content_items),
            total_size_bytes=old_content_size,
            total_size_formatted=format_size(old_content_size) if old_content_size > 0 else "0 B",
        ),
        large_movies=IssueCategorySummary(
            count=len(large_content_items),
            total_size_bytes=large_content_size,
            total_size_formatted=format_size(large_content_size)
            if large_content_size > 0
            else "0 B",
        ),
        language_issues=IssueCategorySummary(
            count=len(language_issues_items),
            total_size_bytes=language_issues_size,
            total_size_formatted=format_size(language_issues_size)
            if language_issues_size > 0
            else "0 B",
        ),
        unavailable_requests=IssueCategorySummary(
            count=unavailable_requests_count,
            total_size_bytes=0,
            total_size_formatted="0 B",
        ),
        # Info categories
        recently_available=InfoCategorySummary(
            count=recently_available_count,
        ),
    )


# ============================================================================
# Content Issues Query
# ============================================================================


async def get_content_issues(
    db: AsyncSession,
    user_id: int,
    filter_type: str | None = None,
) -> ContentIssuesResponse:
    """Get all content with issues for a user.

    Args:
        db: Database session
        user_id: User ID from JWT
        filter_type: Optional filter - "old", "large", "language", "requests"

    Returns items sorted by size (largest first).
    """
    # Get user's thresholds
    thresholds = await get_user_thresholds(db, user_id)

    # Build Sonarr TMDB -> titleSlug map for enriching series items
    from app.services.sonarr import get_decrypted_sonarr_api_key, get_sonarr_tmdb_to_slug_map

    sonarr_slug_map: dict[int, str] = {}
    settings_result = await db.execute(select(UserSettings).where(UserSettings.user_id == user_id))
    user_settings = settings_result.scalar_one_or_none()
    if user_settings and user_settings.sonarr_server_url and user_settings.sonarr_api_key_encrypted:
        sonarr_api_key = get_decrypted_sonarr_api_key(user_settings)
        if sonarr_api_key:
            sonarr_slug_map = await get_sonarr_tmdb_to_slug_map(
                user_settings.sonarr_server_url, sonarr_api_key
            )

    # Get user's cached media items
    result = await db.execute(select(CachedMediaItem).where(CachedMediaItem.user_id == user_id))
    all_items = result.scalars().all()

    # Get user's whitelist (only non-expired entries)
    now = datetime.now(UTC)
    whitelist_result = await db.execute(
        select(ContentWhitelist.jellyfin_id).where(
            ContentWhitelist.user_id == user_id,
            or_(
                ContentWhitelist.expires_at.is_(None),
                ContentWhitelist.expires_at > now,
            ),
        )
    )
    whitelisted_ids = set(whitelist_result.scalars().all())

    # Get user's french-only whitelist
    french_only_ids = await get_french_only_ids(db, user_id)

    # Get user's language-exempt whitelist
    language_exempt_ids = await get_language_exempt_ids(db, user_id)

    # Get user's large content whitelist
    large_whitelist_ids = await get_large_whitelist_ids(db, user_id)

    # Build list of items with issues
    # Store tuple of (item, issues_list, language_issues_detail)
    items_with_issues: list[tuple[CachedMediaItem, list[str], list[str]]] = []

    for item in all_items:
        issues, language_issues_detail = get_item_issues(
            item,
            whitelisted_ids,
            french_only_ids,
            language_exempt_ids,
            large_whitelist_ids,
            thresholds,
        )

        # Skip items with no issues
        if not issues:
            continue

        # Apply filter if specified
        if filter_type == "old" and "old" not in issues:
            continue
        if filter_type == "large" and "large" not in issues:
            continue
        if filter_type == "language" and "language" not in issues:
            continue

        items_with_issues.append((item, issues, language_issues_detail))

    # Sort by size descending (largest first)
    items_with_issues.sort(key=lambda x: x[0].size_bytes or 0, reverse=True)

    # Calculate totals
    total_size_bytes = sum(item.size_bytes or 0 for item, _, _ in items_with_issues)

    # Build reconciliation map: (tmdb_id, media_type) -> jellyseerr_request_id
    # This allows us to link Jellyfin items with their Jellyseerr requests
    jellyseerr_map: dict[tuple[int, str], int] = {}
    requests_result = await db.execute(
        select(
            CachedJellyseerrRequest.tmdb_id,
            CachedJellyseerrRequest.media_type,
            CachedJellyseerrRequest.jellyseerr_id,
        )
        .where(CachedJellyseerrRequest.user_id == user_id)
        .where(CachedJellyseerrRequest.tmdb_id.isnot(None))
    )
    for row in requests_result:
        # Normalize media_type: Jellyfin uses "Movie"/"Series", Jellyseerr uses "movie"/"tv"
        jellyseerr_media_type = row.media_type  # "movie" or "tv"
        jellyseerr_map[(row.tmdb_id, jellyseerr_media_type)] = row.jellyseerr_id

    # Convert to response models
    response_items = []
    for item, issues, language_issues_detail in items_with_issues:
        tmdb_id, imdb_id = extract_provider_ids(item)

        # Look up matching Jellyseerr request and Sonarr titleSlug
        jellyseerr_request_id = None
        sonarr_title_slug = None
        if tmdb_id:
            try:
                tmdb_id_int = int(tmdb_id)
                # Normalize media type for lookup: "Movie" -> "movie", "Series" -> "tv"
                normalized_media_type = "movie" if item.media_type == "Movie" else "tv"
                jellyseerr_request_id = jellyseerr_map.get((tmdb_id_int, normalized_media_type))
                # Look up Sonarr titleSlug for series items (for external links)
                if item.media_type == "Series":
                    sonarr_title_slug = sonarr_slug_map.get(tmdb_id_int)
            except (ValueError, TypeError):
                pass

        # Calculate largest_season_size fields for series
        largest_season_size_bytes = (
            item.largest_season_size_bytes if item.media_type == "Series" else None
        )
        largest_season_size_formatted = (
            format_size(largest_season_size_bytes) if largest_season_size_bytes else None
        )

        response_items.append(
            ContentIssueItem(
                jellyfin_id=item.jellyfin_id,
                name=item.name,
                media_type=item.media_type,
                production_year=item.production_year,
                size_bytes=item.size_bytes,
                size_formatted=format_size(item.size_bytes),
                last_played_date=item.last_played_date,
                played=item.played,
                path=item.path,
                date_created=item.date_created,
                issues=issues,
                language_issues=language_issues_detail if language_issues_detail else None,
                tmdb_id=tmdb_id,
                imdb_id=imdb_id,
                sonarr_title_slug=sonarr_title_slug,
                jellyseerr_request_id=jellyseerr_request_id,
                largest_season_size_bytes=largest_season_size_bytes,
                largest_season_size_formatted=largest_season_size_formatted,
                # US-52.2: Include problematic episodes for series with language issues
                problematic_episodes=get_problematic_episodes(item, issues),
            )
        )

    return ContentIssuesResponse(
        items=response_items,
        total_count=len(response_items),
        total_size_bytes=total_size_bytes,
        total_size_formatted=format_size(total_size_bytes),
    )


# ============================================================================
# Recently Available Queries
# ============================================================================


class SeasonEpisodeDetails(TypedDict, total=False):
    """Type for season/episode details returned by _get_season_episode_details."""

    season_info: str | None
    episode_count: int | None
    available_episodes: int | None
    total_episodes: int | None


def _get_availability_date(request: CachedJellyseerrRequest) -> datetime | None:
    """Extract availability date from a Jellyseerr request.

    Looks for mediaAddedAt in raw_data, falls back to modifiedAt or createdAt.
    Returns a timezone-aware datetime (UTC).
    """
    raw_data = request.raw_data or {}
    media = raw_data.get("media", {})

    # Try mediaAddedAt first (most accurate for when content became available)
    date_str = media.get("mediaAddedAt")
    if not date_str:
        # Fallback to modifiedAt
        date_str = raw_data.get("modifiedAt")
    if not date_str:
        # Final fallback to created_at_source
        date_str = request.created_at_source

    if not date_str:
        return None

    dt = parse_jellyfin_datetime(date_str)
    if dt and dt.tzinfo is None:
        # Make timezone-aware if not already
        dt = dt.replace(tzinfo=UTC)
    return dt


def _get_season_episode_details(
    request: CachedJellyseerrRequest,
) -> SeasonEpisodeDetails:
    """Extract season and episode details from cached Jellyseerr request data.

    For status 5 (Fully Available) TV shows:
        - season_info: "Season 1" or "Seasons 1-3" or "Seasons 1, 3, 4" (non-contiguous)
        - episode_count: Total episodes across all seasons
        - available_episodes/total_episodes: None

    For status 4 (Partially Available) TV shows:
        - season_info: "Season X in progress" (highest partial season)
        - episode_count: None
        - available_episodes: Episodes with data in highest partial season
        - total_episodes: episodeCount of highest partial season

    For movies:
        - All fields are None

    Args:
        request: CachedJellyseerrRequest with raw_data containing season info

    Returns:
        Dict with season_info, episode_count, available_episodes, total_episodes
    """
    # Movies return all None
    if request.media_type == "movie":
        return {
            "season_info": None,
            "episode_count": None,
            "available_episodes": None,
            "total_episodes": None,
        }

    raw_data = request.raw_data or {}
    # Seasons are at root level in Jellyseerr request data, not inside media
    seasons = raw_data.get("seasons", [])

    if not seasons:
        return {
            "season_info": None,
            "episode_count": None,
            "available_episodes": None,
            "total_episodes": None,
        }

    # Filter out season 0 (specials) for season_info display
    regular_seasons = [s for s in seasons if s.get("seasonNumber", 0) > 0]

    if not regular_seasons:
        # Only specials exist - count episodes but no season_info
        total_eps = sum(s.get("episodeCount", 0) for s in seasons)
        return {
            "season_info": None,
            "episode_count": total_eps if total_eps > 0 else None,
            "available_episodes": None,
            "total_episodes": None,
        }

    # Sort seasons by season number
    sorted_seasons = sorted(regular_seasons, key=lambda s: s.get("seasonNumber", 0))
    season_numbers = [s.get("seasonNumber", 0) for s in sorted_seasons]

    # Calculate total episode count (including specials)
    total_episode_count = sum(s.get("episodeCount", 0) for s in seasons)

    # Status 5: Fully Available
    if request.status == 5:
        season_info = _format_season_info(season_numbers)
        return {
            "season_info": season_info,
            "episode_count": total_episode_count if total_episode_count > 0 else None,
            "available_episodes": None,
            "total_episodes": None,
        }

    # Status 4: Partially Available
    if request.status == 4:
        # Find the highest partial season (status 4)
        partial_seasons = [s for s in sorted_seasons if s.get("status") == 4]

        if partial_seasons:
            # Get the highest season number that is partial
            highest_partial = max(partial_seasons, key=lambda s: s.get("seasonNumber", 0))
            season_num = highest_partial.get("seasonNumber", 0)
            total_eps = highest_partial.get("episodeCount", 0)

            # Count available episodes from episode data
            episodes = highest_partial.get("episodes", [])
            available_eps = len(episodes) if episodes else None

            return {
                "season_info": f"Season {season_num} in progress",
                "episode_count": None,
                "available_episodes": available_eps,
                "total_episodes": total_eps if total_eps > 0 else None,
            }

        # No partial seasons found but status is 4 - use all season info
        season_info = _format_season_info(season_numbers)
        return {
            "season_info": season_info,
            "episode_count": total_episode_count if total_episode_count > 0 else None,
            "available_episodes": None,
            "total_episodes": None,
        }

    # Other statuses - return None for all
    return {
        "season_info": None,
        "episode_count": None,
        "available_episodes": None,
        "total_episodes": None,
    }


def _format_season_info(season_numbers: list[int]) -> str:
    """Format season numbers into a human-readable string.

    Examples:
        [1] -> "Season 1"
        [1, 2, 3] -> "Seasons 1-3"
        [1, 3, 4] -> "Seasons 1, 3, 4"
        [1, 2, 4, 5, 6] -> "Seasons 1, 2, 4-6" (contiguous groups)

    Args:
        season_numbers: Sorted list of season numbers (must not be empty)

    Returns:
        Formatted season info string
    """
    if not season_numbers:
        return ""

    if len(season_numbers) == 1:
        return f"Season {season_numbers[0]}"

    # Check if all seasons are contiguous
    is_contiguous = all(
        season_numbers[i + 1] == season_numbers[i] + 1 for i in range(len(season_numbers) - 1)
    )

    if is_contiguous:
        return f"Seasons {season_numbers[0]}-{season_numbers[-1]}"

    # Non-contiguous: list all numbers
    return f"Seasons {', '.join(str(n) for n in season_numbers)}"


def _get_recent_episodes_from_cached_data(
    request: CachedJellyseerrRequest,
    days_back: int,
) -> dict[int, list[int]] | None:
    """Check for recent episodes in cached Jellyseerr request data.

    For status 4 (Partially Available) TV shows, checks for episodes with airDate
    within the days_back window. Looks in both raw_data.media.seasons[] and
    raw_data.seasons[] to support different data structures.

    Args:
        request: CachedJellyseerrRequest with raw_data containing episode info
        days_back: Number of days to look back for recent episodes

    Returns:
        Dict mapping season_number -> list of episode_numbers for recent episodes,
        or None if no recent episodes found.
        Example: {2: [5, 6, 7]} means season 2, episodes 5, 6, 7 are recent.
    """
    raw_data = request.raw_data or {}
    media = raw_data.get("media", {})
    # Try media.seasons first (for episode air dates), fall back to root seasons
    seasons = media.get("seasons", []) or raw_data.get("seasons", [])

    if not seasons:
        return None

    now = datetime.now(UTC)
    cutoff_date = now - timedelta(days=days_back)

    recent_episodes: dict[int, list[int]] = {}

    for season in seasons:
        season_number = season.get("seasonNumber")
        if not season_number:
            continue

        episodes = season.get("episodes", [])
        if not episodes:
            continue

        recent_in_season: list[int] = []

        for episode in episodes:
            air_date_str = episode.get("airDate")
            if not air_date_str:
                continue

            # Parse airDate (format: "YYYY-MM-DD")
            try:
                air_date = datetime.strptime(air_date_str, "%Y-%m-%d").replace(tzinfo=UTC)
            except (ValueError, TypeError):
                continue

            if air_date >= cutoff_date:
                episode_number = episode.get("episodeNumber")
                if episode_number:
                    recent_in_season.append(episode_number)

        if recent_in_season:
            recent_episodes[season_number] = recent_in_season

    return recent_episodes if recent_episodes else None


async def get_recently_available_count(
    db: AsyncSession,
    user_id: int,
    days_back: int | None = None,
) -> int:
    """Get count of recently available content for summary.

    Args:
        db: Database session
        user_id: User ID
        days_back: Number of days to look back. If None, uses user's setting.

    For status 4 (Partially Available) TV shows, also checks for recent episodes
    using cached episode air dates.
    """
    if days_back is None:
        days_back = await get_user_recently_available_days(db, user_id)

    result = await db.execute(
        select(CachedJellyseerrRequest).where(CachedJellyseerrRequest.user_id == user_id)
    )
    all_requests = result.scalars().all()

    now = datetime.now(UTC)
    cutoff_date = now - timedelta(days=days_back)

    count = 0
    for request in all_requests:
        # Only count available (4 or 5 status)
        if request.status not in [4, 5]:
            continue

        # For status 4 TV shows, check for recent episodes first
        if request.status == 4 and request.media_type == "tv":
            recent_episodes = _get_recent_episodes_from_cached_data(request, days_back)
            if recent_episodes:
                count += 1
                continue
            # Status 4 TV without recent episodes: check regular availability date
            availability_date = _get_availability_date(request)
            if availability_date and availability_date >= cutoff_date:
                count += 1
            continue

        # For status 5 or movies: use regular availability date logic
        availability_date = _get_availability_date(request)
        if not availability_date:
            continue

        if availability_date >= cutoff_date:
            count += 1

    return count


async def get_recently_available(
    db: AsyncSession,
    user_id: int,
    days_back: int | None = None,
) -> RecentlyAvailableResponse:
    """Get content that became available in the specified number of days.

    Args:
        db: Database session
        user_id: User ID
        days_back: Number of days to look back. If None, uses user's setting.

    Returns items sorted by date, newest first.
    Includes display_name field resolved from user's nickname mappings.

    For status 4 (Partially Available) TV shows, also checks for recent episodes
    using cached episode air dates. If recent episodes are found, the show is
    included with today's date as the availability_date.
    """
    if days_back is None:
        days_back = await get_user_recently_available_days(db, user_id)

    result = await db.execute(
        select(CachedJellyseerrRequest).where(CachedJellyseerrRequest.user_id == user_id)
    )
    all_requests = result.scalars().all()

    # Get nickname mappings for resolving display names
    nickname_map = await get_nickname_map(db, user_id)

    now = datetime.now(UTC)
    cutoff_date = now - timedelta(days=days_back)

    recent_items: list[tuple[datetime, CachedJellyseerrRequest]] = []

    for request in all_requests:
        # Only count available (4 or 5 status)
        if request.status not in [4, 5]:
            continue

        # For status 4 TV shows, check for recent episodes first
        if request.status == 4 and request.media_type == "tv":
            recent_episodes = _get_recent_episodes_from_cached_data(request, days_back)
            if recent_episodes:
                # Use today's date as availability_date to force inclusion
                recent_items.append((now, request))
                continue
            # Status 4 TV without recent episodes: check regular availability date
            availability_date = _get_availability_date(request)
            if availability_date and availability_date >= cutoff_date:
                recent_items.append((availability_date, request))
            continue

        # For status 5 or movies: use regular availability date logic
        availability_date = _get_availability_date(request)
        if not availability_date:
            continue

        if availability_date >= cutoff_date:
            recent_items.append((availability_date, request))

    # Sort by date descending (newest first)
    recent_items.sort(key=lambda x: x[0], reverse=True)

    # Convert to response models
    response_items: list[RecentlyAvailableItem] = []
    for availability_date, request in recent_items:
        # Get season/episode details for TV shows
        season_details = _get_season_episode_details(request)

        response_items.append(
            RecentlyAvailableItem(
                jellyseerr_id=request.jellyseerr_id,
                title=request.title or "Unknown",
                title_fr=request.title_fr,
                media_type=request.media_type,
                availability_date=availability_date.isoformat(),
                requested_by=request.requested_by,
                display_name=resolve_display_name(request.requested_by, nickname_map),
                season_info=season_details.get("season_info"),
                episode_count=season_details.get("episode_count"),
                available_episodes=season_details.get("available_episodes"),
                total_episodes=season_details.get("total_episodes"),
            )
        )

    return RecentlyAvailableResponse(
        items=response_items,
        total_count=len(response_items),
    )


# ============================================================================
# Unavailable Requests Queries
# ============================================================================


async def get_unavailable_requests_count(
    db: AsyncSession,
    user_id: int,
) -> int:
    """Get count of unavailable requests for summary.

    Excludes whitelisted requests (non-expired only).
    Respects user's show_unreleased_requests setting.
    """
    # Get user's display preference
    show_unreleased = await get_user_show_unreleased_setting(db, user_id)

    result = await db.execute(
        select(CachedJellyseerrRequest).where(CachedJellyseerrRequest.user_id == user_id)
    )
    all_requests = result.scalars().all()

    # Get whitelisted request IDs (non-expired only)
    whitelisted_ids = await get_request_whitelist_ids(db, user_id)

    count = 0
    for request in all_requests:
        # Skip whitelisted requests
        if request.jellyseerr_id in whitelisted_ids:
            continue
        if is_unavailable_request(request, show_unreleased):
            count += 1

    return count


async def get_unavailable_requests(
    db: AsyncSession,
    user_id: int,
) -> list[UnavailableRequestItem]:
    """Get all unavailable requests for a user.

    Returns items sorted by request date (newest first).
    Excludes whitelisted requests (non-expired only).
    Respects user's show_unreleased_requests setting.
    """
    # Get user's display preference
    show_unreleased = await get_user_show_unreleased_setting(db, user_id)

    result = await db.execute(
        select(CachedJellyseerrRequest).where(CachedJellyseerrRequest.user_id == user_id)
    )
    all_requests = result.scalars().all()

    # Get whitelisted request IDs (non-expired only)
    whitelisted_ids = await get_request_whitelist_ids(db, user_id)

    unavailable_items: list[tuple[datetime | None, UnavailableRequestItem]] = []

    for request in all_requests:
        # Skip whitelisted requests
        if request.jellyseerr_id in whitelisted_ids:
            continue
        if not is_unavailable_request(request, show_unreleased):
            continue

        # Get request date for sorting
        request_date_str = request.created_at_source
        raw_data = request.raw_data or {}
        if not request_date_str:
            request_date_str = raw_data.get("createdAt")

        request_date = _parse_release_date(request_date_str)

        # Get missing seasons for TV shows
        missing_seasons = _get_missing_seasons(request) if request.media_type == "tv" else None

        # Get title - try stored title first, then raw_data media object
        title = request.title
        if not title or title == "Unknown":
            media = raw_data.get("media", {})
            title = (
                media.get("title")
                or media.get("name")
                or media.get("originalTitle")
                or media.get("originalName")
            )
            if not title:
                tmdb_id = request.tmdb_id or media.get("tmdbId")
                title = f"TMDB-{tmdb_id}" if tmdb_id else "Unknown"

        item = UnavailableRequestItem(
            jellyseerr_id=request.jellyseerr_id,
            title=title,
            media_type=request.media_type,
            requested_by=request.requested_by,
            request_date=request_date_str,
            issues=["request"],
            missing_seasons=missing_seasons if missing_seasons else None,
            tmdb_id=request.tmdb_id,
            release_date=request.release_date,
        )

        unavailable_items.append((request_date, item))

    # Sort by request date descending (newest first)
    unavailable_items.sort(key=lambda x: x[0] or datetime.min.replace(tzinfo=UTC), reverse=True)

    return [item for _, item in unavailable_items]


# ============================================================================
# Library Query
# ============================================================================


async def get_library(
    db: AsyncSession,
    user_id: int,
    media_type: str | None = None,
    search: str | None = None,
    watched: str | None = None,
    sort: str = "name",
    order: str = "asc",
    min_year: int | None = None,
    max_year: int | None = None,
    min_size_gb: float | None = None,
    max_size_gb: float | None = None,
) -> LibraryResponse:
    """Get all cached media items for a user with filtering and sorting.

    Args:
        db: Database session
        user_id: User ID from JWT
        media_type: Filter by type - "movie", "series", or None for all
        search: Search string (case-insensitive name search)
        watched: Filter by watched status - "true", "false", or None for all
        sort: Sort field - "name", "year", "size", "date_added", "last_watched"
        order: Sort order - "asc" or "desc"
        min_year: Minimum production year filter
        max_year: Maximum production year filter
        min_size_gb: Minimum size in GB filter
        max_size_gb: Maximum size in GB filter

    Returns:
        LibraryResponse with items, totals, and service URLs
    """
    # Build Sonarr TMDB -> titleSlug map for enriching series items
    from app.services.sonarr import get_decrypted_sonarr_api_key, get_sonarr_tmdb_to_slug_map

    sonarr_slug_map: dict[int, str] = {}
    settings_result = await db.execute(select(UserSettings).where(UserSettings.user_id == user_id))
    user_settings = settings_result.scalar_one_or_none()
    if user_settings and user_settings.sonarr_server_url and user_settings.sonarr_api_key_encrypted:
        sonarr_api_key = get_decrypted_sonarr_api_key(user_settings)
        if sonarr_api_key:
            sonarr_slug_map = await get_sonarr_tmdb_to_slug_map(
                user_settings.sonarr_server_url, sonarr_api_key
            )

    # Get all cached media items for the user
    result = await db.execute(select(CachedMediaItem).where(CachedMediaItem.user_id == user_id))
    all_items = list(result.scalars().all())

    # Apply filters
    filtered_items: list[CachedMediaItem] = []
    for item in all_items:
        # Filter by media type
        if media_type:
            if media_type.lower() == "movie" and item.media_type != "Movie":
                continue
            if media_type.lower() == "series" and item.media_type != "Series":
                continue

        # Filter by search string (case-insensitive name match)
        if search:
            if search.lower() not in item.name.lower():
                continue

        # Filter by watched status
        if watched is not None:
            if watched.lower() == "true" and not item.played:
                continue
            if watched.lower() == "false" and item.played:
                continue

        # Filter by year range
        if min_year is not None and (
            item.production_year is None or item.production_year < min_year
        ):
            continue
        if max_year is not None and (
            item.production_year is None or item.production_year > max_year
        ):
            continue

        # Filter by size range (convert GB to bytes)
        if min_size_gb is not None:
            min_bytes = int(min_size_gb * 1024 * 1024 * 1024)
            if item.size_bytes is None or item.size_bytes < min_bytes:
                continue
        if max_size_gb is not None:
            max_bytes = int(max_size_gb * 1024 * 1024 * 1024)
            if item.size_bytes is None or item.size_bytes > max_bytes:
                continue

        filtered_items.append(item)

    # Sort items
    reverse = order.lower() == "desc"

    def sort_key(item: CachedMediaItem) -> tuple[int, Any]:
        """Generate sort key with null handling. Returns (is_null, value) tuple."""
        if sort == "name":
            return (0, item.name.lower())
        elif sort == "year":
            return (0 if item.production_year else 1, item.production_year or 0)
        elif sort == "size":
            return (0 if item.size_bytes else 1, item.size_bytes or 0)
        elif sort == "date_added":
            return (0 if item.date_created else 1, item.date_created or "")
        elif sort == "last_watched":
            return (0 if item.last_played_date else 1, item.last_played_date or "")
        else:
            # Default to name
            return (0, item.name.lower())

    filtered_items.sort(key=sort_key, reverse=reverse)

    # Calculate totals
    total_size_bytes = sum(item.size_bytes or 0 for item in filtered_items)

    # Convert to response models
    response_items = []
    for item in filtered_items:
        tmdb_id, _ = extract_provider_ids(item)

        # Look up Sonarr titleSlug for series items (for external links)
        sonarr_title_slug = None
        if tmdb_id and item.media_type == "Series":
            try:
                tmdb_id_int = int(tmdb_id)
                sonarr_title_slug = sonarr_slug_map.get(tmdb_id_int)
            except (ValueError, TypeError):
                pass

        response_items.append(
            LibraryItem(
                jellyfin_id=item.jellyfin_id,
                name=item.name,
                media_type=item.media_type,
                production_year=item.production_year,
                size_bytes=item.size_bytes,
                size_formatted=format_size(item.size_bytes),
                played=item.played,
                last_played_date=item.last_played_date,
                date_created=item.date_created,
                tmdb_id=tmdb_id,
                sonarr_title_slug=sonarr_title_slug,
            )
        )

    return LibraryResponse(
        items=response_items,
        total_count=len(response_items),
        total_size_bytes=total_size_bytes,
        total_size_formatted=format_size(total_size_bytes) if total_size_bytes > 0 else "0 B",
    )
