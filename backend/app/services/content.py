"""Content analysis service for filtering old/unwatched content."""

from datetime import datetime, timedelta, timezone
from typing import Any, TypedDict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class LanguageCheckResult(TypedDict):
    """Type for check_audio_languages return value."""

    has_english: bool
    has_french: bool
    has_french_subs: bool
    missing_languages: list[str]

from app.database import CachedMediaItem, CachedJellyseerrRequest, ContentWhitelist
from app.models.content import (
    ContentIssueItem,
    ContentIssuesResponse,
    ContentSummaryResponse,
    CurrentlyAiringItem,
    CurrentlyAiringResponse,
    InfoCategorySummary,
    IssueCategorySummary,
    OldUnwatchedItem,
    OldUnwatchedResponse,
    RecentlyAvailableItem,
    RecentlyAvailableResponse,
    UnavailableRequestItem,
    WhitelistItem,
    WhitelistListResponse,
)


# Hardcoded thresholds per acceptance criteria
OLD_CONTENT_MONTHS_CUTOFF = 4  # Content not watched in 4+ months
MIN_AGE_MONTHS = 3  # Don't flag content added recently
LARGE_MOVIE_SIZE_THRESHOLD_GB = 13  # Movies larger than 13GB

# Unavailable requests configuration (from original script)
FILTER_FUTURE_RELEASES = True  # Filter out content not yet released
FILTER_RECENT_RELEASES = True  # Filter out content released recently
RECENT_RELEASE_MONTHS_CUTOFF = 3  # Don't flag content released < 3 months ago

# Jellyseerr status codes
# 0 = Unknown, 1 = Pending, 2 = Approved, 3 = Processing, 4 = Partially Available, 5 = Available
UNAVAILABLE_STATUS_CODES = {0, 1, 2, 4}  # Status codes for unavailable requests


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
    now = datetime.now(timezone.utc)
    cutoff_date = now - timedelta(days=months_cutoff * 30)
    min_age_date = now - timedelta(days=min_age_months * 30)

    # Check if item was added recently (for unplayed items check)
    date_created = parse_jellyfin_datetime(item.date_created)
    item_age_ok = True
    if date_created:
        # Make timezone-aware if not already
        if date_created.tzinfo is None:
            date_created = date_created.replace(tzinfo=timezone.utc)
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
            last_played = last_played.replace(tzinfo=timezone.utc)
        if last_played < cutoff_date:
            return True

    return False


async def get_old_unwatched_content(
    db: AsyncSession,
    user_id: int,
) -> OldUnwatchedResponse:
    """Get all old/unwatched content for a user, excluding whitelisted items.

    Returns items sorted by size (largest first).
    """
    # Get user's cached media items
    result = await db.execute(
        select(CachedMediaItem).where(CachedMediaItem.user_id == user_id)
    )
    all_items = result.scalars().all()

    # Get user's whitelist
    whitelist_result = await db.execute(
        select(ContentWhitelist.jellyfin_id).where(ContentWhitelist.user_id == user_id)
    )
    whitelisted_ids = set(whitelist_result.scalars().all())

    # Filter items
    filtered_items: list[CachedMediaItem] = []
    for item in all_items:
        # Skip whitelisted content
        if item.jellyfin_id in whitelisted_ids:
            continue

        # Check if old/unwatched
        if is_old_or_unwatched(item):
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


