"""Content analysis service for filtering old/unwatched content."""

from dataclasses import dataclass
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


@dataclass
class UserThresholds:
    """User's analysis thresholds."""

    old_content_months: int
    min_age_months: int
    large_movie_size_gb: int
    large_season_size_gb: int


from app.database import CachedMediaItem, CachedJellyseerrRequest, ContentWhitelist, UserSettings
from app.models.content import (
    ContentIssueItem,
    ContentIssuesResponse,
    ContentSummaryResponse,
    InfoCategorySummary,
    IssueCategorySummary,
    OldUnwatchedItem,
    OldUnwatchedResponse,
    RecentlyAvailableItem,
    RecentlyAvailableResponse,
    RequestWhitelistItem,
    RequestWhitelistListResponse,
    UnavailableRequestItem,
    WhitelistItem,
    WhitelistListResponse,
)


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


async def get_user_thresholds(db: AsyncSession, user_id: int) -> UserThresholds:
    """Get user's analysis thresholds, falling back to defaults if not configured."""
    result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == user_id)
    )
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
    # Get user's thresholds
    thresholds = await get_user_thresholds(db, user_id)

    # Get user's cached media items
    result = await db.execute(
        select(CachedMediaItem).where(CachedMediaItem.user_id == user_id)
    )
    all_items = result.scalars().all()

    # Get user's whitelist (only non-expired entries)
    from sqlalchemy import or_
    now = datetime.now(timezone.utc)
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


