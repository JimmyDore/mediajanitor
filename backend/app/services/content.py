"""Content analysis service for filtering old/unwatched content."""

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import CachedMediaItem, ContentWhitelist
from app.models.content import OldUnwatchedItem, OldUnwatchedResponse


# Hardcoded thresholds per acceptance criteria
OLD_CONTENT_MONTHS_CUTOFF = 4  # Content not watched in 4+ months
MIN_AGE_MONTHS = 3  # Don't flag content added recently


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