async def add_to_whitelist(
    db: AsyncSession,
    user_id: int,
    jellyfin_id: str,
    name: str,
    media_type: str,
) -> ContentWhitelist:
    """Add content to user's whitelist.

    Raises ValueError if the content is already in the whitelist.
    """
    # Check if already whitelisted
    result = await db.execute(
        select(ContentWhitelist).where(
            ContentWhitelist.user_id == user_id,
            ContentWhitelist.jellyfin_id == jellyfin_id,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise ValueError(f"Content '{name}' is already in whitelist")

    # Create new whitelist entry
    entry = ContentWhitelist(
        user_id=user_id,
        jellyfin_id=jellyfin_id,
        name=name,
        media_type=media_type,
    )
    db.add(entry)
    await db.flush()  # Get the ID assigned
    return entry


async def get_whitelist(
    db: AsyncSession,
    user_id: int,
) -> WhitelistListResponse:
    """Get all whitelist entries for a user."""
    result = await db.execute(
        select(ContentWhitelist)
        .where(ContentWhitelist.user_id == user_id)
        .order_by(ContentWhitelist.created_at.desc())
    )
    entries = result.scalars().all()

    items = [
        WhitelistItem(
            id=entry.id,
            jellyfin_id=entry.jellyfin_id,
            name=entry.name,
            media_type=entry.media_type,
            created_at=entry.created_at.isoformat() if entry.created_at else "",
        )
        for entry in entries
    ]

    return WhitelistListResponse(
        items=items,
        total_count=len(items),
    )


async def remove_from_whitelist(
    db: AsyncSession,
    user_id: int,
    whitelist_id: int,
) -> bool:
    """Remove an item from the user's whitelist.

    Returns True if item was found and deleted, False otherwise.
    Only deletes items that belong to the specified user.
    """
    result = await db.execute(
        select(ContentWhitelist).where(
            ContentWhitelist.id == whitelist_id,
            ContentWhitelist.user_id == user_id,
        )
    )
    entry = result.scalar_one_or_none()

    if not entry:
        return False

    await db.delete(entry)
    return True


# French-Only Whitelist functions (US-5.2)


async def add_to_french_only_whitelist(
    db: AsyncSession,
    user_id: int,
    jellyfin_id: str,
    name: str,
    media_type: str,
) -> None:
    """Add an item to the user's french-only whitelist.

    Items in this whitelist are exempt from missing English audio checks.
    Raises ValueError if item already exists.
    """
    # Import here to avoid circular imports
    from app.database import FrenchOnlyWhitelist

    # Check if already whitelisted
    result = await db.execute(
        select(FrenchOnlyWhitelist).where(
            FrenchOnlyWhitelist.user_id == user_id,
            FrenchOnlyWhitelist.jellyfin_id == jellyfin_id,
        )
    )
    if result.scalar_one_or_none():
        raise ValueError("Item already in french-only whitelist")

    entry = FrenchOnlyWhitelist(
        user_id=user_id,
        jellyfin_id=jellyfin_id,
        name=name,
        media_type=media_type,
    )
    db.add(entry)


async def get_french_only_whitelist(
    db: AsyncSession,
    user_id: int,
) -> WhitelistListResponse:
    """Get all items in the user's french-only whitelist."""
    from app.database import FrenchOnlyWhitelist

    result = await db.execute(
        select(FrenchOnlyWhitelist)
        .where(FrenchOnlyWhitelist.user_id == user_id)
        .order_by(FrenchOnlyWhitelist.name)
    )
    entries = result.scalars().all()

    items = [
        WhitelistItem(
            id=entry.id,
            jellyfin_id=entry.jellyfin_id,
            name=entry.name,
            media_type=entry.media_type,
            created_at=entry.created_at.isoformat() if entry.created_at else "",
        )
        for entry in entries
    ]

    return WhitelistListResponse(
        items=items,
        total_count=len(items),
    )


async def remove_from_french_only_whitelist(
    db: AsyncSession,
    user_id: int,
    whitelist_id: int,
) -> bool:
    """Remove an item from the user's french-only whitelist.

    Returns True if item was found and deleted, False otherwise.
    """
    from app.database import FrenchOnlyWhitelist

    result = await db.execute(
        select(FrenchOnlyWhitelist).where(
            FrenchOnlyWhitelist.id == whitelist_id,
            FrenchOnlyWhitelist.user_id == user_id,
        )
    )
    entry = result.scalar_one_or_none()

    if not entry:
        return False

    await db.delete(entry)
    return True


async def get_french_only_ids(db: AsyncSession, user_id: int) -> set[str]:
    """Get set of jellyfin_ids in user's french-only whitelist."""
    from app.database import FrenchOnlyWhitelist

    result = await db.execute(
        select(FrenchOnlyWhitelist.jellyfin_id).where(
            FrenchOnlyWhitelist.user_id == user_id
        )
    )
    return set(result.scalars().all())


# Language-Exempt Whitelist functions (US-5.3)


async def add_to_language_exempt_whitelist(
    db: AsyncSession,
    user_id: int,
    jellyfin_id: str,
    name: str,
    media_type: str,
) -> None:
    """Add an item to the user's language-exempt whitelist.

    Items in this whitelist are exempt from ALL language checks.
    Raises ValueError if item already exists.
    """
    from app.database import LanguageExemptWhitelist

    # Check if already whitelisted
    result = await db.execute(
        select(LanguageExemptWhitelist).where(
            LanguageExemptWhitelist.user_id == user_id,
            LanguageExemptWhitelist.jellyfin_id == jellyfin_id,
        )
    )
    if result.scalar_one_or_none():
        raise ValueError("Item already in language-exempt whitelist")

    entry = LanguageExemptWhitelist(
        user_id=user_id,
        jellyfin_id=jellyfin_id,
        name=name,
        media_type=media_type,
    )
    db.add(entry)


async def get_language_exempt_whitelist(
    db: AsyncSession,
    user_id: int,
) -> WhitelistListResponse:
    """Get all items in the user's language-exempt whitelist."""
    from app.database import LanguageExemptWhitelist

    result = await db.execute(
        select(LanguageExemptWhitelist)
        .where(LanguageExemptWhitelist.user_id == user_id)
        .order_by(LanguageExemptWhitelist.name)
    )
    entries = result.scalars().all()

    items = [
        WhitelistItem(
            id=entry.id,
            jellyfin_id=entry.jellyfin_id,
            name=entry.name,
            media_type=entry.media_type,
            created_at=entry.created_at.isoformat() if entry.created_at else "",
        )
        for entry in entries
    ]

    return WhitelistListResponse(
        items=items,
        total_count=len(items),
    )


async def remove_from_language_exempt_whitelist(
    db: AsyncSession,
    user_id: int,
    whitelist_id: int,
) -> bool:
    """Remove an item from the user's language-exempt whitelist.

    Returns True if item was found and deleted, False otherwise.
    """
    from app.database import LanguageExemptWhitelist

    result = await db.execute(
        select(LanguageExemptWhitelist).where(
            LanguageExemptWhitelist.id == whitelist_id,
            LanguageExemptWhitelist.user_id == user_id,
        )
    )
    entry = result.scalar_one_or_none()

    if not entry:
        return False

    await db.delete(entry)
    return True


async def get_language_exempt_ids(db: AsyncSession, user_id: int) -> set[str]:
    """Get set of jellyfin_ids in user's language-exempt whitelist."""
    from app.database import LanguageExemptWhitelist

    result = await db.execute(
        select(LanguageExemptWhitelist.jellyfin_id).where(
            LanguageExemptWhitelist.user_id == user_id
        )
    )
    return set(result.scalars().all())


def is_large_movie(item: CachedMediaItem) -> bool:
    """Check if an item is a large movie (>=13GB).

    Returns True if:
    - Item is a Movie (not Series)
    - Size meets or exceeds LARGE_MOVIE_SIZE_THRESHOLD_GB

    Note: Uses >= to match original_script.py list_large_movies() behavior.
    """
    if item.media_type != "Movie":
        return False

    if item.size_bytes is None:
        return False

    threshold_bytes = LARGE_MOVIE_SIZE_THRESHOLD_GB * 1024 * 1024 * 1024  # 13GB in bytes
    return item.size_bytes >= threshold_bytes


# Language code variants recognized by the system
ENGLISH_CODES = {"eng", "en", "english"}
FRENCH_CODES = {"fre", "fr", "french", "fra"}


def check_audio_languages(item: CachedMediaItem) -> LanguageCheckResult:
    """Check if item has English and French audio tracks.

    Based on original_script.py:check_audio_languages

    Returns dict with:
    - has_english: bool
    - has_french: bool
    - has_french_subs: bool
    - missing_languages: list[str] - specific issues found
    """
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


async def get_content_summary(
    db: AsyncSession,
    user_id: int,
) -> ContentSummaryResponse:
    """Get summary counts for all issue types for a user.

    Returns counts for:
    - old_content: Old/unwatched content (excludes whitelisted)
    - large_movies: Movies larger than 13GB
    - language_issues: Content with language issues (placeholder - 0)
    - unavailable_requests: Unavailable Jellyseerr requests (placeholder - 0)
    """
    # Get user's cached media items
    result = await db.execute(
        select(CachedMediaItem).where(CachedMediaItem.user_id == user_id)
    )
    all_items = result.scalars().all()

    # Get user's whitelist
    whitelist_result = await db.execute(
        select(ContentWhitelist.jellyfin_id).where(ContentWhitelist.user_id == user_id)
    )
    whitelisted_ids = set(whitelist_result.scalars().all())

    # Calculate old content (excluding whitelisted)
    old_content_items: list[CachedMediaItem] = []
    for item in all_items:
        if item.jellyfin_id in whitelisted_ids:
            continue
        if is_old_or_unwatched(item):
            old_content_items.append(item)

    old_content_size = sum(item.size_bytes or 0 for item in old_content_items)

    # Calculate large movies
    large_movies_items: list[CachedMediaItem] = []
    for item in all_items:
        if is_large_movie(item):
            large_movies_items.append(item)

    large_movies_size = sum(item.size_bytes or 0 for item in large_movies_items)

    # Get french-only whitelist for language checks
    french_only_ids = await get_french_only_ids(db, user_id)

    # Get language-exempt whitelist
    language_exempt_ids = await get_language_exempt_ids(db, user_id)

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

    # Unavailable requests count (US-6.1)
    unavailable_requests_count = await get_unavailable_requests_count(db, user_id)

    return ContentSummaryResponse(
        old_content=IssueCategorySummary(
            count=len(old_content_items),
            total_size_bytes=old_content_size,
            total_size_formatted=format_size(old_content_size) if old_content_size > 0 else "0 B",
        ),
        large_movies=IssueCategorySummary(
            count=len(large_movies_items),
            total_size_bytes=large_movies_size,
            total_size_formatted=format_size(large_movies_size) if large_movies_size > 0 else "0 B",
        ),
        language_issues=IssueCategorySummary(
            count=len(language_issues_items),
            total_size_bytes=language_issues_size,
            total_size_formatted=format_size(language_issues_size) if language_issues_size > 0 else "0 B",
        ),
        unavailable_requests=IssueCategorySummary(
            count=unavailable_requests_count,
            total_size_bytes=0,
            total_size_formatted="0 B",
        ),
        # Info categories
        recently_available=InfoCategorySummary(
            count=await get_recently_available_count(db, user_id),
        ),
        currently_airing=InfoCategorySummary(
            count=0,  # Placeholder - will be implemented in US-6.2
        ),
    )


# Constants for info endpoints
RECENT_ITEMS_DAYS_BACK = 7  # Content available in past 7 days


async def get_recently_available_count(
    db: AsyncSession,
    user_id: int,
) -> int:
    """Get count of recently available content for summary."""
    result = await db.execute(
        select(CachedJellyseerrRequest).where(
            CachedJellyseerrRequest.user_id == user_id
        )
    )
    all_requests = result.scalars().all()

    now = datetime.now(timezone.utc)
    cutoff_date = now - timedelta(days=RECENT_ITEMS_DAYS_BACK)

    count = 0
    for request in all_requests:
        # Only count available (4 or 5 status)
        if request.status not in [4, 5]:
            continue

        # Get availability date from raw_data
        availability_date = _get_availability_date(request)
        if not availability_date:
            continue

        if availability_date >= cutoff_date:
            count += 1

    return count


def _get_availability_date(request: CachedJellyseerrRequest) -> datetime | None:
    """Extract availability date from a Jellyseerr request.

    Looks for mediaAddedAt in raw_data, falls back to modifiedAt or createdAt.
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

    return parse_jellyfin_datetime(date_str)


async def get_recently_available(
    db: AsyncSession,
    user_id: int,
) -> RecentlyAvailableResponse:
    """Get content that became available in the past 7 days.

    Returns items sorted by date, newest first.
    """
    result = await db.execute(
        select(CachedJellyseerrRequest).where(
            CachedJellyseerrRequest.user_id == user_id
        )
    )
    all_requests = result.scalars().all()

    now = datetime.now(timezone.utc)
    cutoff_date = now - timedelta(days=RECENT_ITEMS_DAYS_BACK)

    recent_items: list[tuple[datetime, CachedJellyseerrRequest]] = []

    for request in all_requests:
        # Only count available (4 or 5 status)
        if request.status not in [4, 5]:
            continue

        # Get availability date from raw_data
        availability_date = _get_availability_date(request)
        if not availability_date:
            continue

        if availability_date >= cutoff_date:
            recent_items.append((availability_date, request))

    # Sort by date descending (newest first)
    recent_items.sort(key=lambda x: x[0], reverse=True)

    # Convert to response models
    response_items = [
        RecentlyAvailableItem(
            jellyseerr_id=request.jellyseerr_id,
            title=request.title or "Unknown",
            media_type=request.media_type,
            availability_date=availability_date.isoformat(),
            requested_by=request.requested_by,
        )
        for availability_date, request in recent_items
    ]

    return RecentlyAvailableResponse(
        items=response_items,
        total_count=len(response_items),
    )


async def get_currently_airing(
    db: AsyncSession,
    user_id: int,
) -> CurrentlyAiringResponse:
    """Get series that are currently airing (have in-progress seasons).

    Returns items sorted by next air date.
    Note: This is a placeholder implementation - full implementation in US-6.2.
    """
    # Placeholder - return empty list for now
    # Full implementation will analyze raw_data for in_progress_seasons
    return CurrentlyAiringResponse(
        items=[],
        total_count=0,
    )


def get_item_issues(
    item: CachedMediaItem,
    whitelisted_ids: set[str],
    french_only_ids: set[str] | None = None,
    language_exempt_ids: set[str] | None = None,
) -> tuple[list[str], list[str]]:
    """Get all issue types that apply to a content item.

    Args:
        item: The media item to check
        whitelisted_ids: Set of jellyfin_ids in content whitelist
        french_only_ids: Set of jellyfin_ids in french-only whitelist
        language_exempt_ids: Set of jellyfin_ids exempt from ALL language checks

    Returns tuple of:
    - list of issue types: "old", "large", "language", "request"
    - list of specific language issues: "missing_en_audio", "missing_fr_audio", etc.
    """
    issues: list[str] = []
    language_issues_detail: list[str] = []

    # Check for old/unwatched (exclude whitelisted)
    if item.jellyfin_id not in whitelisted_ids and is_old_or_unwatched(item):
        issues.append("old")

    # Check for large movie
    if is_large_movie(item):
        issues.append("large")

    # Check for language issues (skip if language-exempt, respect french-only whitelist)
    is_language_exempt = language_exempt_ids is not None and item.jellyfin_id in language_exempt_ids
    if not is_language_exempt:
        is_french_only = french_only_ids is not None and item.jellyfin_id in french_only_ids
        if has_language_issues(item, is_french_only=is_french_only):
            issues.append("language")
            language_issues_detail = get_language_issues_list(item, is_french_only=is_french_only)

    return issues, language_issues_detail


async def get_content_issues(
    db: AsyncSession,
    user_id: int,
    filter_type: str | None = None,
) -> ContentIssuesResponse:
    """Get all content with issues for a user.

    Args:
        db: Database session
        user_id: User ID from JWT
        filter_type: Optional filter - "old", "large", "language", "requests", "multi"

    Returns items sorted by size (largest first).
    """
    # Get user's cached media items
    result = await db.execute(
        select(CachedMediaItem).where(CachedMediaItem.user_id == user_id)
    )
    all_items = result.scalars().all()

    # Get user's whitelist
    whitelist_result = await db.execute(
        select(ContentWhitelist.jellyfin_id).where(ContentWhitelist.user_id == user_id)
    )
    whitelisted_ids = set(whitelist_result.scalars().all())

    # Get user's french-only whitelist
    french_only_ids = await get_french_only_ids(db, user_id)

    # Get user's language-exempt whitelist
    language_exempt_ids = await get_language_exempt_ids(db, user_id)

    # Build list of items with issues
    # Store tuple of (item, issues_list, language_issues_detail)
    items_with_issues: list[tuple[CachedMediaItem, list[str], list[str]]] = []

    for item in all_items:
        issues, language_issues_detail = get_item_issues(
            item, whitelisted_ids, french_only_ids, language_exempt_ids
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
        if filter_type == "multi" and len(issues) < 2:
            continue

        items_with_issues.append((item, issues, language_issues_detail))

    # Sort by size descending (largest first)
    items_with_issues.sort(key=lambda x: x[0].size_bytes or 0, reverse=True)

    # Calculate totals
    total_size_bytes = sum(item.size_bytes or 0 for item, _, _ in items_with_issues)

    # Convert to response models
    response_items = [
        ContentIssueItem(
            jellyfin_id=item.jellyfin_id,
            name=item.name,
            media_type=item.media_type,
            production_year=item.production_year,
            size_bytes=item.size_bytes,
            size_formatted=format_size(item.size_bytes),
            last_played_date=item.last_played_date,
            path=item.path,
            issues=issues,
            language_issues=language_issues_detail if language_issues_detail else None,
        )
        for item, issues, language_issues_detail in items_with_issues
    ]

    return ContentIssuesResponse(
        items=response_items,
        total_count=len(response_items),
        total_size_bytes=total_size_bytes,
        total_size_formatted=format_size(total_size_bytes),
    )


# US-6.1: Unavailable Requests functions


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
            return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
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


def _should_include_request(request: CachedJellyseerrRequest) -> bool:
    """Check if a request should be included in unavailable list.

    Filters out:
    - Future releases (not yet released)
    - Recent releases (released less than 3 months ago)
    """
    release_date_str = _get_request_release_date(request)
    if not release_date_str:
        # No release date - include by default (safer approach)
        return True

    release_date = _parse_release_date(release_date_str)
    if not release_date:
        return True

    now = datetime.now(timezone.utc)
    today = now.date()
    release_date_only = release_date.date()

    # Filter future releases
    if FILTER_FUTURE_RELEASES and release_date_only > today:
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
    """
    if request.media_type != "tv":
        return []

    raw_data = request.raw_data or {}
    seasons = raw_data.get("seasons", [])

    missing = []
    for season in seasons:
        season_num = season.get("seasonNumber")
        season_status = season.get("status", 0)

        # Season is missing if not Available (status 5)
        if season_num is not None and season_status != 5:
            missing.append(season_num)

    return sorted(missing)


def is_unavailable_request(request: CachedJellyseerrRequest) -> bool:
    """Check if a request is unavailable.

    A request is unavailable if:
    - Status is 0 (Unknown), 1 (Pending), 2 (Approved), or 4 (Partially Available)
    - NOT status 3 (Processing) or 5 (Available)
    - Release date is not in the future
    - Release date is not too recent (< 3 months)
    """
    if request.status not in UNAVAILABLE_STATUS_CODES:
        return False

    return _should_include_request(request)


async def get_unavailable_requests_count(
    db: AsyncSession,
    user_id: int,
) -> int:
    """Get count of unavailable requests for summary."""
    result = await db.execute(
        select(CachedJellyseerrRequest).where(
            CachedJellyseerrRequest.user_id == user_id
        )
    )
    all_requests = result.scalars().all()

    count = 0
    for request in all_requests:
        if is_unavailable_request(request):
            count += 1

    return count


async def get_unavailable_requests(
    db: AsyncSession,
    user_id: int,
) -> list[UnavailableRequestItem]:
    """Get all unavailable requests for a user.

    Returns items sorted by request date (newest first).
    """
    result = await db.execute(
        select(CachedJellyseerrRequest).where(
            CachedJellyseerrRequest.user_id == user_id
        )
    )
    all_requests = result.scalars().all()

    unavailable_items: list[tuple[datetime | None, UnavailableRequestItem]] = []

    for request in all_requests:
        if not is_unavailable_request(request):
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
        if not title:
            media = raw_data.get("media", {})
            title = media.get("title") or media.get("name") or media.get("originalTitle") or "Unknown"

        item = UnavailableRequestItem(
            jellyseerr_id=request.jellyseerr_id,
            title=title,
            media_type=request.media_type,
            requested_by=request.requested_by,
            request_date=request_date_str,
            issues=["request"],
            missing_seasons=missing_seasons if missing_seasons else None,
        )

        unavailable_items.append((request_date, item))

    # Sort by request date descending (newest first)
    unavailable_items.sort(key=lambda x: x[0] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)

    return [item for _, item in unavailable_items]