async def add_to_whitelist(
    db: AsyncSession,
    user_id: int,
    jellyfin_id: str,
    name: str,
    media_type: str,
    expires_at: datetime | None = None,
) -> ContentWhitelist:
    """Add content to user's whitelist.

    Args:
        db: Database session
        user_id: User ID
        jellyfin_id: Jellyfin content ID
        name: Content name
        media_type: "Movie" or "Series"
        expires_at: Optional expiration datetime (None = permanent)

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
        expires_at=expires_at,
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
            expires_at=entry.expires_at.isoformat() if entry.expires_at else None,
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
    expires_at: datetime | None = None,
) -> None:
    """Add an item to the user's french-only whitelist.

    Items in this whitelist are exempt from missing English audio checks.

    Args:
        db: Database session
        user_id: User ID
        jellyfin_id: Jellyfin content ID
        name: Content name
        media_type: "Movie" or "Series"
        expires_at: Optional expiration datetime (None = permanent)

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
        expires_at=expires_at,
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
            expires_at=entry.expires_at.isoformat() if entry.expires_at else None,
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
    """Get set of jellyfin_ids in user's french-only whitelist (non-expired only)."""
    from sqlalchemy import or_
    from app.database import FrenchOnlyWhitelist

    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(FrenchOnlyWhitelist.jellyfin_id).where(
            FrenchOnlyWhitelist.user_id == user_id,
            # Only include non-expired entries (NULL = permanent, or expires_at > now)
            or_(
                FrenchOnlyWhitelist.expires_at.is_(None),
                FrenchOnlyWhitelist.expires_at > now,
            ),
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
    expires_at: datetime | None = None,
) -> None:
    """Add an item to the user's language-exempt whitelist.

    Items in this whitelist are exempt from ALL language checks.

    Args:
        db: Database session
        user_id: User ID
        jellyfin_id: Jellyfin content ID
        name: Content name
        media_type: "Movie" or "Series"
        expires_at: Optional expiration datetime (None = permanent)

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
        expires_at=expires_at,
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
            expires_at=entry.expires_at.isoformat() if entry.expires_at else None,
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
    """Get set of jellyfin_ids in user's language-exempt whitelist (non-expired only)."""
    from sqlalchemy import or_
    from app.database import LanguageExemptWhitelist

    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(LanguageExemptWhitelist.jellyfin_id).where(
            LanguageExemptWhitelist.user_id == user_id,
            # Only include non-expired entries (NULL = permanent, or expires_at > now)
            or_(
                LanguageExemptWhitelist.expires_at.is_(None),
                LanguageExemptWhitelist.expires_at > now,
            ),
        )
    )
    return set(result.scalars().all())


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
    - large_movies: Movies larger than threshold
    - language_issues: Content with language issues
    - unavailable_requests: Unavailable Jellyseerr requests
    """
    # Get user's thresholds
    thresholds = await get_user_thresholds(db, user_id)

    # Get user's cached media items
    result = await db.execute(
        select(CachedMediaItem).where(CachedMediaItem.user_id == user_id)
    )
    all_items = result.scalars().all()

    # Get user's whitelist (only non-expired entries)
    from sqlalchemy import or_
    now = datetime.now(timezone.utc)
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

    # Calculate large content (movies + series)
    large_content_items: list[CachedMediaItem] = []
    for item in all_items:
        if is_large_movie(item, threshold_gb=thresholds.large_movie_size_gb):
            large_content_items.append(item)
        elif is_large_series(item, threshold_gb=thresholds.large_season_size_gb):
            large_content_items.append(item)

    large_content_size = sum(item.size_bytes or 0 for item in large_content_items)

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
            count=len(large_content_items),
            total_size_bytes=large_content_size,
            total_size_formatted=format_size(large_content_size) if large_content_size > 0 else "0 B",
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
    )


# Constants for info endpoints
DEFAULT_RECENTLY_AVAILABLE_DAYS = 7  # Content available in past 7 days


async def get_user_recently_available_days(db: AsyncSession, user_id: int) -> int:
    """Get user's recently_available_days setting, falling back to default."""
    result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == user_id)
    )
    settings = result.scalar_one_or_none()

    if settings and settings.recently_available_days is not None:
        return settings.recently_available_days
    return DEFAULT_RECENTLY_AVAILABLE_DAYS


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
    """
    if days_back is None:
        days_back = await get_user_recently_available_days(db, user_id)

    result = await db.execute(
        select(CachedJellyseerrRequest).where(
            CachedJellyseerrRequest.user_id == user_id
        )
    )
    all_requests = result.scalars().all()

    now = datetime.now(timezone.utc)
    cutoff_date = now - timedelta(days=days_back)

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


async def get_nickname_map(db: AsyncSession, user_id: int) -> dict[str, str]:
    """Get a mapping of jellyseerr_username -> display_name for a user.

    Returns a dict where keys are Jellyseerr usernames and values are display names.
    """
    from app.database import UserNickname

    result = await db.execute(
        select(UserNickname).where(UserNickname.user_id == user_id)
    )
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
    """
    if days_back is None:
        days_back = await get_user_recently_available_days(db, user_id)

    result = await db.execute(
        select(CachedJellyseerrRequest).where(
            CachedJellyseerrRequest.user_id == user_id
        )
    )
    all_requests = result.scalars().all()

    # Get nickname mappings for resolving display names
    nickname_map = await get_nickname_map(db, user_id)

    now = datetime.now(timezone.utc)
    cutoff_date = now - timedelta(days=days_back)

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
            title_fr=request.title_fr,
            media_type=request.media_type,
            availability_date=availability_date.isoformat(),
            requested_by=request.requested_by,
            display_name=resolve_display_name(request.requested_by, nickname_map),
        )
        for availability_date, request in recent_items
    ]

    return RecentlyAvailableResponse(
        items=response_items,
        total_count=len(response_items),
    )


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


