"""Content analysis service for filtering old/unwatched content."""

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import CachedMediaItem, CachedJellyseerrRequest, ContentWhitelist
from app.models.content import (
    ContentSummaryResponse,
    CurrentlyAiringItem,
    CurrentlyAiringResponse,
    InfoCategorySummary,
    IssueCategorySummary,
    OldUnwatchedItem,
    OldUnwatchedResponse,
    RecentlyAvailableItem,
    RecentlyAvailableResponse,
    WhitelistItem,
    WhitelistListResponse,
)


# Hardcoded thresholds per acceptance criteria
OLD_CONTENT_MONTHS_CUTOFF = 4  # Content not watched in 4+ months
MIN_AGE_MONTHS = 3  # Don't flag content added recently
LARGE_MOVIE_SIZE_THRESHOLD_GB = 13  # Movies larger than 13GB


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
    """
    now = datetime.now(timezone.utc)
    cutoff_date = now - timedelta(days=months_cutoff * 30)
    min_age_date = now - timedelta(days=min_age_months * 30)

    # Check if item was added recently (skip if too new)
    date_created = parse_jellyfin_datetime(item.date_created)
    if date_created:
        # Make timezone-aware if not already
        if date_created.tzinfo is None:
            date_created = date_created.replace(tzinfo=timezone.utc)
        if date_created > min_age_date:
            # Item is too new, skip it
            return False

    # Never played - include if item is old enough
    if not item.played:
        return True

    # Played but no last_played_date (treat as old)
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


def is_large_movie(item: CachedMediaItem) -> bool:
    """Check if an item is a large movie (>13GB).

    Returns True if:
    - Item is a Movie (not Series)
    - Size exceeds LARGE_MOVIE_SIZE_THRESHOLD_GB
    """
    if item.media_type != "Movie":
        return False

    if item.size_bytes is None:
        return False

    threshold_bytes = LARGE_MOVIE_SIZE_THRESHOLD_GB * 1024 * 1024 * 1024  # 13GB in bytes
    return item.size_bytes > threshold_bytes


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

    # Language issues and unavailable requests are placeholders (implemented in US-5.1 and US-6.1)
    language_issues_count = 0
    unavailable_requests_count = 0

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
            count=language_issues_count,
            total_size_bytes=0,
            total_size_formatted="0 B",
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