def get_item_issues(
    item: CachedMediaItem,
    whitelisted_ids: set[str],
    french_only_ids: set[str] | None = None,
    language_exempt_ids: set[str] | None = None,
    thresholds: UserThresholds | None = None,
) -> tuple[list[str], list[str]]:
    """Get all issue types that apply to a content item.

    Args:
        item: The media item to check
        whitelisted_ids: Set of jellyfin_ids in content whitelist
        french_only_ids: Set of jellyfin_ids in french-only whitelist
        language_exempt_ids: Set of jellyfin_ids exempt from ALL language checks
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
    large_movie_size = thresholds.large_movie_size_gb if thresholds else LARGE_MOVIE_SIZE_THRESHOLD_GB
    large_season_size = thresholds.large_season_size_gb if thresholds else LARGE_SEASON_SIZE_THRESHOLD_GB

    # Check for old/unwatched (exclude whitelisted)
    if item.jellyfin_id not in whitelisted_ids and is_old_or_unwatched(
        item, months_cutoff=old_months, min_age_months=min_age
    ):
        issues.append("old")

    # Check for large content (movie or series)
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
    from app.services.sonarr import get_sonarr_tmdb_to_slug_map, get_decrypted_sonarr_api_key
    sonarr_slug_map: dict[int, str] = {}
    settings_result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == user_id)
    )
    user_settings = settings_result.scalar_one_or_none()
    if user_settings and user_settings.sonarr_server_url and user_settings.sonarr_api_key_encrypted:
        sonarr_api_key = get_decrypted_sonarr_api_key(user_settings)
        if sonarr_api_key:
            sonarr_slug_map = await get_sonarr_tmdb_to_slug_map(
                user_settings.sonarr_server_url, sonarr_api_key
            )

    # Get user's cached media items
    result = await db.execute(
        select(CachedMediaItem).where(CachedMediaItem.user_id == user_id)
    )
    all_items = result.scalars().all()

    # Get user's whitelist (only non-expired entries)
    from sqlalchemy import or_
    now = datetime.now(timezone.utc)
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

    # Build list of items with issues
    # Store tuple of (item, issues_list, language_issues_detail)
    items_with_issues: list[tuple[CachedMediaItem, list[str], list[str]]] = []

    for item in all_items:
        issues, language_issues_detail = get_item_issues(
            item, whitelisted_ids, french_only_ids, language_exempt_ids, thresholds
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
        select(CachedJellyseerrRequest.tmdb_id, CachedJellyseerrRequest.media_type, CachedJellyseerrRequest.jellyseerr_id)
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
        largest_season_size_bytes = item.largest_season_size_bytes if item.media_type == "Series" else None
        largest_season_size_formatted = format_size(largest_season_size_bytes) if largest_season_size_bytes else None

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
            )
        )

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

    now = datetime.now(timezone.utc)
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


def is_unavailable_request(
    request: CachedJellyseerrRequest,
    show_unreleased: bool = False,
) -> bool:
    """Check if a request is unavailable.

    A request is unavailable if:
    - Status is 0 (Unknown), 1 (Pending), 2 (Approved), or 4 (Partially Available)
    - NOT status 3 (Processing) or 5 (Available)
    - Release date is not in the future (unless show_unreleased=True)
    - Release date is not too recent (< 3 months)

    Args:
        request: The Jellyseerr request to check
        show_unreleased: If True, include future releases (user preference)
    """
    if request.status not in UNAVAILABLE_STATUS_CODES:
        return False

    return _should_include_request(request, show_unreleased)


async def get_user_show_unreleased_setting(db: AsyncSession, user_id: int) -> bool:
    """Get user's show_unreleased_requests setting.

    Returns False (default) if not configured.
    """
    result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == user_id)
    )
    settings = result.scalar_one_or_none()
    return settings.show_unreleased_requests if settings else False


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
        select(CachedJellyseerrRequest).where(
            CachedJellyseerrRequest.user_id == user_id
        )
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
        select(CachedJellyseerrRequest).where(
            CachedJellyseerrRequest.user_id == user_id
        )
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
    unavailable_items.sort(key=lambda x: x[0] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)

    return [item for _, item in unavailable_items]


# US-13.4: Request Whitelist functions


async def add_to_request_whitelist(
    db: AsyncSession,
    user_id: int,
    jellyseerr_id: int,
    title: str,
    media_type: str,
    expires_at: datetime | None = None,
) -> None:
    """Add a Jellyseerr request to user's whitelist.

    Args:
        db: Database session
        user_id: User ID
        jellyseerr_id: Jellyseerr request ID
        title: Request title
        media_type: "movie" or "tv"
        expires_at: Optional expiration datetime (None = permanent)

    Raises ValueError if the request is already in the whitelist.
    """
    from app.database import JellyseerrRequestWhitelist

    # Check if already whitelisted
    result = await db.execute(
        select(JellyseerrRequestWhitelist).where(
            JellyseerrRequestWhitelist.user_id == user_id,
            JellyseerrRequestWhitelist.jellyseerr_id == jellyseerr_id,
        )
    )
    if result.scalar_one_or_none():
        raise ValueError("Request already in whitelist")

    entry = JellyseerrRequestWhitelist(
        user_id=user_id,
        jellyseerr_id=jellyseerr_id,
        title=title,
        media_type=media_type,
        expires_at=expires_at,
    )
    db.add(entry)


async def get_request_whitelist(
    db: AsyncSession,
    user_id: int,
) -> RequestWhitelistListResponse:
    """Get all items in the user's request whitelist."""
    from app.database import JellyseerrRequestWhitelist

    result = await db.execute(
        select(JellyseerrRequestWhitelist)
        .where(JellyseerrRequestWhitelist.user_id == user_id)
        .order_by(JellyseerrRequestWhitelist.title)
    )
    entries = result.scalars().all()

    items = [
        RequestWhitelistItem(
            id=entry.id,
            jellyseerr_id=entry.jellyseerr_id,
            title=entry.title,
            media_type=entry.media_type,
            created_at=entry.created_at.isoformat() if entry.created_at else "",
            expires_at=entry.expires_at.isoformat() if entry.expires_at else None,
        )
        for entry in entries
    ]

    return RequestWhitelistListResponse(
        items=items,
        total_count=len(items),
    )


async def remove_from_request_whitelist(
    db: AsyncSession,
    user_id: int,
    whitelist_id: int,
) -> bool:
    """Remove an item from the user's request whitelist.

    Returns True if item was found and deleted, False otherwise.
    """
    from app.database import JellyseerrRequestWhitelist

    result = await db.execute(
        select(JellyseerrRequestWhitelist).where(
            JellyseerrRequestWhitelist.id == whitelist_id,
            JellyseerrRequestWhitelist.user_id == user_id,
        )
    )
    entry = result.scalar_one_or_none()

    if not entry:
        return False

    await db.delete(entry)
    return True


async def get_request_whitelist_ids(db: AsyncSession, user_id: int) -> set[int]:
    """Get set of jellyseerr_ids in user's request whitelist (non-expired only)."""
    from sqlalchemy import or_
    from app.database import JellyseerrRequestWhitelist

    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(JellyseerrRequestWhitelist.jellyseerr_id).where(
            JellyseerrRequestWhitelist.user_id == user_id,
            # Only include non-expired entries (NULL = permanent, or expires_at > now)
            or_(
                JellyseerrRequestWhitelist.expires_at.is_(None),
                JellyseerrRequestWhitelist.expires_at > now,
            ),
        )
    )
    return set(result.scalars().all())


# US-22.1: Library API functions


from app.models.content import LibraryItem, LibraryResponse


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
    # Get all cached media items for the user
    result = await db.execute(
        select(CachedMediaItem).where(CachedMediaItem.user_id == user_id)
    )
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
        if min_year is not None and (item.production_year is None or item.production_year < min_year):
            continue
        if max_year is not None and (item.production_year is None or item.production_year > max_year):
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
            )
        )

    return LibraryResponse(
        items=response_items,
        total_count=len(response_items),
        total_size_bytes=total_size_bytes,
        total_size_formatted=format_size(total_size_bytes) if total_size_bytes > 0 else "0 B",
    )
